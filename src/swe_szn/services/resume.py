from pathlib import Path
from pypdf import PdfReader


def parse_pdf(path: str) -> str:
    reader = PdfReader(path)
    text = []
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return " ".join(" ".join(text).split())


def parse_resume(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Resume not found: {path}")

    if p.suffix.lower() == ".pdf":
        return parse_pdf(str(p))
    elif p.suffix.lower() == ".txt":
        return p.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError("Resume must be .pdf or .txt")
