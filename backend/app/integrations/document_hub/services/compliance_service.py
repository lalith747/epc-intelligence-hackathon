import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.database.init_db import DB_PATH
from backend.schemas.models import ComplianceReport, ComplianceRequest, Deviation
from backend.services.metadata_extractor import extract_metadata

try:
    from groq import Groq  # type: ignore
except Exception:  # pragma: no cover
    Groq = None  # type: ignore


class ComplianceService:
    def __init__(self) -> None:
        self.db_path = DB_PATH
        self.storage_dir = Path(__file__).resolve().parents[1] / "storage" / "reports"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        if Groq is not None:
            try:
                self.client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
            except Exception:
                self.client = None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def run(self, request: ComplianceRequest, background_tasks: Optional[BackgroundTasks] = None) -> ComplianceReport:
        conn = self._connect()
        try:
            spec_row = conn.execute("SELECT * FROM documents WHERE id = ?", (request.specification_document_id,)).fetchone()
            vendor_row = conn.execute("SELECT * FROM documents WHERE id = ?", (request.vendor_document_id,)).fetchone()

            if not spec_row or not vendor_row:
                return ComplianceReport(
                    overall_score="Fail",
                    summary="Specification or vendor document not found in the system.",
                    deviations=[],
                    report_pdf_url=None,
                )

            spec_text = self._chunk_text(conn, spec_row["id"])
            vendor_text = self._chunk_text(conn, vendor_row["id"])

            deviations: List[Deviation] = []
            deviations.extend(self._check_missing_text(spec_text, vendor_text))

            if spec_text.strip() and vendor_text.strip():
                spec_meta = extract_metadata(spec_text, spec_row["file_name"] or "spec")
                vendor_meta = extract_metadata(vendor_text, vendor_row["file_name"] or "submittal")
                deviations.extend(self._compare_technical_fields(spec_meta, vendor_meta))
                deviations.extend(self._llm_review(spec_text, vendor_text))

            overall_score = self._score(deviations)
            report_id = str(uuid.uuid4())
            pdf_url = f"/reports/{report_id}.pdf"
            report_payload = {
                "overall_score": overall_score,
                "summary": self._summarize(overall_score, deviations),
                "deviations": [deviation.model_dump() for deviation in deviations],
                "report_pdf_url": pdf_url,
                "spec_title": spec_row["title"],
                "vendor_title": vendor_row["title"],
            }
            conn.execute(
                "INSERT INTO compliance_reports (document_id, overall_score, status, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (spec_row["id"], overall_score, "completed", json.dumps(report_payload), datetime.utcnow().isoformat()),
            )
            conn.commit()

            self._generate_pdf_report(report_id, report_payload)

            return ComplianceReport(
                overall_score=overall_score,
                summary=report_payload["summary"],
                deviations=deviations,
                report_pdf_url=pdf_url,
            )
        except Exception as exc:
            conn.rollback()
            return ComplianceReport(
                overall_score="Fail",
                summary=f"Compliance check encountered a system error: {str(exc)}",
                deviations=[],
                report_pdf_url=None,
            )
        finally:
            conn.close()

    def list_reports(self) -> List[dict]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT id, document_id, overall_score, status, created_at FROM compliance_reports ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Deterministic checks
    # ------------------------------------------------------------------
    def _chunk_text(self, conn: sqlite3.Connection, document_id: int) -> str:
        rows = conn.execute(
            "SELECT content FROM chunks WHERE document_id = ? ORDER BY id", (document_id,)
        ).fetchall()
        return "\n".join(row["content"] for row in rows)[:8000]

    def _check_missing_text(self, spec_text: str, vendor_text: str) -> List[Deviation]:
        deviations: List[Deviation] = []
        if not spec_text.strip():
            deviations.append(Deviation(
                severity="critical",
                description="Specification payload is empty or missing chunk text.",
                evidence="No specification content was found for the selected document.",
                recommendation="Re-upload the specification document and ensure it was ingested successfully.",
                document_ref="Specification", page_number=1, spec_clause="N/A",
            ))
        if not vendor_text.strip():
            deviations.append(Deviation(
                severity="critical",
                description="Vendor submittal payload is empty or missing chunk text.",
                evidence="No vendor submittal content was found for the selected document.",
                recommendation="Re-upload the vendor submittal and ensure it was ingested successfully.",
                document_ref="Submittal", page_number=1, spec_clause="N/A",
            ))
        return deviations

    def _compare_technical_fields(self, spec: Dict[str, Any], vendor: Dict[str, Any]) -> List[Deviation]:
        deviations: List[Deviation] = []

        # Capacity (kVA) — vendor must meet or exceed spec
        spec_kva, vendor_kva = spec.get("capacity_kva"), vendor.get("capacity_kva")
        if spec_kva and vendor_kva:
            try:
                if int(vendor_kva) < int(spec_kva):
                    deviations.append(Deviation(
                        severity="critical",
                        description="Capacity mismatch between specification and vendor submittal.",
                        evidence=f"Specification requires {spec_kva} kVA; vendor submittal offers only {vendor_kva} kVA.",
                        recommendation="Request a revised submittal meeting or exceeding the specified capacity, or obtain a client waiver.",
                        document_ref="Submittal", page_number=1, spec_clause="Section 3.0/5.0",
                    ))
            except ValueError:
                pass

        # Voltage — must match exactly
        spec_v, vendor_v = spec.get("voltage_v"), vendor.get("voltage_v")
        if spec_v and vendor_v and spec_v != vendor_v:
            deviations.append(Deviation(
                severity="critical",
                description="Voltage mismatch between specification and vendor submittal.",
                evidence=f"Specification requires {spec_v}V; vendor submittal specifies {vendor_v}V.",
                recommendation="Confirm the correct voltage rating with the vendor before approval.",
                document_ref="Submittal", page_number=1, spec_clause="Section 3.0",
            ))

        # Frequency — must match exactly
        spec_hz, vendor_hz = spec.get("frequency_hz"), vendor.get("frequency_hz")
        if spec_hz and vendor_hz and spec_hz != vendor_hz:
            deviations.append(Deviation(
                severity="major",
                description="Frequency mismatch between specification and vendor submittal.",
                evidence=f"Specification requires {spec_hz}Hz; vendor submittal specifies {vendor_hz}Hz.",
                recommendation="Verify frequency compatibility with site electrical infrastructure.",
                document_ref="Submittal", page_number=1, spec_clause="Section 3.0",
            ))

        # Redundancy — N < N+1 < N+2 < 2N
        rank = {"N": 0, "N+1": 1, "N+2": 2, "2N": 3, "2N+1": 4}
        spec_r, vendor_r = spec.get("redundancy"), vendor.get("redundancy")
        if spec_r and vendor_r:
            spec_r_n, vendor_r_n = spec_r.upper(), vendor_r.upper()
            if spec_r_n in rank and vendor_r_n in rank and rank[vendor_r_n] < rank[spec_r_n]:
                deviations.append(Deviation(
                    severity="critical",
                    description="Redundancy mismatch between specification and vendor submittal.",
                    evidence=f"Specification requires {spec_r} redundancy; vendor submittal offers only {vendor_r}.",
                    recommendation="Escalate to the client — this is a critical availability risk that typically requires a design change or waiver.",
                    document_ref="Submittal", page_number=1, spec_clause="Section 3.0/5.0",
                ))

        # Certification standards — spec-required standards must appear in vendor cert list
        spec_certs = {c.upper().replace(" ", "") for c in (spec.get("certifications") or [])}
        vendor_certs = {c.upper().replace(" ", "") for c in (vendor.get("certifications") or [])}
        missing_certs = spec_certs - vendor_certs
        if not vendor.get("certifications"):
            deviations.append(Deviation(
                severity="major",
                description="No certification standard detected in the vendor submittal.",
                evidence="Extracted submittal text does not reference UL, CE, CSA, IEC, or NEC certification.",
                recommendation="Request the vendor's certification package (UL/CE/CSA/IEC) before approval.",
                document_ref="Submittal", page_number=1, spec_clause="Section 2.0",
            ))
        elif missing_certs:
            deviations.append(Deviation(
                severity="minor",
                description="Certification standards referenced in the specification were not found in the submittal.",
                evidence=f"Specification references {', '.join(sorted(spec_certs))}; submittal only references {', '.join(sorted(vendor_certs)) or 'none'}.",
                recommendation="Confirm equivalent certification coverage with the vendor.",
                document_ref="Submittal", page_number=1, spec_clause="Section 2.0",
            ))

        return deviations

    def _llm_review(self, spec_text: str, vendor_text: str) -> List[Deviation]:
        """Use Groq to catch qualitative mismatches the regex checks can't (dimensions,
        material, missing documentation, incorrect standards, narrative discrepancies)."""
        if self.client is None:
            return []
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior EPC compliance engineer reviewing a vendor submittal "
                            "against a client specification for a data centre project. Identify only "
                            "deviations NOT already obviously covered by capacity/voltage/frequency/"
                            "redundancy/certification numeric checks -- focus on dimension mismatches, "
                            "material mismatches, missing required documentation, and incorrect or "
                            "unreferenced standards. Respond ONLY with a JSON object: "
                            '{"deviations": [{"category": str, "severity": "critical|major|minor", '
                            '"description": str, "evidence": str, "recommendation": str}]}. '
                            "If there are no additional deviations, return an empty list. Do not "
                            "invent facts that are not supported by the provided text."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"SPECIFICATION:\n{spec_text[:4000]}\n\nVENDOR SUBMITTAL:\n{vendor_text[:4000]}",
                    },
                ],
                temperature=0.1,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            out: List[Deviation] = []
            for item in data.get("deviations", [])[:5]:
                out.append(Deviation(
                    severity=str(item.get("severity", "minor")).lower(),
                    description=str(item.get("description", "Potential deviation identified by AI review.")),
                    evidence=str(item.get("evidence", "")),
                    recommendation=str(item.get("recommendation", "Review manually.")),
                    document_ref="Submittal", page_number=1,
                    spec_clause=str(item.get("category", "General")),
                ))
            return out
        except Exception:
            return []

    def _score(self, deviations: List[Deviation]) -> str:
        severities = [d.severity for d in deviations]
        if "critical" in severities:
            return "Fail"
        if severities:
            return "Warning"
        return "Pass"

    def _summarize(self, overall_score: str, deviations: List[Deviation]) -> str:
        if not deviations:
            return "Vendor submittal meets all checked specification requirements. No deviations detected."
        critical = sum(1 for d in deviations if d.severity == "critical")
        major = sum(1 for d in deviations if d.severity == "major")
        minor = sum(1 for d in deviations if d.severity == "minor")
        parts = []
        if critical:
            parts.append(f"{critical} critical")
        if major:
            parts.append(f"{major} major")
        if minor:
            parts.append(f"{minor} minor")
        return f"Compliance review found {', '.join(parts)} deviation(s) between the specification and vendor submittal. Overall result: {overall_score}."

    def _generate_pdf_report(self, report_id: str, payload: Dict[str, Any]) -> str:
        report_path = self.storage_dir / f"{report_id}.pdf"
        styles = getSampleStyleSheet()
        story = [Paragraph("Compliance Report", styles["Title"]), Spacer(1, 12)]
        story.append(Paragraph(f"Specification: {payload.get('spec_title', 'N/A')}", styles["Normal"]))
        story.append(Paragraph(f"Vendor Submittal: {payload.get('vendor_title', 'N/A')}", styles["Normal"]))
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Score: {payload.get('overall_score', 'Fail')}", styles["Heading2"]))
        story.append(Paragraph(payload.get("summary", ""), styles["Normal"]))
        story.append(Spacer(1, 12))
        rows = [["Severity", "Description", "Evidence", "Recommendation"]]
        for deviation in payload.get("deviations", []):
            rows.append([
                deviation.get("severity", "minor"),
                deviation.get("description", ""),
                deviation.get("evidence", "")[:200],
                deviation.get("recommendation", ""),
            ])
        table = Table(rows, repeatRows=1, colWidths=[60, 130, 160, 130])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)
        document = SimpleDocTemplate(str(report_path), pagesize=letter)
        document.build(story)
        return str(report_path)
