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
_HEADING_PREFIX = r"^[\s`'\"“”‘’\-\–\—\:\.;,\(\)\[\]_|lI1]*"
_CHAPTER_HEADER_PATTERN = re.compile(
    _HEADING_PREFIX + r"Chương\s+([IVXLCDM\dHỊÍÌÎÏIl]+)\s*[\.\:\-]?\s*([^\n]*)",
    re.IGNORECASE | re.MULTILINE,
)
_ARTICLE_HEADER_PATTERN = re.compile(
    _HEADING_PREFIX + r"Điều\s+(\d+)\s*[\.\:\-]\s*([^\n]*)",
    re.IGNORECASE | re.MULTILINE,
)
_CLAUSE_HEADER_PATTERN = re.compile(
    _HEADING_PREFIX + r"Khoản\s+(\d+)\s*[\.\:\-]\s*([^\n]*)",
    re.IGNORECASE | re.MULTILINE,
)


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


def _clean_heading_title(value: str | None) -> str:
    clean_value = re.sub(r"\s+", " ", value or "")
    clean_value = re.sub(r"^[`'\"“”‘’\-\–\—\:\.;,\(\)\[\]_|lI1\s]+", "", clean_value)
    clean_value = re.sub(r"[`'\"“”‘’\-\–\—\:\.;,\(\)\[\]_|¬ˆ\s]+$", "", clean_value)
    return clean_value.strip(" .:-")


def _normalize_chapter_number(value: str) -> str:
    token = re.sub(r"[^IVXLCDM\dHỊÍÌÎÏl]", "", value or "", flags=re.IGNORECASE).upper()
    token = (
        token.replace("Ị", "I")
        .replace("Í", "I")
        .replace("Ì", "I")
        .replace("Î", "I")
        .replace("Ï", "I")
    )
    if token == "L":
        token = "I"
    if token.startswith("H"):
        token = "II" + token[1:]
    return token


def _next_heading_title(full_text: str, heading_end: int) -> str:
    for raw_line in full_text[heading_end:].splitlines()[1:4]:
        title = _clean_heading_title(raw_line)
        if not title:
            continue
        if re.match(r"^(Chương|Điều|Khoản)\b", title, re.IGNORECASE):
            return ""
        if len(title) <= 120:
            return title
    return ""


def _is_false_chapter_heading(match: re.Match) -> bool:
    title = _clean_heading_title(match.group(2)).lower()
    return any(marker in title for marker in ("thông tư", "nghị định", "văn bản này"))


def _is_false_article_heading(match: re.Match) -> bool:
    title = _clean_heading_title(match.group(2)).lower()
    false_markers = (
        "nghị định số",
        "thông tư số",
        "được sửa",
        "quy định tại",
        "của thông tư",
    )
    return any(marker in title for marker in false_markers)


def _chapter_heading_matches(full_text: str) -> list[re.Match]:
    return [match for match in _CHAPTER_HEADER_PATTERN.finditer(full_text) if not _is_false_chapter_heading(match)]


def _article_heading_matches(full_text: str) -> list[re.Match]:
    return [match for match in _ARTICLE_HEADER_PATTERN.finditer(full_text) if not _is_false_article_heading(match)]


def _last_chapter_before(chapter_matches: list[re.Match], position: int, full_text: str) -> tuple[str, str]:
    selected = None
    for match in chapter_matches:
        if match.start() > position:
            break
        selected = match
    if not selected:
        return "", ""
    chapter_title = _clean_heading_title(selected.group(2))
    if not chapter_title:
        chapter_title = _next_heading_title(full_text, selected.end())
    return _normalize_chapter_number(selected.group(1)), chapter_title


def _section_path(chapter_number: str, article_number: str) -> str:
    parts = []
    if chapter_number:
        parts.append(f"Chương {chapter_number}")
    if article_number:
        parts.append(f"Điều {article_number}")
    return " > ".join(parts)


def _make_parent_metadata(
    base_meta: dict,
    doc_id: int,
    parent_index: int,
    parent_type: str,
    chapter_number: str = "",
    chapter_title: str = "",
    article_number: str = "",
    article_title: str = "",
    clause_number: str = "",
    clause_title: str = "",
) -> dict:
    parent_key = article_number or clause_number or str(parent_index)
    parent_id = f"doc-{doc_id}:{parent_type}-{parent_key}"
    return {
        **base_meta,
        "chunk_type": "child",
        "parent_id": parent_id,
        "parent_type": parent_type,
        "parent_index": parent_index,
        "chapter_number": chapter_number,
        "chapter_title": chapter_title,
        "article_number": article_number,
        "article_title": article_title,
        "clause_number": clause_number,
        "clause_title": clause_title,
        "section_path": _section_path(chapter_number, article_number),
    }


