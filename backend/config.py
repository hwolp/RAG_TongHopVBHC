import os

# === JWT Config ===
SECRET_KEY = os.getenv("SECRET_KEY", "HanhChinh_BaoMat_Sieu_Cap_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240

# === MySQL Config ===
MYSQL_URL = os.getenv("MYSQL_URL", "mysql+pymysql:///rag_db")

# === Ollama Config ===
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")

# === ChromaDB Config ===
CHROMA_PERSIST_DIR = os.getenv("CHROMA_DIR", "./database/chromadb_storage")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# === Upload Directories ===
UPLOAD_DIR_PERSONAL = "uploads/personal"
UPLOAD_DIR_DEPARTMENT = "uploads/department"
UPLOAD_DIR_SQP = "uploads/sqp"
