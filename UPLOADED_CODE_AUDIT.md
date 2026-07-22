# Uploaded Code Audit Checklist

This file is the working checklist for the supplied folders and zip contents.

## DataCentre Completed

- Integrated: document storage, sample PDFs, compliance PDF, metadata fields, document preview/download, extraction-to-DB flow.
- Integrated: compliance issue creation with severity/evidence/recommendation/reference.
- Integrated: RAG chunk storage and FAISS/vector-store update.
- Integrated: schedule/procurement CSV sample ingestion.
- Integrated: Quarto/report artifact concepts.
- Not directly mounted: its standalone FastAPI app/routes, because the unified app serves one cohesive `/api/v1/intelligence/*` API.

## F2ET

- Integrated: project monitoring shell, dashboard module layout, procurement/schedule/risk concepts, notification concepts.
- Integrated: delivery-map behavior into the served procurement route map.
- Integrated: SMTP email notification flow.
- Partially integrated: SQLAlchemy/Celery/Redis/Postgres app stack. The code remains available in `platform/backend/app/*`, but the unified prototype uses SQLite for the single DB hub requested.
- Not directly mounted: legacy auth/projects/suppliers pages as separate workflows, because they duplicate the unified local demo flow.

## ethack

- Integrated: OCR/PDF parser pattern.
- Integrated: Gemini multimodal drawing/image analysis prompt.
- Integrated: deterministic rule engine and severity-weighted scoring concepts.
- Integrated: equipment/vendor/requirement/standard/evidence concepts as SQLite hub tables.
- Integrated: Gmail reader through `/communications/import-gmail`.
- Integrated: email sender and SMS/WhatsApp stubs, extended into SMTP and Twilio-compatible delivery.
- Integrated: report generation behavior, with Quarto first and PyMuPDF PDF fallback.
- Not directly mounted: Postgres/Alembic/pgvector runtime, because the unified MVP is intentionally SQLite.

## New Unified Features Added From Audit

- `/appointments`: engineer appointment scheduling.
- `/sustainability`: AI impact/water-consumption awareness analytics.
- `/settings`: integration-key configuration for Groq, Gemini, OpenWeather, SMTP, Twilio.
- `/procurement`: OpenWeather risk summary and route map.
- `/communications`: Gmail import.
- `/notifications/dispatch`: email/SMS/WhatsApp delivery attempts.

## Final Runtime Verification

- Groq, FAISS, SentenceTransformers, Google Generative AI, Google OAuth, dotenv, and Twilio now import from `platform/backend/vendor`.
- The supplied Groq, Gemini, and OpenWeather keys were placed in `platform/backend/.env`; keys are not printed in UI or logs.
- OpenWeather is live in `/procurement`; the smoke check returned `source: openweather` and weather risk metrics are displayed in the Procurement module.
- Gemini multimodal is wired to the uploaded drawing-analysis prompt and called during image ingestion. On this machine, the live Google SDK call times out because Python/gRPC cannot validate the local TLS certificate chain; the application now caps the Gemini subprocess at 15 seconds and records the runtime error instead of hanging.
- SentenceTransformers and FAISS are installed. If `all-MiniLM-L6-v2` cannot be downloaded because of the same local TLS trust issue, RAG falls back to deterministic local embeddings while retaining FAISS/vector-store files.
- Twilio notification delivery is wired, but SMS/WhatsApp delivery is skipped until `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, and `ALERT_RECIPIENT_PHONE` are configured.
- Gmail import is wired through the uploaded reader path. If Google OAuth credentials/token are missing, `/communications/import-gmail` imports the sample email CSV so the communications flow remains testable.
- Served UI verification passed for `/dashboard`, `/documents`, `/procurement`, `/communications`, `/appointments`, `/sustainability`, `/chat`, and `/settings`.

## Files Excluded With Reason

- `node_modules`, `.venv`, `__pycache__`, compiled bundles, generated logs, and cache folders are excluded from feature integration because they are dependency/runtime artifacts, not source features.
- Duplicate legacy app entrypoints are preserved but not served by default to avoid two separate applications fighting over navigation, authentication, DB schema, and routes.
