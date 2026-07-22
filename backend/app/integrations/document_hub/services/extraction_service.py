import csv
import re
import zipfile
from pathlib import Path
from typing import List, Tuple, Any, Dict
import xml.etree.ElementTree as ET

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover
    fitz = None

try:
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover
    Image = None

try:
    import pytesseract  # type: ignore
except ImportError:  # pragma: no cover
    pytesseract = None


def extract_text(file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    suffix = file_path.suffix.lower()
    if suffix == ".txt":
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return text, chunk_text(text)
    if suffix == ".csv":
        text = _extract_csv_text(file_path)
        return text, chunk_text(text)
    if suffix == ".pdf":
        text = _extract_pdf_text(file_path)
        return text, chunk_text(text)
    if suffix == ".docx":
        text = _extract_docx_text(file_path)
        return text, chunk_text(text)
    if suffix in {".png", ".jpg", ".jpeg"}:
        text = _extract_image_text(file_path)
        return text, chunk_text(text)
    if suffix in {".xlsx", ".xls"}:
        text = _extract_xlsx_text(file_path)
        return text, chunk_text(text)
    return "", []


def _extract_csv_text(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return ""
    header = rows[0]
    body = rows[1:]
    lines = [", ".join(header)] + [", ".join(row) for row in body if row]
    return "\n".join(lines)


def _extract_pdf_text(file_path: Path) -> str:
    if fitz is None:
        return ""
    document = fitz.open(file_path)
    pages = []
    for page in document:
        pages.append(page.get_text())
    document.close()
    return "\n\n".join(pages)


def _extract_docx_text(file_path: Path) -> str:
    with zipfile.ZipFile(file_path) as archive:
        xml_content = archive.read("word/document.xml")
    root = ET.fromstring(xml_content)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for node in root.findall(".//w:p", ns):
        texts = [t.text or "" for t in node.findall(".//w:t", ns)]
        paragraph = "".join(texts).strip()
        if paragraph:
            paragraphs.append(paragraph)
    return "\n".join(paragraphs)


def _extract_xlsx_text(file_path: Path) -> str:
    try:
        import pandas as pd  # local import: keeps module importable without pandas
    except ImportError:  # pragma: no cover
        return ""
    try:
        sheets = pd.read_excel(file_path, sheet_name=None)
    except Exception:
        return ""
    parts: List[str] = []
    for sheet_name, frame in sheets.items():
        parts.append(f"Sheet: {sheet_name}")
        parts.append(frame.to_csv(index=False))
    return "\n".join(parts)


def _extract_image_text(file_path: Path) -> str:
    if Image is None or pytesseract is None:
        return ""
    image = Image.open(file_path)
    return pytesseract.image_to_string(image)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 140) -> List[Dict[str, Any]]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    words = cleaned.split()
    if len(words) <= chunk_size:
        return [{"content": cleaned, "section": "Section 1", "page_number": 1}]
    chunks: List[Dict[str, Any]] = []
    start = 0
    chunk_index = 1
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk = " ".join(words[start:end])
        chunks.append({"content": chunk, "section": f"Section {chunk_index}", "page_number": 1})
        if end >= len(words):
            break
        start = max(0, end - overlap)
        chunk_index += 1
    return chunks
