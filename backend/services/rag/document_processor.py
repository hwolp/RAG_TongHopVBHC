import io
import logging
import os
import re
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import fitz
from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_engine.models import DocumentIndexMetadata

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("Pillow not installed; OCR for scanned PDFs disabled")

try:
    import pytesseract

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not installed; Tesseract OCR fallback disabled")


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
_BACKEND_DIR = Path(__file__).resolve().parents[2]


def _backend_relative_path_from_env(name: str, default: Path) -> Path:
    raw_value = os.getenv(name)
    path = Path(raw_value) if raw_value else default
    return path if path.is_absolute() else _BACKEND_DIR / path


_OCR_RENDER_SCALE = float(os.getenv("OCR_RENDER_SCALE", "3") or "3")
_OCR_LANG = os.getenv("TESSERACT_OCR_LANG", "vie")
_TESSERACT_AUTO_DOWNLOAD_VIE = os.getenv("TESSERACT_AUTO_DOWNLOAD_VIE", "true").strip().lower() not in {
    "0",
    "false",
    "no",
}
_TESSERACT_TESSDATA_DIR = _backend_relative_path_from_env("TESSERACT_TESSDATA_DIR", _BACKEND_DIR / "tessdata")
_TESSERACT_VIE_TRAINEDDATA_URL = os.getenv(
    "TESSERACT_VIE_TRAINEDDATA_URL",
    "https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/vie.traineddata",
)
_OCR_CONFIGS = [
    "--oem 1 --psm 6 -c preserve_interword_spaces=1",
    "--oem 1 --psm 4 -c preserve_interword_spaces=1",
]
_OCR_IMAGE_VARIANTS = os.getenv("TESSERACT_OCR_IMAGE_VARIANTS", "grayscale,threshold").split(",")
_OCR_ACCEPT_MIN_CHARS = int(os.getenv("OCR_ACCEPT_MIN_CHARS", "80") or "80")
_OCR_ACCEPT_MIN_CONFIDENCE = float(os.getenv("OCR_ACCEPT_MIN_CONFIDENCE", "75") or "75")
_OCR_MAX_WORKERS = max(1, int(os.getenv("OCR_MAX_WORKERS", "5") or "5"))
_ADMIN_CHUNK_SIZE = 800
_ADMIN_CHUNK_OVERLAP = 150
_NORMAL_CHUNK_SIZE = 900
_NORMAL_CHUNK_OVERLAP = 200
_HEADING_PREFIX = r"^[\s`'\"“”‘’\-\–\—\:\.;,\(\)\[\]_|lI1]*"
_CHAPTER_WORD_PATTERN = r"Ch(?:ương|uong)"
_CHAPTER_HEADER_PATTERN = re.compile(
    _HEADING_PREFIX + _CHAPTER_WORD_PATTERN + r"\s*([IVXLCDM\dHỊÍÌÎÏIlTt\[\]\|!]+)\s*[\.\:\-]?\s*([^\n]*)",
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
_LIST_SECTION_HEADER_PATTERN = re.compile(
    _HEADING_PREFIX + r"([IVXLCDM]+)\s*[\.\:\-]\s+([A-ZÀ-ỸĐ][^\n]{3,160})",
    re.IGNORECASE | re.MULTILINE,
)
_LIST_ITEM_HEADER_PATTERN = re.compile(
    _HEADING_PREFIX + r"(\d{1,2})\s*[\.\:\-]\s+([A-ZÀ-ỸĐa-zà-ỹđ][^\n]{2,140})",
    re.MULTILINE,
)
_LIST_POINT_HEADER_PATTERN = re.compile(
    _HEADING_PREFIX + r"([a-zđ])\)\s+([A-ZÀ-ỸĐa-zà-ỹđ][^\n]{2,140})",
    re.IGNORECASE | re.MULTILINE,
)


def _ocr_page_to_text(page) -> str:
    if not PIL_AVAILABLE:
        logging.warning("Pillow not available, skipping OCR")
        return ""

    try:
        image = _render_pdf_page_image(page)
        extracted_text, confidence = _ocr_image_to_text(image, page.number)
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


def _render_pdf_page_image(page) -> Image.Image:
    # Đảm bảo render tối thiểu 300 DPI để Tesseract đọc dấu chính xác
    # PyMuPDF mặc định 72 DPI, cần scale ít nhất 300/72 ≈ 4.17
    _MIN_SCALE_FOR_300DPI = 300.0 / 72.0
    scale = max(_OCR_RENDER_SCALE, _MIN_SCALE_FOR_300DPI)
    matrix = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("ppm"))).convert("RGB")


