from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database.init_db import init_db
from backend.api.routes import router
from backend.api.connector_routes import router as connector_router
from backend.api.schedule_routes import router as schedule_router
from backend.api.structured_routes import router as structured_router

app = FastAPI(title="AI Document Intelligence Hub", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(connector_router)
app.include_router(schedule_router)
app.include_router(structured_router)

@app.on_event("startup")
def startup_event() -> None:
    init_db()

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
