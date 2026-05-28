"""
Convert PDF extraction/OCR output to Word for manual OCR QA.

Run from backend:
    python ocr_test_template/ocr_pdf_to_word.py
"""
from __future__ import annotations

import argparse
import html
import io
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import fitz

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input_pdfs"
OUTPUT_DIR = ROOT / "word_output"
DEFAULT_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
OCR_CONFIGS = [
    "--oem 1 --psm 6 -c preserve_interword_spaces=1",
    "--oem 1 --psm 4 -c preserve_interword_spaces=1",
]

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


def page_needs_ocr(text: str, min_text_length: int) -> bool:
    return len(text.strip()) < min_text_length


def ocr_page(page: fitz.Page, lang: str, tesseract_cmd: str | None) -> str:
    if not TESSERACT_AVAILABLE:
        return "[OCR unavailable: pytesseract/Pillow is not installed]"

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    elif DEFAULT_TESSERACT.exists():
        pytesseract.pytesseract.tesseract_cmd = str(DEFAULT_TESSERACT)

    matrix = fitz.Matrix(3, 3)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    image = Image.open(io.BytesIO(pix.tobytes("ppm")))
    processed_image = prepare_ocr_image(image)
    return best_ocr_result(processed_image, lang)[0]


def prepare_ocr_image(image: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    gray = ImageEnhance.Contrast(gray).enhance(1.7)
    gray = ImageEnhance.Sharpness(gray).enhance(1.4)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return gray.point(lambda pixel: 255 if pixel > 168 else 0)


def best_ocr_result(image: Image.Image, lang: str) -> tuple[str, float, str]:
    best_text = ""
    best_score = -1.0
    best_config = OCR_CONFIGS[0]

    for config in OCR_CONFIGS:
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            config=config,
            output_type=pytesseract.Output.DICT,
        )
        confidences = []
        for confidence in data.get("conf", []):
            try:
                numeric_confidence = float(confidence)
            except (TypeError, ValueError):
                continue
            if numeric_confidence >= 0:
                confidences.append(numeric_confidence)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        text = pytesseract.image_to_string(image, lang=lang, config=config).strip()
        score = avg_confidence + min(len(text), 4000) / 4000
        if text and score > best_score:
            best_text = text
            best_score = score
            best_config = config

    return best_text, best_score, best_config


def iter_pdf_results(
    pdf_path: Path,
    ocr_mode: str,
    min_text_length: int,
    lang: str,
    tesseract_cmd: str | None,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    doc = fitz.open(pdf_path)
    try:
        for index, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            images = page.get_images()
            should_ocr = ocr_mode == "always" or (
                ocr_mode == "auto" and page_needs_ocr(text, min_text_length)
            )
            ocr_text = ocr_page(page, lang, tesseract_cmd) if should_ocr else ""
            combined_text = ocr_text if should_ocr and ocr_text else text
            if text and ocr_text:
                combined_text = f"{text}\n\n[OCR Result]\n{ocr_text}"

            results.append(
                {
                    "page": index,
                    "text_chars": len(text),
                    "image_count": len(images),
                    "ocr_ran": should_ocr,
                    "ocr_chars": len(ocr_text),
                    "content": combined_text or "[EMPTY PAGE]",
                }
            )
    finally:
        doc.close()
    return results


def paragraph_xml(text: str, style: str | None = None) -> str:
    safe_text = html.escape(text).replace("\n", "</w:t><w:br/><w:t>")
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{style_xml}<w:r><w:t>{safe_text}</w:t></w:r></w:p>"


def build_docx(paragraphs: list[tuple[str, str | None]], output_path: Path) -> None:
    body = "\n".join(paragraph_xml(text, style) for text, style in paragraphs)
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:rPr><w:b/><w:sz w:val="26"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Meta"><w:name w:val="Meta"/><w:rPr><w:color w:val="666666"/><w:sz w:val="20"/></w:rPr></w:style>
</w:styles>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", document_xml)
        docx.writestr("word/styles.xml", styles)


def write_outputs(pdf_path: Path, results: list[dict[str, object]], output_dir: Path) -> tuple[Path, Path]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_stem = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in pdf_path.stem)
    docx_path = output_dir / f"{safe_stem}_ocr_check_{timestamp}.docx"
    txt_path = output_dir / f"{safe_stem}_ocr_check_{timestamp}.txt"

    paragraphs: list[tuple[str, str | None]] = [
        (f"OCR check: {pdf_path.name}", "Title"),
        (f"Generated at: {datetime.now().isoformat(timespec='seconds')}", "Meta"),
        (f"Source: {pdf_path}", "Meta"),
    ]
    txt_lines = [f"OCR check: {pdf_path.name}", f"Source: {pdf_path}", ""]

    for result in results:
        heading = f"Page {result['page']}"
        meta = (
            f"text_chars={result['text_chars']} | images={result['image_count']} | "
            f"ocr_ran={result['ocr_ran']} | ocr_chars={result['ocr_chars']}"
        )
        content = str(result["content"])
        paragraphs.extend([(heading, "Heading1"), (meta, "Meta"), (content, None)])
        txt_lines.extend([heading, meta, content, ""])

    build_docx(paragraphs, docx_path)
    txt_path.write_text("\n".join(txt_lines), encoding="utf-8")
    return docx_path, txt_path


def find_input_pdfs() -> list[Path]:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(INPUT_DIR.glob("*.pdf"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Export PDF text/OCR result to Word for QA.")
    parser.add_argument("--pdf", type=Path, help="Path to one PDF file. Defaults to all PDFs in input_pdfs.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Output folder for docx/txt files.")
    parser.add_argument("--ocr-mode", choices=["auto", "always", "never"], default="auto")
    parser.add_argument("--min-text-length", type=int, default=500)
    parser.add_argument("--lang", default="vie+eng", help="Tesseract language, e.g. vie or vie+eng.")
    parser.add_argument("--tesseract-cmd", help="Full path to tesseract.exe if not in PATH.")
    args = parser.parse_args()

    pdfs = [args.pdf] if args.pdf else find_input_pdfs()
    if not pdfs:
        print(f"No PDF files found. Put PDFs in: {INPUT_DIR}")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for pdf_path in pdfs:
        if not pdf_path.exists():
            print(f"Missing PDF: {pdf_path}")
            continue
        print(f"Processing: {pdf_path}")
        results = iter_pdf_results(
            pdf_path=pdf_path,
            ocr_mode=args.ocr_mode,
            min_text_length=args.min_text_length,
            lang=args.lang,
            tesseract_cmd=args.tesseract_cmd,
        )
        docx_path, txt_path = write_outputs(pdf_path, results, args.output_dir)
        print(f"  Word: {docx_path}")
        print(f"  Text: {txt_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