def _ocr_image_to_text(image: Image.Image, page_number: int) -> tuple[str, float]:
    return _ocr_with_tesseract(image)


def _ocr_with_tesseract(image: Image.Image) -> tuple[str, float]:
    if not TESSERACT_AVAILABLE:
        logging.warning("pytesseract not available, skipping Tesseract fallback")
        return "", 0.0

    _ensure_tesseract_language_data()

    tesseract_cmd = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if tesseract_cmd and (os.path.exists(tesseract_cmd) or os.getenv("TESSERACT_CMD")):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    return _best_ocr_result(image)


_TESSERACT_ENG_TRAINEDDATA_URL = os.getenv(
    "TESSERACT_ENG_TRAINEDDATA_URL",
    "https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/eng.traineddata",
)


def _download_traineddata(url: str, dest: Path) -> None:
    """Tải file traineddata Tesseract, bỏ qua nếu đã có."""
    if dest.exists():
        return
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        logging.info("Downloading Tesseract traineddata: %s → %s", url, dest)
        urllib.request.urlretrieve(url, dest)
    except Exception as exc:
        logging.warning("Could not download Tesseract traineddata from %s: %s", url, exc)


def _ensure_tesseract_language_data() -> None:
    """Đảm bảo các file .traineddata cần thiết tồn tại trong tessdata_dir.

    - vie.traineddata: luôn cần nếu lang chứa 'vie'
    - eng.traineddata: cần nếu lang chứa 'eng' (để nhận dạng ký tự Latin,
      số, dấu câu trong văn bản hành chính tiếng Việt)
    """
    tessdata_dir = _TESSERACT_TESSDATA_DIR
    has_any = False

    if "vie" in _OCR_LANG.lower():
        vie_path = tessdata_dir / "vie.traineddata"
        if not vie_path.exists() and _TESSERACT_AUTO_DOWNLOAD_VIE:
            _download_traineddata(_TESSERACT_VIE_TRAINEDDATA_URL, vie_path)
        if vie_path.exists():
            has_any = True

    if "eng" in _OCR_LANG.lower():
        eng_path = tessdata_dir / "eng.traineddata"
        if not eng_path.exists() and _TESSERACT_AUTO_DOWNLOAD_VIE:
            _download_traineddata(_TESSERACT_ENG_TRAINEDDATA_URL, eng_path)
        if eng_path.exists():
            has_any = True

    if has_any:
        os.environ.setdefault("TESSDATA_PREFIX", str(tessdata_dir))
        return

    if not _TESSERACT_AUTO_DOWNLOAD_VIE:
        return

    try:
        tessdata_dir.mkdir(parents=True, exist_ok=True)
        logging.info("Downloading Vietnamese Tesseract traineddata to %s", tessdata_dir / "vie.traineddata")
        urllib.request.urlretrieve(_TESSERACT_VIE_TRAINEDDATA_URL, tessdata_dir / "vie.traineddata")
        os.environ.setdefault("TESSDATA_PREFIX", str(tessdata_dir))
    except Exception as exc:
        logging.warning(
            "Could not auto-download Vietnamese Tesseract traineddata from %s: %s",
            _TESSERACT_VIE_TRAINEDDATA_URL,
            exc,
        )


def _prepare_ocr_image(image: Image.Image) -> Image.Image:
    return _prepare_ocr_image_grayscale(image)


