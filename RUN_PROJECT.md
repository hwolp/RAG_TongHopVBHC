# Huong dan chay du an RAG Tong Hop VBHC

Tai lieu nay huong dan chay day du tu tao file `.env`, khoi tao database, cai
model lan dau, chay Backend va Frontend. Du an khong dung Docker; MySQL va
Ollama can chay truc tiep tren may. Background job duoc luu va xu ly truc tiep
tu database.

## 1. Yeu cau moi truong

Can cai san:

- Python 3.10+.
- Node.js 20+ va npm.
- MySQL 8.0.
- Ollama.
- Tesseract OCR, neu can xu ly OCR.

## 2. Chay cac service nen

Can dam bao cac service sau dang chay:

- MySQL: `localhost:3306`
- Ollama: `http://localhost:11434`

Kiem tra Ollama:

```powershell
ollama list
```

Kiem tra MySQL:

```powershell
mysql -u root -p -e "SELECT VERSION();"
```

## 3. Tao database lan dau

Mo terminal tai thu muc root project:

```powershell
cd "D:\Nam3\Ky_2\Quản Lý Dự Án\Demo\RAG_TongHopVBHC"
```

Chay file query khoi tao database:

```powershell
mysql -u root -p < backend/database/init_database.sql
```

File nay tao database `rag_db`. Cac bang se duoc Backend tu tao khi start bang
SQLAlchemy ORM.

## 4. Tao file Backend .env

Tao file:

```text
backend/.env
```

Noi dung mau:

```dotenv
SECRET_KEY=change-this-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=240

MYSQL_URL=mysql+pymysql://root:your_password@localhost:3306/rag_db

OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b-instruct-q4_K_M
OLLAMA_TIMEOUT_SECONDS=600
OLLAMA_TEMPERATURE=0

CHROMA_DIR=./database/chromadb_storage

EMBEDDING_MODEL=dangvantuan/vietnamese-document-embedding
EMBEDDING_MODEL_CACHE_DIR=./models/huggingface
EMBEDDING_MODEL_ALLOW_DOWNLOAD=true

ENABLE_INTERNAL_JOB_WORKER=true
INTERNAL_JOB_WORKER_INTERVAL_SECONDS=2
INTERNAL_JOB_WORKER_BATCH_SIZE=3
INTERNAL_JOB_WORKER_COUNT=2

UPLOAD_DIR_PERSONAL=uploads/personal
UPLOAD_DIR_DEPARTMENT=uploads/department
UPLOAD_DIR_SQP=uploads/sqp
```

Neu MySQL root khong co mat khau, dung:

```dotenv
MYSQL_URL=mysql+pymysql://root@localhost:3306/rag_db
```

## 5. Cai Backend

Tao va kich hoat virtual environment:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Cai thu vien:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Cai model Ollama lan dau

Tai model Ollama:

```powershell
ollama pull qwen2.5:3b-instruct-q4_K_M
```

Kiem tra model:

```powershell
ollama list
```

## 7. Cai embedding model lan dau

Khong can chay lenh rieng. Khi Backend can embedding lan dau, no se:

1. Thu doc model tu cache local.
2. Neu cache chua co va may co internet, tu tai
   `dangvantuan/vietnamese-document-embedding`.
3. Luu vao `backend/models/huggingface`.
4. Cac lan sau dung lai cache local.

Sau khi tai xong, neu muon ep chay offline, sua trong `backend/.env`:

```dotenv
EMBEDDING_MODEL_ALLOW_DOWNLOAD=false
```

## 8. Seed du lieu mau

Trong terminal dang kich hoat `.venv` va dang o thu muc `backend`:

```powershell
python seed.py
```

Tai khoan mau:

- `admin / admin123`
- `tp_nhansu / manager123`
- `nv_ketoan / nv123`

## 9. Chay Backend

Trong terminal dang kich hoat `.venv` va dang o thu muc `backend`:

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Kiem tra Backend:

```text
http://localhost:8000
http://localhost:8000/docs
```

Luu y: Frontend hien co mot so duong dan hard-code toi `http://localhost:8000`,
nen nen giu Backend o port `8000`.

## 10. Tao file Frontend .env

Tao file:

```text
frontend/.env
```

Noi dung:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

## 11. Cai va chay Frontend

Mo terminal moi tai root project:

```powershell
cd frontend
npm install
npm run dev
```

Frontend mac dinh chay tai:

```text
http://localhost:5173
```

## 12. Thu tu chay moi lan sau

Moi lan mo lai project, dam bao MySQL va Ollama dang chay. Sau do:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Mo terminal khac:

```powershell
cd frontend
npm run dev
```

Sau do vao:

```text
http://localhost:5173
```

## 13. Build Frontend

Khi can build ban production:

```powershell
cd frontend
npm run build
```

Thu muc output:

```text
frontend/dist
```

## 14. Loi thuong gap

Neu Backend loi ket noi MySQL:

- Kiem tra MySQL da chay chua.
- Kiem tra `MYSQL_URL` trong `backend/.env`.
- Chay lai `backend/database/init_database.sql`.

Neu Backend loi ket noi Ollama:

- Kiem tra `http://localhost:11434`.
- Kiem tra model da pull chua bang `ollama list`.

Neu lan dau embedding model tai cham:

- Day la binh thuong vi model `all-MiniLM-L6-v2` dang duoc tai ve cache.
- Cac lan sau se nhanh hon vi dung cache local.

Neu Frontend goi API that bai:

- Dam bao Backend dang chay o `http://localhost:8000`.
- Dam bao `frontend/.env` co `VITE_API_BASE_URL=http://localhost:8000`.
