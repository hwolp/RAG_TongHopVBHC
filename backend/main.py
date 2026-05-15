from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import models
from database.db_config import engine
from database.schema_sync import sync_schema
from routers import admin, auth, chat, documents, jobs, manager, tags, users
from services.job_runner import start_internal_worker

models.Base.metadata.create_all(bind=engine)
sync_schema(engine)

app = FastAPI(title="RAG Hành Chính API", version="2.0", description="Hệ thống AI tổng hợp văn bản hành chính nội bộ")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(jobs.router)
app.include_router(tags.router)
app.include_router(manager.router)
app.include_router(admin.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def start_background_jobs():
    start_internal_worker()


@app.get("/")
def root():
    return {"status": "ok", "message": "Backend RAG v2.0 — Full RBAC — Running"}