def _prepare_ocr_image_grayscale(image: Image.Image) -> Image.Image:
    """Preserve thin Vietnamese accent marks better than hard binarization."""
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    gray = ImageEnhance.Contrast(gray).enhance(1.25)
    return ImageEnhance.Sharpness(gray).enhance(1.35)


def _prepare_ocr_image_threshold(image: Image.Image) -> Image.Image:
    """Binarize ảnh nhưng giữ threshold thấp hơn để không mất dấu mỏng.

    Thay đổi so với trước:
    - Bỏ MedianFilter(size=3): filter này làm mờ các nét thanh điệu mảnh
      (sắc, huyền, ngã, hỏi, nặng) khiến Tesseract đọc sai
    - Threshold 176 → 155: dấu tiếng Việt thường nhạt hơn thân chữ,
      ngưỡng cao cắt mất dấu → hạ xuống 155 để giữ lại nhiều hơn
    """
    gray = _prepare_ocr_image_grayscale(image)
    # Không dùng MedianFilter để giữ nét dấu thanh điệu
    return gray.point(lambda pixel: 255 if pixel > 155 else 0)


def _ocr_image_variants(image: Image.Image) -> list[tuple[str, Image.Image]]:
    variants = []
    for raw_name in _OCR_IMAGE_VARIANTS:
        name = raw_name.strip().lower()
        if name in {"gray", "grayscale"}:
            variants.append(("grayscale", _prepare_ocr_image_grayscale(image)))
        elif name in {"threshold", "binary", "binarized"}:
            variants.append(("threshold", _prepare_ocr_image_threshold(image)))
    return variants or [("grayscale", _prepare_ocr_image_grayscale(image))]


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
    text = _text_from_tesseract_data(data)
    return _postprocess_ocr_text(text), avg_confidence


def _text_from_tesseract_data(data: dict) -> str:
    texts = data.get("text", []) or []
    block_nums = data.get("block_num", []) or []
    paragraph_nums = data.get("par_num", []) or []
    line_nums = data.get("line_num", []) or []
    lines: list[str] = []
    current_key = None
    current_words: list[str] = []

    for index, raw_text in enumerate(texts):
        word = str(raw_text or "").strip()
        if not word:
            continue
        key = (
            block_nums[index] if index < len(block_nums) else 0,
            paragraph_nums[index] if index < len(paragraph_nums) else 0,
            line_nums[index] if index < len(line_nums) else 0,
        )
        if current_key is not None and key != current_key:
            lines.append(" ".join(current_words))
            current_words = []
        current_key = key
        current_words.append(word)

    if current_words:
        lines.append(" ".join(current_words))
    return "\n".join(lines).strip()


def _is_ocr_result_good_enough(text: str, confidence: float) -> bool:
    return len(text.strip()) >= _OCR_ACCEPT_MIN_CHARS and confidence >= _OCR_ACCEPT_MIN_CONFIDENCE


def _ocr_result_score(text: str, confidence: float) -> float:
    vietnamese_marks = sum(1 for char in text if _has_vietnamese_diacritic(char))
    non_space_chars = max(1, sum(1 for char in text if not char.isspace()))
    diacritic_bonus = min(8.0, (vietnamese_marks / non_space_chars) * 80)
    structure_bonus = min(8.0, len(_article_heading_matches(text)) * 2.5 + len(_chapter_heading_matches(text)) * 1.5)
    suspicious_penalty = _ocr_suspicious_text_penalty(text)
    return confidence + min(len(text), 4000) / 4000 + diacritic_bonus + structure_bonus - suspicious_penalty


def _best_ocr_result(image: Image.Image) -> tuple[str, float]:
    if not _OCR_CONFIGS:
        return "", 0.0

    best_text = ""
    best_confidence = 0.0
    best_score = -1.0
    for variant_name, variant_image in _ocr_image_variants(image):
        for config in _OCR_CONFIGS:
            text, confidence = _ocr_with_config(variant_image, config)
            score = _ocr_result_score(text, confidence)
            if text and score > best_score:
                best_text = text
                best_confidence = confidence
                best_score = score

    logging.info("OCR selected result confidence=%.1f score=%.2f", best_confidence, best_score)
    return best_text, best_confidence


