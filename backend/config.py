import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class JWTSettings:
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int


@dataclass(frozen=True)
class DatabaseSettings:
    mysql_url: str


@dataclass(frozen=True)
class OllamaSettings:
    base_url: str
    model: str
    timeout_seconds: int


@dataclass(frozen=True)
class VectorSettings:
    chroma_persist_dir: str
    embedding_model_base_url: str
    embedding_model: str


@dataclass(frozen=True)
class JobSettings:
    redis_url: str
    rq_queue_name: str


@dataclass(frozen=True)
class UploadSettings:
    personal_dir: str
    department_dir: str
    sqp_dir: str


@dataclass(frozen=True)
class AppSettings:
    jwt: JWTSettings
    database: DatabaseSettings
    ollama: OllamaSettings
    vector: VectorSettings
    jobs: JobSettings
    uploads: UploadSettings


# === JWT Config ===
SECRET_KEY = _require_env("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "240"))

# === MySQL Config ===
MYSQL_URL = _require_env("MYSQL_URL")

# === Ollama Config ===
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0"))

# === ChromaDB Config ===
CHROMA_PERSIST_DIR = os.getenv("CHROMA_DIR", "./database/chromadb_storage")
EMBEDDING_MODEL_BASE_URL = os.getenv("EMBEDDING_MODEL_BASE_URL", "sentence-transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# === Background Jobs ===
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RQ_QUEUE_NAME = os.getenv("RQ_QUEUE_NAME", "rag_jobs")

# === Upload Directories ===
UPLOAD_DIR_PERSONAL = os.getenv("UPLOAD_DIR_PERSONAL", "uploads/personal")
UPLOAD_DIR_DEPARTMENT = os.getenv("UPLOAD_DIR_DEPARTMENT", "uploads/department")
UPLOAD_DIR_SQP = os.getenv("UPLOAD_DIR_SQP", "uploads/sqp")

APP_SETTINGS = AppSettings(
    jwt=JWTSettings(
        secret_key=SECRET_KEY,
        algorithm=ALGORITHM,
        access_token_expire_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
    ),
    database=DatabaseSettings(mysql_url=MYSQL_URL),
    ollama=OllamaSettings(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        timeout_seconds=OLLAMA_TIMEOUT_SECONDS,
    ),
    vector=VectorSettings(
        chroma_persist_dir=CHROMA_PERSIST_DIR,
        embedding_model_base_url=EMBEDDING_MODEL_BASE_URL,
        embedding_model=EMBEDDING_MODEL,
    ),
    jobs=JobSettings(redis_url=REDIS_URL, rq_queue_name=RQ_QUEUE_NAME),
    uploads=UploadSettings(
        personal_dir=UPLOAD_DIR_PERSONAL,
        department_dir=UPLOAD_DIR_DEPARTMENT,
        sqp_dir=UPLOAD_DIR_SQP,
    ),
)
