import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# === JWT Config ===
SECRET_KEY = _require_env("SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "240"))

# === MySQL Config ===
MYSQL_URL = _require_env("MYSQL_URL")

# === Ollama Config ===
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")

# === ChromaDB Config ===
CHROMA_PERSIST_DIR = os.getenv("CHROMA_DIR", "./database/chromadb_storage")
EMBEDDING_MODEL_BASE_URL = os.getenv("EMBEDDING_MODEL_BASE_URL", "sentence-transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# === Upload Directories ===
UPLOAD_DIR_PERSONAL = os.getenv("UPLOAD_DIR_PERSONAL", "uploads/personal")
UPLOAD_DIR_DEPARTMENT = os.getenv("UPLOAD_DIR_DEPARTMENT", "uploads/department")
UPLOAD_DIR_SQP = os.getenv("UPLOAD_DIR_SQP", "uploads/sqp")
