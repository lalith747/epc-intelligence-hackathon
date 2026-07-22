# Integration Audit

This audit tracks how the supplied code/archive capabilities are wired into the unified prototype.

## Integrated Sources

- `DataCentre_completed.zip`: copied into `backend/app/integrations/document_hub` and used as the source for the compliance PDF, project PDFs, schedule/procurement CSVs, RFI workbook, meeting minutes, and document storage seed set.
- `F2ET.zip`: used as the base application structure for the project monitoring UI/backend layout.
- `ethack (2).zip`: audited and source-selected for OCR/PDF parsing behavior, Gemini vision behavior, deterministic compliance rules, severity scoring, vendor/equipment/standard concepts, notifications, RAG, and report generation.

## Feature-Level Audit

| Uploaded source | Feature/code found | Integration status | Notes |
|---|---|---|---|
| DataCentre completed | Document hub APIs, storage, metadata extraction, compliance PDF, sample construction docs | Integrated | Seeded into unified SQLite DB and exposed through `/documents`, `/documents/{id}`, `/compliance`, RAG, reports |
| DataCentre completed | Compliance service and rule/comparison behavior | Integrated | Unified into heuristic + deterministic rule + optional Groq review pipeline |
| DataCentre completed | RAG service concepts | Integrated | FAISS/sentence-transformer path plus hash fallback stored in `backend/vector_store/` |
| DataCentre completed | Schedule/procurement structured CSV routes | Integrated | Used as sample sources; sparse files are augmented so the demo exercises real risk logic |
| F2ET | Dashboard, schedule, procurement, risk, recommendation, conversation agents | Partially integrated | Core analytics concepts are integrated into the unified hub; original SQLAlchemy/Celery agent runtime is not mounted because the prototype runs one SQLite DB without the legacy project schema |
| F2ET | Leaflet delivery map implementation | Integrated | Reused route/marker/status concepts in the served procurement map; React source remains corrected for future Vite builds |
| F2ET | SMTP notification delivery | Integrated | Unified notification dispatch now attempts SMTP when configured |
| F2ET | Projects/suppliers/auth legacy screens | Not mounted by default | Replaced by local demo project/user mode to keep the unified prototype single-flow and avoid duplicate navigation/auth stacks |
| ethack | Gemini multimodal drawing analyzer and vision prompts | Integrated | Drawing/image uploads now use the richer engineering diagram prompt when Gemini key is configured |
| ethack | OCR/PDF parser pattern | Integrated | Native PDF first, OCR fallback, image OCR/Gemini fallback |
| ethack | Gmail reader | Integrated | `/communications/import-gmail` reuses the adapter when OAuth credentials exist; otherwise imports sample email CSV |
| ethack | Deterministic rule engine and scoring | Integrated | Rule evaluations, vendor submittal scores, requirements, standards are first-class DB tables and `/knowledge` UI records |
| ethack | Email/SMS/WhatsApp notification stubs | Integrated/extended | Email integrated through SMTP; SMS/WhatsApp upgraded to Twilio-compatible dispatch when credentials are configured |
| ethack | Report generators | Integrated | Quarto-first report generation; PyMuPDF PDF fallback if Quarto is unavailable |
| ethack | Postgres/pgvector/Alembic full schema | Not mounted by default | The requested MVP uses a single SQLite DB hub; schema concepts were ported into SQLite tables |
| All archives | `node_modules`, `.venv`, `__pycache__`, build artifacts | Not integrated | Dependency/build/cache files are intentionally excluded from app logic |

## Newly Connected In Latest Pass

- Gemini multimodal prompt upgraded with uploaded ethack diagram-analysis instructions.
- OpenWeather procurement weather-risk integration added, with persisted weather snapshots and fallback signals.
- Procurement map replaced with a route/marker/weather visualization based on F2ET delivery-map behavior.
- Gmail import route added, using the uploaded Gmail adapter where credentials are available.
- Twilio-compatible SMS/WhatsApp notification delivery added behind smart notifications.
- Engineer appointment table, API, and UI page added.
- AI sustainability/impact analytics page added, including water-consumption awareness.
- Settings page can write Groq, Gemini, OpenWeather, SMTP, and Twilio keys to `backend/.env`.

## Active End-To-End Flow

1. `/documents` upload preview extracts text/metadata without committing.
2. Commit upload stores the file in the document hub and inserts `intelligence_documents`.
3. Extracted text is chunked into `intelligence_chunks`.
4. Communications documents populate `action_items`.
5. Equipment and standards metadata populate `equipment_assets`, `vendor_submittals`, and `engineering_standards`.
6. Compliance runs heuristic checks, ethack-style deterministic rules, and optional Groq review.
7. Rule results are persisted to `rule_evaluations`; compliance flags go to `compliance_issues`.
8. RAG rebuilds `backend/vector_store/chunks.json` and FAISS index when available.
9. Schedule/procurement engines read seeded structured CSVs, augment sparse supplied data, combine procurement/workforce/weather signals, and generate risk overlays.
10. Notifications are regenerated from compliance, schedule, procurement risk, and overdue communication action items.
11. Dashboard, module pages, chat, and reports all read from the same SQLite DB hub.

## Verification Snapshot

Latest smoke test:

- Documents: 50
- Chunks: 227
- Compliance issues: 34
- Action items: 11
- Notifications: 37
- Equipment assets: 24
- Vendor submittals: 24
- Requirements: 6
- Standards: 8
- Rule evaluations: 68
- Report generation: verified PDF fallback when Quarto is unavailable

Verified routes:

- `/dashboard`
- `/documents`
- `/compliance`
- `/schedule`
- `/procurement`
- `/communications`
- `/knowledge`
- `/appointments`
- `/sustainability`
- `/chat`
- `/reports`
- `/settings`
- all backing `/api/v1/intelligence/*` endpoints used by those pages