def _append_parent_children(
    result: list[LCDocument],
    parent_text: str,
    parent_meta: dict,
    parent_header: str,
    splitter: RecursiveCharacterTextSplitter,
) -> None:
    parent_text = parent_text.strip()
    if not parent_text:
        return

    child_texts = [parent_text] if len(parent_text) <= _ADMIN_CHUNK_SIZE else splitter.split_text(parent_text)
    child_count = len(child_texts)
    for index, child_text in enumerate(child_texts):
        content = child_text
        if index > 0 and parent_header:
            content = f"[{parent_header}] (tiếp)\n{child_text}"
        child_meta = {
            **parent_meta,
            "child_index": index,
            "parent_child_count": child_count,
        }
        result.append(LCDocument(page_content=content, metadata=child_meta))


def _split_administrative(
    pages: list[LCDocument],
    metadata: DocumentIndexMetadata | None = None,
) -> list[LCDocument]:
    full_text = "\n".join(page.page_content for page in pages)
    base_meta = pages[0].metadata if pages else {}
    doc_id = metadata.doc_id if metadata else int(base_meta.get("doc_id", 0) or 0)
    chapter_matches = _chapter_heading_matches(full_text)
    article_matches = _article_heading_matches(full_text)

    fallback_splitter = RecursiveCharacterTextSplitter(
        chunk_size=_ADMIN_CHUNK_SIZE,
        chunk_overlap=_ADMIN_CHUNK_OVERLAP,
        separators=_NORMAL_SEPARATORS,
    )

    result: list[LCDocument] = []
    if article_matches:
        preamble = full_text[: article_matches[0].start()].strip()
        if preamble:
            parent_meta = _make_parent_metadata(dict(base_meta), doc_id, 0, "preamble")
            _append_parent_children(result, preamble, parent_meta, "Phần mở đầu", fallback_splitter)

        for parent_index, match in enumerate(article_matches, start=1):
            next_start = article_matches[parent_index].start() if parent_index < len(article_matches) else len(full_text)
            article_text = full_text[match.start():next_start].strip()
            chapter_number, chapter_title = _last_chapter_before(chapter_matches, match.start(), full_text)
            article_number = match.group(1).strip()
            article_title = _clean_heading_title(match.group(2))
            article_header = f"Điều {article_number}"
            if article_title:
                article_header = f"{article_header}. {article_title}"
            parent_meta = _make_parent_metadata(
                dict(base_meta),
                doc_id,
                parent_index,
                "article",
                chapter_number=chapter_number,
                chapter_title=chapter_title,
                article_number=article_number,
                article_title=article_title,
            )
            _append_parent_children(result, article_text, parent_meta, article_header, fallback_splitter)

        return result

    clause_matches = list(_CLAUSE_HEADER_PATTERN.finditer(full_text))
    if clause_matches:
        for parent_index, match in enumerate(clause_matches, start=1):
            next_start = clause_matches[parent_index].start() if parent_index < len(clause_matches) else len(full_text)
            clause_text = full_text[match.start():next_start].strip()
            clause_number = match.group(1).strip()
            clause_title = _clean_heading_title(match.group(2))
            clause_header = f"Khoản {clause_number}"
            if clause_title:
                clause_header = f"{clause_header}. {clause_title}"
            parent_meta = _make_parent_metadata(
                dict(base_meta),
                doc_id,
                parent_index,
                "clause",
                clause_number=clause_number,
                clause_title=clause_title,
            )
            _append_parent_children(result, clause_text, parent_meta, clause_header, fallback_splitter)
        return result

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
        print(
            f"\n===== OCR TEXT START page={page_index + 1} =====\n"
            f"{ocr_text}\n"
            f"===== OCR TEXT END page={page_index + 1} =====\n",
            flush=True,
        )
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
        splits = _split_administrative(pages, metadata) if is_admin else _split_normal(pages)
        chunk_strategy = "administrative" if is_admin else "normal"

        chroma_metadata = metadata.as_chroma_metadata(chunk_strategy)
        for index, split in enumerate(splits):
            split.metadata.setdefault("chunk_type", "child")
            split.metadata.setdefault("chunk_index", index)
            split.metadata.update(chroma_metadata)
        return splits
