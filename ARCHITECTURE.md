# Data-Centre Construction Project Intelligence Platform

```mermaid
flowchart LR
    A["Documents, PDFs, scans, images, CSV, JSON, emails"] --> B["Document Hub Upload + Preview"]
    B --> C["Extraction Layer"]
    C --> C1["PDF/Text/CSV/XLSX/DOCX parsers"]
    C --> C2["OCR for scans and images"]
    C --> C3["Gemini multimodal for drawings when API key exists"]
    C1 --> D["Unified SQLite DB Hub"]
    C2 --> D
    C3 --> D
    D --> D1["Equipment, vendors, requirements, standards"]
    D --> E["Spec Compliance Agent"]
    D1 --> E1["Deterministic Rule Engine + severity score"]
    E --> E1
    E1 --> E2["Groq explanation/review when configured"]
    E2 --> D
    D --> F["FAISS Vector Store in backend/vector_store"]
    F --> G["RAG Knowledge Assistant"]
    G --> G1["Groq Llama 3.1 8B Instant generation"]
    D --> H["Schedule Risk Engine"]
    D --> I["Procurement Agent"]
    D --> J["Communication Intelligence Agent"]
    H --> K["Smart Notifications + Dashboard KPIs"]
    I --> K
    J --> K
    E --> K
    K --> L["UI: dashboard, documents, compliance, schedule, procurement, communications, knowledge, chat, reports, settings"]
    D --> M["Quarto Report Generator"]
    M --> L
```

All module outputs are persisted in `backend/ai_monitoring.db`. The vector chunks and FAISS index are persisted in `backend/vector_store/`. Existing DBs are migrated and backfilled on `hub.initialize()` so extracted documents gain equipment/vendor/standard records and deterministic rule evaluations without deleting prior data.