def _postprocess_ocr_text(text: str) -> str:
    # Bước 1: Normalize Unicode về NFC — gộp dấu rời vào chữ cái
    # Ví dụ: 'a\u0301' (a + combining acute) → 'á'
    # OCR hay sinh ra NFD/NFKD khiến dấu bị tách, gây lỗi khi match text
    text = unicodedata.normalize("NFC", text)

    # Bước 2: Fix số La Mã bị nhận sai trong tiêu đề Chương
    text = _fix_ocr_chapter_roman_numerals(text)

    # Bước 3: Fix dấu ở các heading hành chính hay bị Tesseract đọc thiếu
    text = _fix_ocr_administrative_heading_accents(text)
    text = _fix_ocr_article_heading(text)
    text = _fix_common_vietnamese_ocr_words(text)
    text = _fix_ocr_administrative_heading_accents(text)

    # Bước 4: Xóa ký tự '?' thừa mà Tesseract sinh ra khi không nhận dạng được
    text = text.replace("¬", "")
    text = re.sub(r"(?m)^\s*\?\s+", "", text)
    text = re.sub(r"([A-Za-zÀ-ỹ0-9\)])\?{2,}", r"\1", text)
    text = re.sub(r"([A-Za-zÀ-ỹ0-9\)])\s+\?", r"\1", text)
    text = re.sub(r"(?m)([A-Za-zÀ-ỹ0-9\)])\?(\s*$)", r"\1\2", text)

    # Bước 5: Xóa ký tự điều khiển không in được (giữ newline và tab)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Bước 6: Chuẩn hóa khoảng trắng thừa (giữ xuống dòng)
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"(?m)\s+[_.:;|\-]+(?:\s+[_.:;|\-]+)*\s*$", "", text)

    return text


def _fix_ocr_chapter_roman_numerals(text: str) -> str:
    return re.sub(
        r"(?im)^[^\nA-Za-zÀ-ỹ]{0,30}Ch(?:ương|uong)\s*([IVXLCDM\dHỊÍÌÎÏIlTt\[\]\|!]+)(?=\s|[\.\:\-\]]|$)",
        lambda match: f"Chương {_normalize_chapter_number(match.group(1))}",
        text,
    )


def _fix_ocr_article_heading(text: str) -> str:
    text = re.sub(r"(?im)^[^A-Za-zÀ-ỹ0-9\n]*Đi[êềếểễệe]u\s+(\d+)", r"Điều \1", text)
    text = re.sub(r"(?im)" + _HEADING_PREFIX + r"Đi[êềếểễệe]u\s+(\d+)", r"Điều \1", text)
    text = re.sub(r"(?im)" + _HEADING_PREFIX + r"Điều\s+(\d+)\.(\d+)\s+", r"Điều \1. ", text)
    return text


def _fix_ocr_administrative_heading_accents(text: str) -> str:
    lines = text.splitlines()
    fixed_lines = []
    previous_is_chapter = False
    for line in lines:
        stripped = line.strip()
        should_fix = previous_is_chapter or _looks_like_upper_heading(stripped)
        fixed = _fix_upper_heading_terms(line) if should_fix else line
        fixed_lines.append(fixed)
        previous_is_chapter = bool(re.match(_HEADING_PREFIX + r"Chương\s+[IVXLCDM]+", fixed, re.IGNORECASE))
    return "\n".join(fixed_lines)


def _looks_like_upper_heading(value: str) -> bool:
    upper_value = value.upper()
    if upper_value.lstrip().startswith(("LỄ TANG", "LE TANG")):
        return True
    letters = [char for char in value if char.isalpha()]
    if len(letters) < 4:
        return False
    uppercase = sum(1 for char in letters if char.upper() == char)
    return uppercase / len(letters) >= 0.75 and len(value) <= 120


