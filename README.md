# Unified AI Data-Centre Project Intelligence Platform

This is a cohesive FastAPI-powered prototype for data-centre construction intelligence. It integrates the supplied document intelligence code patterns, OCR extraction, Gemini multimodal hooks, Groq compliance/RAG generation, FAISS vector storage, schedule risk, procurement intelligence, communications extraction, smart notifications, and Quarto report generation.

## What Is Included

- Backend: FastAPI, SQLite unified DB, document extraction, deterministic rule compliance, Groq compliance review, FAISS-ready RAG, schedule/procurement/communications engines, smart notification endpoint, and Quarto report endpoint.
- Frontend: a backend-served SPA in `frontend/dist` with top bar, project switcher, global search, notification panel, floating chat drawer, and pages for `/dashboard`, `/documents`, document viewer, `/compliance`, `/schedule`, `/procurement`, `/communications`, `/knowledge`, `/chat`, `/reports`, and `/settings`.
- Optional React/Vite source remains in `frontend/src` for future component development, but the verified run path does not depend on npm.
- Default sample data: supplied PDFs, `sample_drawing.png`, schedule/procurement CSVs, workforce/weather CSVs, RFI workbook, meeting minutes, vendor datasheet PDF, compliance PDF, plus a small sample email CSV for effortless communication-agent testing.
- Architecture diagram: see `ARCHITECTURE.md`.

## Environment Variables

Create `backend/.env`:

```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
GOOGLE_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-1.5-flash
OPENWEATHER_API_KEY=your_openweather_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_FROM_NUMBER=your_twilio_sms_number
ALERT_RECIPIENT_PHONE=recipient_phone
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
DATABASE_URL=sqlite+aiosqlite:///./ai_monitoring.db
SEED_DEMO_DATA=true
```

The app still runs without API keys. Without `GROQ_API_KEY`, RAG uses extractive local answers. Without `GEMINI_API_KEY`/`GOOGLE_API_KEY`, image/drawing processing uses OCR/text extraction. Without `OPENWEATHER_API_KEY`, procurement uses persisted fallback weather signals. Without Twilio/SMTP, notifications stay in-app and delivery attempts are logged as skipped. If Quarto is not installed or not on PATH, report generation produces a fallback PDF through PyMuPDF.

For this local workspace, Groq, Gemini, and OpenWeather keys have been configured in `backend/.env`. The runtime dependencies that were missing from the base interpreter were installed into `backend/vendor`, and `app/services/intelligence_hub.py` prepends that folder to `sys.path` at startup.

If the local Windows/Python certificate store cannot validate external TLS certificates, Gemini multimodal and Hugging Face model downloads may fail before they reach the API. The platform handles this without blocking ingestion: Gemini drawing analysis is time-bounded, and RAG falls back to local deterministic embeddings while keeping FAISS/vector-store files current.

## Run Locally

From `platform/backend`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.unified_main:app --host 127.0.0.1 --port 8010
```

`app.unified_main:app` is the verified cohesive prototype entrypoint for the unified intelligence platform. The original project-monitoring entrypoint remains available as `app.main:app` if you also want to run the legacy F2ET routes and install their full dependency set.

Open `http://127.0.0.1:8010/dashboard`.

## Default Login

The frontend is configured for local demo mode and opens directly with:

- User: `admin@example.com`
- Password if using the original auth page: `Admin@123`

## How To Test The End-To-End Flow

1. Start the backend with the command above. It serves both API and UI.
2. Open `/documents`. The hub seeds supplied sample files on first startup.
3. Use the upload panel to preview a PDF, CSV, JSON, DOCX, XLSX, or image before committing it to the DB.
4. Commit the upload. Upload triggers extraction, metadata persistence, automatic compliance check, communication extraction if relevant, notification refresh, and vector rebuild.
5. Open `/compliance`. Review flags grouped by source document with severity, evidence, and recommendations.
6. Open `/schedule`. Inspect the Gantt-style risk overlay and mitigation suggestions.
7. Open `/procurement`. Review Kanban lanes, shipment map markers, supplier scorecards, and critical-path procurement delay flags.
8. Open `/communications`. Review action items and similar RFI links extracted from emails/RFIs/meeting minutes.
9. Use `Import Gmail` on `/communications` to run the uploaded read-only Gmail adapter; if OAuth credentials are not available, the sample email export is imported.
10. Open `/knowledge`. Review extracted equipment assets, vendor submittals, engineering requirements, standards, and deterministic rule evaluations.
11. Open `/appointments`. Review or add engineer review appointments tied to risks/issues.
12. Open `/sustainability`. Review AI usage, estimated electricity/water impact, and responsible AI guidance.
13. Open `/chat` or the floating chat drawer. Try: `What is the redundancy requirement for UPS in Hall 3?`
14. Open `/reports` and generate the default weekly report for the last 7 days.

## Integrated Supplied Modules

- Document extraction logic from the supplied DataCentre backend was integrated into `app/services/intelligence_hub.py`.
- OCR/PDF/image handling follows the supplied ethack OCR/PDF parser pattern: native PDF text first, OCR for scans/images, and Gemini multimodal when configured.
- Gemini drawing/schematic analysis uses the richer uploaded ethack diagram prompt and feeds extracted visual insight into the DB/RAG/compliance pipeline.
- Procurement uses the F2ET delivery-map model and OpenWeather integration for route/weather risk.
- Email import reuses the uploaded ethack Gmail reader adapter and SMTP notification code paths.
- Twilio-compatible SMS/WhatsApp dispatch is wired behind smart notifications when credentials are configured.
- Compliance now includes ethack-style deterministic rule evaluations, severity-weighted vendor submittal status, and Groq review using `llama-3.1-8b-instant`.
- Equipment, vendor submittal, engineering requirement, engineering standard, and rule evaluation data are stored as first-class DB hub tables and exposed through `/api/v1/intelligence/equipment`, `/vendors`, `/requirements`, `/standards`, and `/compliance/rule-evaluations`.
- RAG persists chunks into `backend/vector_store/` and uses `sentence-transformers/all-MiniLM-L6-v2` with FAISS when available.
- Schedule/procurement/UI shell and demo project structure came from the supplied F2ET project-monitoring app.
- Quarto report generation is called from Python through the `quarto` CLI. When Quarto is unavailable, the platform still generates a PDF report with PyMuPDF and stores it in report history.

## Key Files

- `backend/app/services/intelligence_hub.py`
- `backend/app/api/endpoints/intelligence.py`
- `frontend/dist/index.html`
- `frontend/dist/assets/app.js`
- `frontend/dist/assets/app.css`
- `frontend/src/pages/intelligence/*`
- `frontend/src/components/chat/FloatingChat.tsx`
- `ARCHITECTURE.md`
- `INTEGRATION_AUDIT.md`
