# Chay embedding model local sau lan dau

Backend dung `HuggingFaceEmbeddings` voi model mac dinh:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Luồng da duoc cau hinh:

1. Khi khoi dong, backend thu load model tu cache local truoc.
2. Neu cache chua co va `EMBEDDING_MODEL_ALLOW_DOWNLOAD=true`, backend se tai model tu internet.
3. Model duoc luu vao `EMBEDDING_MODEL_CACHE_DIR`.
4. Cac lan chay sau se load lai tu cache, khong can tai lai.

## Cau hinh khuyen nghi

Trong `backend/.env`:

```dotenv
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_MODEL_CACHE_DIR=./models/huggingface
EMBEDDING_MODEL_ALLOW_DOWNLOAD=true
```

Duong dan tuong doi cua `EMBEDDING_MODEL_CACHE_DIR` duoc tinh tu thu muc
`backend`, nen cau hinh tren se luu model vao `backend/models/huggingface` du
ban khoi dong app tu root hay tu `backend`.

Lan dau chay can co internet. Sau khi model da tai xong, neu muon ep server chay
offline hoan toan, doi thanh:

```dotenv
EMBEDDING_MODEL_ALLOW_DOWNLOAD=false
```

Khi do neu model trong cache bi thieu file, backend se bao loi ngay thay vi thu
ket noi internet.

## Kiem tra model da duoc cache

Sau lan chay dau, kiem tra thu muc:

```powershell
Get-ChildItem backend\models\huggingface -Recurse | Select-Object -First 20
```

Thu muc `backend/models/` da duoc ignore trong git vi model co kich thuoc lon.
