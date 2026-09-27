import pytest
from backend.models.model_backend import get_backend, MockBackend, QNNBackend, ModelBackend


def test_model_backend_hierarchy():
    backend = get_backend()
    assert isinstance(backend, ModelBackend)
    assert backend.name is not None


def test_mock_backend_generation():
    mock = MockBackend()
    res = mock.generate("Write a concise docstring for this function")
    assert "docstring" in res.lower() or '"""' in res

    review = mock.generate("You are a senior code reviewer.")
    assert "ISSUES:" in review
    assert "SEVERITY:" in review


def test_qnn_backend_heuristic_review():
    try:
        qnn = QNNBackend()
    except Exception:
        pytest.skip("QNN model context binary not found in test environment")

    # 1. URL and path should NOT trigger division by zero false positive
    clean_code = """Code:
def download_data():
    url = "http://example.com/api/v1/data"
    path = "users/data/report.json"
    # comment with / slash
    return url
"""
    review = qnn.generate(clean_code)
    assert "division by zero" not in review.lower()

    # 2. Genuine unvalidated division SHOULD be caught
    risky_code = """Code:
def compute_ratio(total, count):
    return total / count
"""
    review_risky = qnn.generate(risky_code)
    assert "division by zero" in review_risky.lower()


def test_qnn_backend_detects_mutable_default():
    backend = get_backend()
    code = """Code:
def append_item(val, bucket=[]):
    bucket.append(val)
    return bucket
"""
    res = backend.generate(code)
    assert "mutable default argument" in res.lower()
    assert "Medium" in res


def test_qnn_backend_detects_bare_except():
    backend = get_backend()
    code = """Code:
def run_task():
    try:
        do_work()
    except:
        pass
"""
    res = backend.generate(code)
    assert "bare 'except:'" in res.lower()


def test_qnn_backend_detects_blocking_call_in_async():
    backend = get_backend()
    code = """Code:
import time

async def fetch_job():
    time.sleep(2)
    return "done"
"""
    res = backend.generate(code)
    assert "blocking synchronous call" in res.lower()
    assert "High" in res


def test_qnn_backend_detects_dom_xss():
    backend = get_backend()
    code = """Code:
// JavaScript UI handler
function renderProfile(user) {
    document.getElementById("output").innerHTML = "<div>" + user.bio + "</div>";
}
"""
    res = backend.generate(f"You are a senior code reviewer for javascript.\n{code}")
    assert "dom xss" in res.lower() or "innerhtml" in res.lower()
    assert "High" in res


def test_qnn_backend_detects_insecure_random_token():
    backend = get_backend()
    code = """Code:
import random

def generate_session_token():
    return "".join(random.choice("abcdef0123456789") for _ in range(32))
"""
    res = backend.generate(code)
    assert "insecure" in res.lower() or "random" in res.lower()
    assert "High" in res


def test_qnn_backend_detects_unhandled_promise():
    backend = get_backend()
    code = """Code:
function syncData() {
    fetch("/api/sync");
}
"""
    res = backend.generate(f"You are a senior code reviewer for javascript.\n{code}")
    assert "unhandled promise" in res.lower()