def _fix_upper_heading_terms(line: str) -> str:
    replacements = [
        (r"\bL[ẺÉE]\s+TANG\b", "LỄ TANG"),
        (r"\bC[ÁA]P\b", "CẤP"),
        (r"\bNH[ÀA]\s+N(?:ƯỚC|UOC|ƯOC|UỚC)\b", "NHÀ NƯỚC"),
        (r"\bQUY\s+D[ỊI]NH\b", "QUY ĐỊNH"),
        (r"\b[ĐđD][ÓỐóốOÒò]I\s+V[ỚớO]I\b", "ĐỐI VỚI"),
        (r"\bQU[ẦÂA]N\s+NH[ÂA]N\b", "QUÂN NHÂN"),
        (r"\bD[ẠA]I\s+T[ÁA]\b", "ĐẠI TÁ"),
        (r"\bTR[ỞO]\s+XU[ỐO]NG\b", "TRỞ XUỐNG"),
        (r"\bT[ỎỔO]\s+CH[ỨƯU]C\b", "TỔ CHỨC"),
        (r"\bTH[ỊI]\s+H[ÀA]NH\d*\b", "THI HÀNH"),
    ]
    fixed = line
    for pattern, replacement in replacements:
        fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)
    return fixed


def _fix_common_vietnamese_ocr_words(text: str) -> str:
    replacements = [
        (r"\bsô\b", "số"),
        (r"\btô chức\b", "tổ chức"),
        (r"\bLêtang\b", "Lễ tang"),
        (r"\blêtang\b", "lễ tang"),
        (r"\bđôi với\b", "đối với"),
        (r"\bquôc\b", "quốc"),
        (r"\bquéc\b", "quốc"),
        (r"\bviệt gon\b", "viết gọn"),
        (r"\bhuan luyện\b", "huấn luyện"),
        (r"\bcâp\b", "cấp"),
        (r"\bthâm quyên\b", "thẩm quyền"),
        (r"\bquyêt\b", "quyết"),
        (r"\btỗ chức\b", "tổ chức"),
        (r"\btỗ chúc\b", "tổ chức"),
        (r"\bsửa đôi\b", "sửa đổi"),
        (r"\bb(?:ê|e|ô|ồ|ố|ỗ|ổ|ộ|o|ơ|ỗổ)\s+sung\b", "bổ sung"),
        (r"\bbỗ sung\b", "bổ sung"),
        (r"\bbộ sung\b", "bổ sung"),
        (r"\bbố sung\b", "bổ sung"),
        (r"\bquan hàm\b", "quân hàm"),
        (r"\bquân ham\b", "quân hàm"),
        (r"\bquần nhân\b", "quân nhân"),
        (r"\bđói với\b", "đối với"),
        (r"\blời điền\b", "lời điếu"),
        (r"\bBáo Nhân đân\b", "Báo Nhân dân"),
        (r"\bnhân đân\b", "nhân dân"),
        (r"\bbảo đám\b", "bảo đảm"),
        (r"\bthị hành\d*\b", "thi hành"),
        (r"\bcập có thẩm quyền\b", "cấp có thẩm quyền"),
        (r"\bđiêu\b", "điều"),
        (r"\bcơ yêu\b", "cơ yếu"),
        (r"\ban tang\b", "an táng"),
        (r"\bNghỉ thức\b", "Nghi thức"),
        (r"\bnghỉ thức\b", "nghi thức"),
    ]
    fixed = text
    for pattern, replacement in replacements:
        fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)
    return fixed


def _has_vietnamese_diacritic(char: str) -> bool:
    decomposed = unicodedata.normalize("NFD", char)
    return any(unicodedata.category(part) == "Mn" for part in decomposed) or char in "đĐ"


def _ocr_suspicious_text_penalty(text: str) -> float:
    penalty = 0.0
    penalty += min(5.0, text.count("?") * 0.4)
    penalty += min(5.0, text.count("¬") * 0.5)
    penalty += len(re.findall(r"(?im)^Chương\s*[\.\:\-]?\s*$", text)) * 4.0
    penalty += len(re.findall(r"(?im)^Đi[êeệ]u\s+[A-Z]\b", text)) * 4.0
    penalty += len(re.findall(r"(?im)^Điều\s+[A-Z]\b", text)) * 4.0
    penalty += len(re.findall(r"\b(?:CAP|NHA NUOC|LE TANG)\b", text)) * 0.5
    return penalty


