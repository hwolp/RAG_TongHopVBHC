import io
import logging
import re

import fitz
from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_engine.models import DocumentIndexMetadata

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not installed; OCR for scanned PDFs disabled")


_ADMIN_DOC_PATTERNS = [
    r"\bĐiều\s+\d+",
    r"\bKhoản\s+\d+",
    r"\bĐiểm\s+[a-zđ]\)",
    r"\bNghị\s+định\b",
    r"\bThông\s+tư\b",
    r"\bQuyết\s+định\b",
    r"\bQuy\s+chế\b",
    r"\bQuy\s+định\b",
    r"\bNội\s+quy\b",
]

_NORMAL_SEPARATORS = ["\n\n", "\n", ".", " "]
_OCR_LANG = "vie+eng"
_OCR_CONFIGS = [
    "--oem 1 --psm 6 -c preserve_interword_spaces=1",
    "--oem 1 --psm 4 -c preserve_interword_spaces=1",
]
_OCR_ACCEPT_MIN_CHARS = 80
_OCR_ACCEPT_MIN_CONFIDENCE = 55.0
_ADMIN_CHUNK_SIZE = 1600
_ADMIN_CHUNK_OVERLAP = 250
_NORMAL_CHUNK_SIZE = 1800
_NORMAL_CHUNK_OVERLAP = 300


def _ocr_page_to_text(page) -> str:
    if not TESSERACT_AVAILABLE:
        logging.warning("pytesseract not available, skipping OCR")
        return ""

    try:
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        matrix = fitz.Matrix(3, 3)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("ppm")))
        processed_img = _prepare_ocr_image(img)
        extracted_text, confidence = _best_ocr_result(processed_img)
        if extracted_text:
            logging.info(
                "Page %s OCR success: %s chars extracted, confidence %.1f",
                page.number,
                len(extracted_text),
                confidence,
            )
        else:
            logging.warning("Page %s OCR completed but returned no text", page.number)
        return extracted_text
    except Exception as exc:
        logging.error("OCR failed at page %s: %s", page.number, exc)
        return ""


def _prepare_ocr_image(image: Image.Image) -> Image.Image:
    """Improve Vietnamese OCR by normalizing scanned PDF page images."""
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    gray = ImageEnhance.Contrast(gray).enhance(1.7)
    gray = ImageEnhance.Sharpness(gray).enhance(1.4)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return gray.point(lambda pixel: 255 if pixel > 168 else 0)


def _ocr_with_config(image: Image.Image, config: str) -> tuple[str, float]:
    data = pytesseract.image_to_data(
        image,
        lang=_OCR_LANG,
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
    text = pytesseract.image_to_string(image, lang=_OCR_LANG, config=config).strip()
    return text, avg_confidence


def _is_ocr_result_good_enough(text: str, confidence: float) -> bool:
    return len(text.strip()) >= _OCR_ACCEPT_MIN_CHARS and confidence >= _OCR_ACCEPT_MIN_CONFIDENCE


def _ocr_result_score(text: str, confidence: float) -> float:
    return confidence + min(len(text), 4000) / 4000


def _best_ocr_result(image: Image.Image) -> tuple[str, float]:
    if not _OCR_CONFIGS:
        return "", 0.0

    best_text, best_confidence = _ocr_with_config(image, _OCR_CONFIGS[0])
    if _is_ocr_result_good_enough(best_text, best_confidence):
        return best_text, best_confidence

    best_score = _ocr_result_score(best_text, best_confidence)
    logging.info(
        "Primary OCR result weak: %s chars, confidence %.1f; trying fallback config",
        len(best_text),
        best_confidence,
    )

    for config in _OCR_CONFIGS[1:]:
        text, confidence = _ocr_with_config(image, config)
        score = _ocr_result_score(text, confidence)
        if text and score > best_score:
            best_text = text
            best_confidence = confidence
            best_score = score

    return best_text, best_confidence


def _is_page_scanned(page_text: str, min_text_length: int = 500) -> bool:
    return len(page_text.strip()) < min_text_length


def _is_administrative_text(full_text: str) -> bool:
    matches = sum(1 for pattern in _ADMIN_DOC_PATTERNS if re.search(pattern, full_text, re.IGNORECASE))
    return matches >= 2


def _split_administrative(pages: list[LCDocument]) -> list[LCDocument]:
    full_text = "\n".join(page.page_content for page in pages)
    base_meta = pages[0].metadata if pages else {}

    article_pattern = re.compile(r"(?=\nĐiều\s+\d+[\s\.\:])", re.IGNORECASE)
    raw_chunks = article_pattern.split("\n" + full_text)

    if len(raw_chunks) <= 1:
        clause_pattern = re.compile(r"(?=\nKhoản\s+\d+[\s\.\:])", re.IGNORECASE)
        raw_chunks = clause_pattern.split("\n" + full_text)

    fallback_splitter = RecursiveCharacterTextSplitter(
        chunk_size=_ADMIN_CHUNK_SIZE,
        chunk_overlap=_ADMIN_CHUNK_OVERLAP,
        separators=_NORMAL_SEPARATORS,
    )

    result: list[LCDocument] = []
    for chunk_text in raw_chunks:
        chunk_text = chunk_text.strip()
        if not chunk_text:
            continue

        title_match = re.match(r"(Điều\s+\d+[^\n]*)", chunk_text, re.IGNORECASE)
        article_header = title_match.group(1).strip() if title_match else ""

        if len(chunk_text) <= 1200:
            result.append(LCDocument(page_content=chunk_text, metadata=dict(base_meta)))
            continue

        sub_docs = fallback_splitter.split_text(chunk_text)
        for index, sub in enumerate(sub_docs):
            content = sub if index == 0 or not article_header else f"[{article_header}] (tiếp)\n{sub}"
            result.append(LCDocument(page_content=content, metadata=dict(base_meta)))

    return result if result else [LCDocument(page_content=full_text[:2000], metadata=dict(base_meta))]


def _split_normal(pages: list[LCDocument]) -> list[LCDocument]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_NORMAL_CHUNK_SIZE,
        chunk_overlap=_NORMAL_CHUNK_OVERLAP,
        separators=_NORMAL_SEPARATORS,
    )
    return splitter.split_documents(pages)


