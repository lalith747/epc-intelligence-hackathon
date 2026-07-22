"""
Regex-based metadata extraction for EPC documents.

Pulls structured fields out of raw extracted text: vendor, revision,
issue date, equipment IDs, drawing numbers, spec clause references,
approval status, and technical fields used by the compliance engine
(capacity, voltage, frequency, redundancy, certification standards).

This is deliberately dependency-free (stdlib re only) so it works the
same whether called from the upload pipeline or the sample-data seeder.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------
# Category inference from filename (matches the generator's naming
# convention: doc_###_Category_Name.ext)
# ---------------------------------------------------------------------
_CATEGORY_RE = re.compile(r"^doc_\d+_(.+)$", re.IGNORECASE)

KNOWN_CATEGORIES = [
    "Client Specification",
    "Vendor Submittal",
    "Shop Drawing",
    "RFIs",
    "Test Record",
    "NCR",
    "Change Order",
    "Inspection Report",
    "Meeting Minutes",
    "Notes",
]


def infer_category_from_filename(filename: str) -> str:
    """e.g. doc_001_Client_Specification.pdf -> 'Client Specification'."""
    stem = Path(filename).stem
    match = _CATEGORY_RE.match(stem)
    if not match:
        return "Unclassified"
    return match.group(1).replace("_", " ").strip()


# ---------------------------------------------------------------------
# Field extraction patterns
# ---------------------------------------------------------------------
_REVISION_RE = re.compile(r"Revision\s*:?\s*([A-Za-z0-9.]+)", re.IGNORECASE)
_DATE_RE = re.compile(
    r"(?:Issue Date|Submittal Date|Date)\s*:?\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE
)
_DOC_ID_RE = re.compile(r"Document ID\s*:?\s*([A-Z]+-\d+)", re.IGNORECASE)
_DWG_RE = re.compile(r"\bDWG[- ]?(?:No\.?)?\s*:?\s*([A-Z]*-?\d[\w-]*)", re.IGNORECASE)
_DWG_ALT_RE = re.compile(r"\bDW-\d{3}-[A-Z]\b")
_EQUIPMENT_RE = re.compile(r"\b(?:EQ|UPS|GEN|PDU|AHU|CHW)-\d{1,4}\b")
_CLAUSE_RE = re.compile(r"\b(?:Clause|Section)\s+[\d.]+\b", re.IGNORECASE)
_VOLTAGE_RE = re.compile(r"\b(\d{2,3})\s*V\b(?:\s*3-phase)?", re.IGNORECASE)
_FREQUENCY_RE = re.compile(r"\b(\d{2})\s*Hz\b", re.IGNORECASE)
_KVA_RE = re.compile(r"(\d{2,5})\s*kVA", re.IGNORECASE)
_REDUNDANCY_RE = re.compile(r"\b(2N\+1|2N|N\+\d|N)\s*redundancy\b", re.IGNORECASE)
_CERT_RE = re.compile(r"\b(UL Listed|CE Mark|CSA|IEC ?\d+|UL ?\d+|NEC)\b", re.IGNORECASE)
_TEMP_RE = re.compile(r"(-?\d{1,3})\s*(?:°C|deg ?C|C)\b(?:\s*(?:to|-)\s*(-?\d{1,3})\s*(?:°C|deg ?C|C))?")
_APPROVAL_KEYWORDS = [
    ("Approved", re.compile(r"\bApproved\b", re.IGNORECASE)),
    ("Rejected", re.compile(r"\bRejected\b", re.IGNORECASE)),
    ("Under Review", re.compile(r"\bUnder Review\b", re.IGNORECASE)),
    ("Pending", re.compile(r"\bPending\b", re.IGNORECASE)),
]
_VENDOR_RE = re.compile(r"Vendor Submittal\s*[–-]\s*(.+)", re.IGNORECASE)


def _first(pattern: re.Pattern, text: str) -> Optional[str]:
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def _all_unique(pattern: re.Pattern, text: str, limit: int = 10) -> List[str]:
    seen: list[str] = []
    for m in pattern.finditer(text):
        val = m.group(0).strip()
        if val not in seen:
            seen.append(val)
        if len(seen) >= limit:
            break
    return seen


def extract_metadata(text: str, filename: str) -> Dict[str, Any]:
    """Extract all structured fields from a document's raw text."""
    text = text or ""

    approval_status = "Pending"
    for label, pattern in _APPROVAL_KEYWORDS:
        if pattern.search(text):
            approval_status = label
            break

    vendor = _first(_VENDOR_RE, text)

    return {
        "document_category": infer_category_from_filename(filename),
        "document_ref": _first(_DOC_ID_RE, text),
        "revision": _first(_REVISION_RE, text) or "Unspecified",
        "issue_date": _first(_DATE_RE, text),
        "vendor": vendor,
        "equipment_ids": _all_unique(_EQUIPMENT_RE, text),
        "drawing_numbers": list(
            dict.fromkeys(_all_unique(_DWG_RE, text) + _all_unique(_DWG_ALT_RE, text))
        ),
        "spec_references": _all_unique(_CLAUSE_RE, text),
        "approval_status": approval_status,
        # Technical fields, used heavily by the compliance engine
        "voltage_v": _first(_VOLTAGE_RE, text),
        "frequency_hz": _first(_FREQUENCY_RE, text),
        "capacity_kva": _first(_KVA_RE, text),
        "redundancy": _first(_REDUNDANCY_RE, text),
        "certifications": _all_unique(_CERT_RE, text),
        "temperature_c": _TEMP_RE.search(text).group(0) if _TEMP_RE.search(text) else None,
    }
