# OCR Setup for Scanned PDFs

## Problem

Van ban scan khong co text layer day du, nen `PyMuPDFLoader` co the doc thieu noi dung. Trang PDF co text ngan hon nguong se duoc render thanh anh va chay OCR truoc khi chunk/index.

## Engine hien tai

Backend hien dung Tesseract local qua `pytesseract`.

```env
OCR_RENDER_SCALE=3
TESSERACT_OCR_LANG=vie
TESSERACT_AUTO_DOWNLOAD_VIE=true
TESSERACT_TESSDATA_DIR=tessdata
TESSERACT_OCR_IMAGE_VARIANTS=grayscale,threshold
OCR_MAX_WORKERS=5
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

`TESSERACT_CMD`, `TESSERACT_OCR_LANG`, `TESSERACT_TESSDATA_DIR`, va `TESSERACT_OCR_IMAGE_VARIANTS` la tuy chon. Mac dinh backend dung ngon ngu `vie` va tu tai `vie.traineddata` tu `tessdata_best` ve `backend/tessdata/` trong lan OCR dau tien neu file chua ton tai. Nen uu tien `vie` thay vi `vie+eng` cho van ban hanh chinh tieng Viet, vi `eng` co the lam Tesseract nham dau tieng Viet va so La Ma trong heading.

## Quick Install

```powershell
cd backend
pip install -r requirements.txt
```

Can cai Tesseract binary tren may neu chua co:

```powershell
choco install tesseract
```

Hoac cai ban Windows tu UB Mannheim:

```text
https://github.com/UB-Mannheim/tesseract/wiki
```

## How It Works

1. `PyMuPDFLoader` doc text layer cua PDF.
2. Trang nao co text ngan hon `500` ky tu se duoc xem la scan.
3. Trang scan duoc render voi `OCR_RENDER_SCALE=3`.
4. Neu thieu `vie.traineddata`, backend tu tai ban `tessdata_best` ve `backend/tessdata/`.
5. Cac trang can OCR duoc chay song song theo `OCR_MAX_WORKERS`.
6. Tesseract OCR doc anh bang ngon ngu `vie`. Moi trang duoc cham diem qua 4 candidate: `grayscale + psm 6`, `grayscale + psm 4`, `threshold + psm 6`, va `threshold + psm 4`.
7. OCR text duoc hau xu ly cac loi pho bien nhu `Chuong HI` thanh `Chuong III`, sau do ghep vao `page_content` va di qua chunk/index.

## Troubleshooting

- Sau khi doi OCR setup, restart backend/worker de process moi nhan dependency/env moi.
- Neu log bao `pytesseract not available`, cai lai package trong dung virtualenv worker dang dung.
- Neu OCR tra ve rong, kiem tra Tesseract binary va file ngon ngu `vie.traineddata`.
- Neu moi truong khong co internet, dat san `vie.traineddata` vao thu muc `backend/tessdata/` hoac tat `TESSERACT_AUTO_DOWNLOAD_VIE=false`.
- Neu van mat dau tieng Viet tren trang scan, giu `TESSERACT_OCR_IMAGE_VARIANTS=grayscale,threshold`; tranh de threshold len truoc vi co the lam mat net dau mu, dau sac.
- Neu may bi day CPU/RAM khi index file lon, giam `OCR_MAX_WORKERS` xuong `1` hoac `2`.