def _is_page_scanned(page_text: str, min_text_length: int = 500) -> bool:
    """Phát hiện page cần OCR.

    Ngoài việc kiểm tra độ dài, còn kiểm tra tỷ lệ ký tự hợp lệ:
    PDF có text nhúng nhưng encoding sai sẽ có nhiều ký tự lạ
    (> 30% không in được) → cần OCR lại.
    """
    text = page_text.strip()
    if len(text) < min_text_length:
        return True
    # Kiểm tra chất lượng text: nếu quá nhiều ký tự lạ thì coi như scanned
    non_space_chars = [c for c in text if not c.isspace()]
    if not non_space_chars:
        return True
    printable_count = sum(1 for c in non_space_chars if c.isprintable())
    valid_ratio = printable_count / len(non_space_chars)
    if valid_ratio < 0.70:
        logging.info(
            "Page has low printable ratio (%.0f%%), treating as scanned",
            valid_ratio * 100,
        )
        return True
    return False


def _is_administrative_text(full_text: str) -> bool:
    matches = sum(1 for pattern in _ADMIN_DOC_PATTERNS if re.search(pattern, full_text, re.IGNORECASE))
    if matches >= 2:
        return True
    return bool(_list_section_heading_matches(full_text) and _list_item_heading_matches(full_text))


def _clean_heading_title(value: str | None) -> str:
    clean_value = re.sub(r"\s+", " ", value or "")
    clean_value = _fix_upper_heading_terms(clean_value)
    clean_value = _fix_common_vietnamese_ocr_words(clean_value)
    clean_value = re.sub(r"^[`'\"“”‘’\-\–\—\:\.;,\(\)\[\]_|lI1\s]+", "", clean_value)
    clean_value = re.sub(r"^[*®\d\)\]\s]+(?=[A-ZÀ-ỸĐa-zà-ỹđ])", "", clean_value)
    clean_value = re.sub(r"[`'\"“”‘’\-\–\—\:\.;,\(\)\[\]_|¬ˆ“”‘’\d\s]+$", "", clean_value)
    return clean_value.strip(" .:-")


def _normalize_chapter_number(value: str) -> str:
    raw_token = re.sub(r"[^IVXLCDM\dHỊÍÌÎÏlT\[\]\|!]", "", value or "", flags=re.IGNORECASE).upper()
    has_bracket_like_i = any(char in raw_token for char in "[]|!")
    token = re.sub(r"[\[\]\|!]", "", raw_token)
    token = (
        token.replace("Ị", "I")
        .replace("Í", "I")
        .replace("Ì", "I")
        .replace("Î", "I")
        .replace("Ï", "I")
        .replace("T", "I")
    )
    if not token and has_bracket_like_i:
        token = "I"
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


def _is_false_list_section_heading(match: re.Match) -> bool:
    title = _clean_heading_title(match.group(2))
    if not title:
        return True
    if re.match(r"^(Chương|Điều|Khoản)\b", title, re.IGNORECASE):
        return True
    letters = [char for char in title if char.isalpha()]
    if len(letters) < 4:
        return True
    uppercase_ratio = sum(1 for char in letters if char.upper() == char) / len(letters)
    return uppercase_ratio < 0.55


def _is_false_list_item_heading(match: re.Match) -> bool:
    title = _clean_heading_title(match.group(2))
    if not title:
        return True
    if re.match(r"^(Chương|Điều|Khoản|Nghị định|Thông tư)\b", title, re.IGNORECASE):
        return True
    return len(title) > 140


def _chapter_heading_matches(full_text: str) -> list[re.Match]:
    return [match for match in _CHAPTER_HEADER_PATTERN.finditer(full_text) if not _is_false_chapter_heading(match)]


def _article_heading_matches(full_text: str) -> list[re.Match]:
    return [match for match in _ARTICLE_HEADER_PATTERN.finditer(full_text) if not _is_false_article_heading(match)]


