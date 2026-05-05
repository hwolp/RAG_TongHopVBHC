# OCR Setup for Scanned PDFs

## Problem
Hầu hết văn bản hành chính VN là bản scan → `PyMuPDFLoader` chỉ extract text layer, không OCR ảnh → mất gần hết nội dung.

## Solution
Enable OCR support cho trang PDF scan (tự động detect + extract).

## Quick Install (Windows)

### Option 1: Tesseract (Recommended for Windows)

1. **Download & Install Tesseract:**
   - https://github.com/UB-Mannheim/tesseract/wiki
   - Hoặc chạy: `choco install tesseract` (nếu có Chocolatey)
   - Default install path: `C:\Program Files\Tesseract-OCR`

2. **Install pytesseract (Python wrapper):**
   ```powershell
   pip install pytesseract pdf2image
   ```

3. **Update backend/rag_engine/chroma_manager.py** — Replace OCR import:
   ```python
   # Replace the EasyOCR section with:
   try:
       import pytesseract
       from PIL import Image
       PYTESSERACT_AVAILABLE = True
   except ImportError:
       PYTESSERACT_AVAILABLE = False
       logging.warning("pytesseract not installed — OCR disabled")
   ```

4. **Update `_get_ocr_reader()` function:**
   ```python
   def _get_ocr_reader():
       """Return pytesseract (no lazy loading needed)."""
       return pytesseract if PYTESSERACT_AVAILABLE else None
   ```

5. **Update `_ocr_page_to_text(page)` function:**
   ```python
   def _ocr_page_to_text(page) -> str:
       """OCR PDF page using Tesseract."""
       reader = _get_ocr_reader()
       if reader is None:
           logging.warning("Tesseract not available, skipping OCR")
           return ""
       
       try:
           # Convert PDF page → PIL Image
           pix = page.get_pixmap(matrix=None, alpha=False, clip=None)
           img_data = pix.tobytes("ppm")
           img = Image.open(io.BytesIO(img_data))
           
           # Extract text
           text = pytesseract.image_to_string(img, lang='vie')
           return text
       except Exception as e:
           logging.error(f"OCR failed: {e}")
           return ""
   ```

### Option 2: EasyOCR (Pure Python, no binary needed)

⚠️ **Note:** EasyOCR has heavy build dependencies (`python-bidi`). May require build tools.

```powershell
# Install build tools first (if needed)
pip install --upgrade setuptools wheel

# Then install easyocr
pip install easyocr --no-build-isolation --prefer-binary
```

### Option 3: Cloud OCR (Google Vision, Azure, AWS Textract)

Dùng cloud OCR service:
```python
# Modify _ocr_page_to_text() để call cloud API
# Example: Google Cloud Vision API
```

## How It Works

**Automatic Detection:**
```python
# In process_and_store_pdf():
if _is_page_scanned(page_text):  # Detected < 500 chars
    ocr_text = _ocr_page_to_text(page)
    page.content = original_text + "\n[OCR Result]\n" + ocr_text
```

**Chunking:**
- Văn bản hành chính (Điều/Khoản) → administrative chunking
- Văn bản thường → normal chunking

## Testing

```bash
# Without OCR (default):
python main.py  # Will warn about OCR not available

# With Tesseract:
# (After installing Tesseract binary + pytesseract)
python main.py  # Will auto-detect and OCR scan pages
```

## Performance Notes

| Approach | Speed | Quality | Dependencies |
|----------|-------|---------|---|
| No OCR | ✅ Fast | ❌ Poor for scans | None |
| Tesseract | 🟡 ~2-3s/page | ✅ Good | Binary + pytesseract |
| EasyOCR | 🟡 ~3-5s/page | ✅ Excellent | Heavy (torch + deps) |
| Cloud | 🟡 ~500ms/page | ✅ Excellent | API key + network |

---

**Status:** OCR is **completely optional**. System works fine without it (will log warnings). Enable only if processing many scanned PDFs.