class DocumentProcessor:
    def process_pdf(
        self,
        file_path: str,
        metadata: DocumentIndexMetadata,
        force_admin_chunking: bool = False,
    ) -> list[LCDocument]:
        pages = PyMuPDFLoader(file_path).load()
        if not pages:
            return []
        enhanced_pages = self._enhance_pdf_pages_with_ocr(file_path, pages)
        return self._chunk_and_tag(enhanced_pages, metadata, force_admin_chunking)

    def process_word(
        self,
        file_path: str,
        metadata: DocumentIndexMetadata,
        force_admin_chunking: bool = False,
    ) -> list[LCDocument]:
        pages = Docx2txtLoader(file_path).load()
        if not pages:
            return []
        return self._chunk_and_tag(pages, metadata, force_admin_chunking)

    def _enhance_pdf_pages_with_ocr(self, file_path: str, pages: list[LCDocument]) -> list[LCDocument]:
        pdf_doc = fitz.open(file_path)
        try:
            enhanced_pages = []
            for page_index, page in enumerate(pages):
                if _is_page_scanned(page.page_content):
                    self._merge_ocr_text(pdf_doc, page_index, page)
                enhanced_pages.append(page)
            return enhanced_pages
        finally:
            pdf_doc.close()

    def _merge_ocr_text(self, pdf_doc, page_index: int, page: LCDocument) -> None:
        logging.info("Page %s detected as scanned, running OCR", page_index)
        try:
            ocr_text = _ocr_page_to_text(pdf_doc[page_index])
        except Exception as exc:
            logging.error("OCR failed for page %s: %s", page_index, exc)
            return

        if not ocr_text.strip():
            logging.warning("Page %s OCR returned empty result", page_index)
            return

        original_text = page.page_content
        page.page_content = f"{original_text}\n\n[OCR Result]\n{ocr_text}" if original_text.strip() else ocr_text

    def _chunk_and_tag(
        self,
        pages: list[LCDocument],
        metadata: DocumentIndexMetadata,
        force_admin_chunking: bool,
    ) -> list[LCDocument]:
        sample_text = "\n".join(page.page_content for page in pages[:5])
        is_admin = force_admin_chunking or _is_administrative_text(sample_text)
        splits = _split_administrative(pages) if is_admin else _split_normal(pages)
        chunk_strategy = "administrative" if is_admin else "normal"

        chroma_metadata = metadata.as_chroma_metadata(chunk_strategy)
        for split in splits:
            split.metadata.update(chroma_metadata)
        return splits