def _list_section_heading_matches(full_text: str) -> list[re.Match]:
    return [
        match for match in _LIST_SECTION_HEADER_PATTERN.finditer(full_text) if not _is_false_list_section_heading(match)
    ]


def _list_item_heading_matches(full_text: str) -> list[re.Match]:
    return [match for match in _LIST_ITEM_HEADER_PATTERN.finditer(full_text) if not _is_false_list_item_heading(match)]


def _list_point_heading_matches(full_text: str) -> list[re.Match]:
    return list(_LIST_POINT_HEADER_PATTERN.finditer(full_text))


def _last_chapter_before(chapter_matches: list[re.Match], position: int, full_text: str) -> tuple[str, str]:
    selected = None
    for match in chapter_matches:
        if match.start() > position:
            break
        selected = match
    if not selected:
        return "", ""
    chapter_title = _clean_heading_title(selected.group(2))
    fallback_title = _next_heading_title(full_text, selected.end())
    if (not chapter_title or len(chapter_title) <= 4) and fallback_title:
        chapter_title = fallback_title
    return _normalize_chapter_number(selected.group(1)), chapter_title


def _last_list_section_before(section_matches: list[re.Match], position: int) -> tuple[str, str]:
    selected = None
    for match in section_matches:
        if match.start() > position:
            break
        selected = match
    if not selected:
        return "", ""
    return selected.group(1).strip().upper(), _clean_heading_title(selected.group(2))


def _last_list_item_before(item_matches: list[re.Match], position: int) -> tuple[str, str]:
    selected = None
    for match in item_matches:
        if match.start() > position:
            break
        selected = match
    if not selected:
        return "", ""
    return selected.group(1).strip(), _clean_heading_title(selected.group(2))


def _section_path(
    chapter_number: str,
    article_number: str,
    list_section_number: str = "",
    list_item_number: str = "",
) -> str:
    parts = []
    if chapter_number:
        parts.append(f"Chương {chapter_number}")
    if article_number:
        parts.append(f"Điều {article_number}")
    if list_section_number:
        parts.append(f"Mục {list_section_number}")
    if list_item_number:
        parts.append(f"{list_item_number}.")
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
    list_section_number: str = "",
    list_section_title: str = "",
    list_item_number: str = "",
    list_item_title: str = "",
    list_point_number: str = "",
    list_point_title: str = "",
) -> dict:
    parent_key = article_number or clause_number or list_item_number or list_section_number or str(parent_index)
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
        "list_section_number": list_section_number,
        "list_section_title": list_section_title,
        "list_item_number": list_item_number,
        "list_item_title": list_item_title,
        "list_point_number": list_point_number,
        "list_point_title": list_point_title,
        "section_path": _section_path(chapter_number, article_number, list_section_number, list_item_number),
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
        # Lấy thông tin đường dẫn phân cấp (ví dụ: "Chương I > Điều 5")
        section_path = parent_meta.get("section_path", "")
        # Nếu section_path trống (ví dụ: preamble), dùng parent_header làm fallback
        if not section_path and parent_header:
            section_path = parent_header

        # Nhúng thông tin phân cấp trực tiếp vào nội dung chunk
        if section_path:
            if index == 0:
                content = f"[Nguồn: {section_path}]\n{child_text}"
            else:
                content = f"[Nguồn: {section_path} (tiếp)]\n{child_text}"
        else:
            content = child_text

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

    list_sections = _list_section_heading_matches(full_text)
    list_items = _list_item_heading_matches(full_text)
    if list_sections or list_items:
        return _split_list_structured(full_text, base_meta, doc_id, fallback_splitter)

    return result if result else [LCDocument(page_content=full_text[:2000], metadata=dict(base_meta))]


