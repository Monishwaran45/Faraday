"""
Unit tests for Faraday On-Device LoRA Fine-Tuning Engine
Author: Monishwaran K
Qualcomm Snapdragon Innovation Challenge 2026
"""

import shutil
import tempfile
from pathlib import Path

import pytest
import torch

from backend.core.lora_trainer import (
    LoRAConfig,
    LoRALinear,
    OnDeviceCodeStyleModel,
    OnDeviceLoRATrainer,
)


def test_lora_config_defaults():
    config = LoRAConfig(r=8, lora_alpha=16.0)
    assert config.r == 8
    assert config.lora_alpha == 16.0
    assert config.scaling == 2.0  # 16 / 8 = 2.0


def test_lora_linear_parameter_freezing():
    config = LoRAConfig(r=4, in_features=64, out_features=64)
    layer = LoRALinear(64, 64, config)

    # Base weights must be frozen
    assert not layer.base_linear.weight.requires_grad
    if layer.base_linear.bias is not None:
        assert not layer.base_linear.bias.requires_grad

    # LoRA matrices must exist and B must be zero-initialized
    assert layer.lora_A is not None
    assert layer.lora_B is not None
    assert torch.all(layer.lora_B == 0.0)

    # Forward pass on zero-initialized B should match base_linear output exactly
    x = torch.randn(2, 64)
    y_lora = layer(x)
    y_base = layer.base_linear(x)
    assert torch.allclose(y_lora, y_base, atol=1e-5)


def test_lora_model_parameter_efficiency():
    config = LoRAConfig(r=4, in_features=128, out_features=128)
    model = OnDeviceCodeStyleModel(config)
    stats = model.count_parameters()

    assert stats["trainable_parameters"] > 0
    assert stats["frozen_parameters"] > 0
    # LoRA trainable ratio should be very small (< 15%)
    assert stats["trainable_ratio"] < 15.0


def test_on_device_training_loop():
    config = LoRAConfig(r=4, in_features=128, out_features=128, epochs=3, learning_rate=1e-3)
    trainer = OnDeviceLoRATrainer(config)

    # Use sample_project for real AST dataset extraction
    sample_dir = Path("demo/sample_project")
    results = trainer.train(sample_dir, epochs=3)

    assert results["epochs"] == 3
    assert results["dataset_size"] > 0
    assert len(trainer.train_losses) == 3
    # Loss should not be NaN
    assert not torch.isnan(torch.tensor(results["final_loss"]))


def test_save_and_load_adapter_roundtrip():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        config = LoRAConfig(r=8, in_features=128, out_features=128, epochs=2)
        trainer = OnDeviceLoRATrainer(config)
        trainer.train(Path("demo/sample_project"), epochs=2)

        # Save adapter
        adapter_path = trainer.save_adapter(temp_dir / "test_adapter")
        assert (adapter_path / "adapter_config.json").exists()
        assert (adapter_path / "adapter_weights.pt").exists()

        # Load into fresh trainer
        fresh_trainer = OnDeviceLoRATrainer(LoRAConfig(r=8, in_features=128, out_features=128))
        fresh_trainer.load_adapter(adapter_path)

        # Verify weights match
        for key in trainer.model.state_dict():
            if "lora" in key:
                orig = trainer.model.state_dict()[key]
                loaded = fresh_trainer.model.state_dict()[key]
                assert torch.allclose(orig, loaded, atol=1e-6)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
