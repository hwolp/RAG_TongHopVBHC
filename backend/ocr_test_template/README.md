# OCR PDF to Word Test Template

Thu muc nay dung de test nhanh viec doc PDF/OCR:

- `input_pdfs/`: dat cac file PDF can test vao day.
- `word_output/`: script se xuat file `.docx` va `.txt` da extract/OCR vao day.
- `ocr_pdf_to_word.py`: script chuyen noi dung PDF sang Word de doi chieu.

## Cach chay

Tu thu muc `backend`:

```powershell
python ocr_test_template/ocr_pdf_to_word.py
```

Hoac chi dinh mot file PDF:

```powershell
python ocr_test_template/ocr_pdf_to_word.py --pdf "uploads/personal/example.pdf"
```

## Tuy chon huu ich

```powershell
# OCR tat ca cac trang, ke ca trang da co text layer
python ocr_test_template/ocr_pdf_to_word.py --ocr-mode always

# Chi lay text layer, khong OCR
python ocr_test_template/ocr_pdf_to_word.py --ocr-mode never

# Doi ngon ngu Tesseract
python ocr_test_template/ocr_pdf_to_word.py --lang vie+eng
```

Mac dinh script dung `--ocr-mode auto`: neu text layer cua trang ngan hon 500 ky tu thi se chay OCR.

## Cach doi chieu

1. Mo file `.docx` trong `word_output/`.
2. Kiem tra tung trang: script co ghi so ky tu text layer, so anh, va OCR co duoc chay hay khong.
3. Neu noi dung trong Word bi thieu hoac sai dau tieng Viet, kiem tra lai cai dat Tesseract va goi ngon ngu `vie`.

