import subprocess
from pathlib import Path

def convert_html_to_pdf():
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    base_dir = Path(__file__).resolve().parent.parent
    html_path = base_dir / "submission_docs" / "Faraday_Documentary.html"
    pdf_path = base_dir / "submission_docs" / "Faraday_Complete_Documentary_Dossier.pdf"

    cmd = [
        edge_path,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path.resolve()}",
        f"file:///{html_path.resolve()}".replace("\\", "/")
    ]
    try:
        subprocess.run(cmd, timeout=12)
    except subprocess.TimeoutExpired:
        pass

    if pdf_path.exists():
        print(f"SUCCESS: Generated PDF at {pdf_path} (Size: {pdf_path.stat().st_size} bytes)")
    else:
        print("ERROR: PDF was not generated.")

if __name__ == "__main__":
    convert_html_to_pdf()