def _split_list_structured(
    full_text: str,
    base_meta: dict,
    doc_id: int,
    splitter: RecursiveCharacterTextSplitter,
) -> list[LCDocument]:
    section_matches = _list_section_heading_matches(full_text)
    item_matches = _list_item_heading_matches(full_text)
    point_matches = _list_point_heading_matches(full_text)
    parents = item_matches or section_matches or point_matches
    result: list[LCDocument] = []

    preamble = full_text[: parents[0].start()].strip() if parents else ""
    if preamble:
        parent_meta = _make_parent_metadata(dict(base_meta), doc_id, 0, "preamble")
        _append_parent_children(result, preamble, parent_meta, "Phần mở đầu", splitter)

    for parent_index, match in enumerate(parents, start=1):
        next_start = parents[parent_index].start() if parent_index < len(parents) else len(full_text)
        parent_text = full_text[match.start():next_start].strip()
        section_number, section_title = _last_list_section_before(section_matches, match.start())

        if parents is item_matches:
            item_number = match.group(1).strip()
            item_title = _clean_heading_title(match.group(2))
            parent_header = f"{item_number}. {item_title}" if item_title else f"{item_number}."
            parent_meta = _make_parent_metadata(
                dict(base_meta),
                doc_id,
                parent_index,
                "list_item",
                list_section_number=section_number,
                list_section_title=section_title,
                list_item_number=item_number,
                list_item_title=item_title,
            )
        elif parents is section_matches:
            section_number = match.group(1).strip().upper()
            section_title = _clean_heading_title(match.group(2))
            parent_header = f"{section_number}. {section_title}" if section_title else section_number
            parent_meta = _make_parent_metadata(
                dict(base_meta),
                doc_id,
                parent_index,
                "list_section",
                list_section_number=section_number,
                list_section_title=section_title,
            )
        else:
            item_number, item_title = _last_list_item_before(item_matches, match.start())
            point_number = match.group(1).strip()
            point_title = _clean_heading_title(match.group(2))
            parent_header = f"{point_number}) {point_title}" if point_title else f"{point_number})"
            parent_meta = _make_parent_metadata(
                dict(base_meta),
                doc_id,
                parent_index,
                "list_point",
                list_section_number=section_number,
                list_section_title=section_title,
                list_item_number=item_number,
                list_item_title=item_title,
                list_point_number=point_number,
                list_point_title=point_title,
            )

        _append_parent_children(result, parent_text, parent_meta, parent_header, splitter)

    return result


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
        ocr_page_indexes = [
            page_index for page_index, page in enumerate(pages) if _is_page_scanned(page.page_content)
        ]
        if not ocr_page_indexes:
            return pages

        worker_count = min(_OCR_MAX_WORKERS, len(ocr_page_indexes))
        logging.info("Running OCR for %s pages with %s workers", len(ocr_page_indexes), worker_count)
        if TESSERACT_AVAILABLE:
            _ensure_tesseract_language_data()
        if worker_count == 1:
            for page_index in ocr_page_indexes:
                self._merge_ocr_text(file_path, page_index, pages[page_index])
            return pages

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(self._ocr_pdf_page_by_index, file_path, page_index): page_index
                for page_index in ocr_page_indexes
            }
            for future in as_completed(futures):
                page_index = futures[future]
                try:
                    ocr_text = future.result()
                except Exception as exc:
                    logging.error("OCR failed for page %s: %s", page_index, exc)
                    continue
                self._apply_ocr_text(page_index, pages[page_index], ocr_text)
        return pages

    def _ocr_pdf_page_by_index(self, file_path: str, page_index: int) -> str:
        with fitz.open(file_path) as pdf_doc:
            logging.info("Page %s detected as scanned, running OCR", page_index)
            return _ocr_page_to_text(pdf_doc[page_index])

    def _merge_ocr_text(self, file_path: str, page_index: int, page: LCDocument) -> None:
        logging.info("Page %s detected as scanned, running OCR", page_index)
        try:
            with fitz.open(file_path) as pdf_doc:
                ocr_text = _ocr_page_to_text(pdf_doc[page_index])
        except Exception as exc:
            logging.error("OCR failed for page %s: %s", page_index, exc)
            return
        self._apply_ocr_text(page_index, page, ocr_text)

    def _apply_ocr_text(self, page_index: int, page: LCDocument, ocr_text: str) -> None:
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
