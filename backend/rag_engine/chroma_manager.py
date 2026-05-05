import re
from typing import Optional
import io
import logging
import cv2
import fitz
import numpy as np

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not installed — OCR for scanned PDFs disabled")

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader
from langchain_core.documents import Document as LCDocument
from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL

# Sử dụng pytesseract cho OCR Vietnamese

def _ocr_page_to_text(page) -> str:
    if not TESSERACT_AVAILABLE:
        logging.warning("pytesseract not available, skipping OCR")
        return ""
    
    try:
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        # --- SỬA TẠI ĐÂY: Tăng độ nét (DPI) để OCR chính xác hơn ---
        matrix = fitz.Matrix(2, 2) # Zoom 2x, giúp chữ rõ nét hơn rất nhiều
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        
        img_data = pix.tobytes("ppm")
        img = Image.open(io.BytesIO(img_data))
        
        # --- SỬA TẠI ĐÂY: Thêm config để Tesseract tập trung tìm văn bản ---
        custom_config = r'--oem 3 --psm 6' 
        text = pytesseract.image_to_string(img, lang='vie', config=custom_config)
        
        extracted_text = text.strip()

        # --- KIỂM TRA THÀNH CÔNG ---
        if not extracted_text:
            logging.warning(f"Trang {page.number}: OCR chạy xong nhưng KHÔNG tìm thấy chữ.")
        else:
            logging.info(f"Trang {page.number}: OCR thành công, lấy được {len(extracted_text)} ký tự.")
            # In thử 50 ký tự đầu để kiểm tra mắt
            print(f"DEBUG Trang {page.number}: {extracted_text[:50]}...")
        print(f"Ket qua: {text}")
        return extracted_text
    
    except Exception as e:
        logging.error(f"OCR failed at page {page.number}: {e}")
        return ""


# ──────────────────────────────────────────────────────────────────────────────
# Patterns nhận diện văn bản hành chính Việt Nam
# ──────────────────────────────────────────────────────────────────────────────
_ADMIN_DOC_PATTERNS = [
    r"\bĐiều\s+\d+",          # Điều 1, Điều 10 ...
    r"\bKhoản\s+\d+",         # Khoản 1, Khoản 2 ...
    r"\bĐiểm\s+[a-zđ]\)",     # Điểm a), Điểm b) ...
    r"\bNghị\s+định\b",
    r"\bThông\s+tư\b",
    r"\bQuyết\s+định\b",
    r"\bQuy\s+chế\b",
    r"\bQuy\s+định\b",
    r"\bNội\s+quy\b",
]

# Ranh giới tách chunk cho văn bản hành chính — ưu tiên từ lớn đến nhỏ
_ADMIN_SEPARATORS = [
    r"(?=\nNghị\s+định\s+[\d/]+)",      # Nghị định (bao gồm số hiệu /NĐ-CP)
    r"(?=\nThông\s+tư\s+[\d/]+)",        # Thông tư
    r"(?=\nQuyết\s+định\s+[\d/]+)",      # Thêm Quyết định (rất phổ biến)
    r"(?=\nChương\s+[IVXLCDMivxlcdm\d]+)", # Chương dùng số La Mã hoặc số thường
    r"(?=\nMục\s+\d+)",                 # Thêm Mục (dưới Chương, trên Điều)
    r"(?=\nĐiều\s+\d+)",                 
    r"(?=\nKhoản\s+\d+)",                
    r"(?=\n[a-zđ]\)\s+)",                # Điểm a), b)... ở đầu dòng
    r"\n\n", 
    r"\.\s+",                            # Dấu chấm kết thúc câu
    r"\n",
    r" ",
]


# Separator thông thường
_NORMAL_SEPARATORS = ["\n\n", "\n", ".", " "]


def _is_page_scanned(page_text: str, min_text_ratio: float = 0.1) -> bool:
    """
    Phát hiện nếu một trang PDF là scan (ít text được extracted từ layer).
    
    Args:
        page_text: Text extracted từ PDF page
        min_text_ratio: Nếu extracted text < 10% expected, coi là scanned
    
    Returns:
        True nếu page có vẻ là scan (thiếu text), False nếu là text-based PDF
    """
    # Nếu page text quá ngắn → có khả năng là scan
    # Giả sử một trang text-based PDF nên có ít nhất 500 ký tự
    return len(page_text.strip()) < 500


def _extract_images_from_pdf_page(page):
    """
    Extract tất cả images từ một PDF page object (fitz/PyMuPDF).
    Returns list of PIL Image objects.
    """
    from PIL import Image
    images = []
    try:
        image_list = page.get_images()
        for img_index in image_list:
            xref = page.get_image(img_index)
            pix = page.parent.get_pixmap(xref=xref)
            # Convert pixmap to PIL Image
            img_data = pix.tobytes("ppm")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
    except Exception as e:
        logging.warning(f"Failed to extract images from page: {e}")
    return images


# (Old OCR function removed - replaced above)


# Separator thông thường
_NORMAL_SEPARATORS = ["\n\n", "\n", ".", " "]


def _build_chroma_filter(conditions: dict) -> Optional[dict]:
    """Build Chroma where filter with a single root operator when needed."""
    clean_conditions = {k: v for k, v in conditions.items() if v is not None}
    if not clean_conditions:
        return None
    if len(clean_conditions) == 1:
        return clean_conditions
    return {"$and": [{k: v} for k, v in clean_conditions.items()]}


def _is_administrative_text(full_text: str) -> bool:
    """Phát hiện văn bản hành chính dựa trên regex patterns."""
    matches = sum(1 for p in _ADMIN_DOC_PATTERNS if re.search(p, full_text, re.IGNORECASE))
    return matches >= 2  # Cần ít nhất 2 pattern khớp để chắc chắn


def _split_administrative(pages: list[LCDocument]) -> list[LCDocument]:
    """
    Tách văn bản hành chính theo ranh giới Điều/Khoản/Điểm.
    Mỗi chunk cố gắng giữ một Điều (hoặc Khoản nhỏ) hoàn chỉnh.
    """
    # Ghép toàn bộ text lại
    full_text = "\n".join(p.page_content for p in pages)
    base_meta = pages[0].metadata if pages else {}

    # Tách theo Điều trước tiên
    article_pattern = re.compile(r"(?=\nĐiều\s+\d+[\s\.\:])", re.IGNORECASE)
    raw_chunks = article_pattern.split("\n" + full_text)

    # Nếu không tách được (không có Điều) → fallback sang tách khoản
    if len(raw_chunks) <= 1:
        clause_pattern = re.compile(r"(?=\nKhoản\s+\d+[\s\.\:])", re.IGNORECASE)
        raw_chunks = clause_pattern.split("\n" + full_text)

    # Bổ sung splitter dự phòng nếu chunk vẫn quá dài (>2000 chars)
    fallback_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=_NORMAL_SEPARATORS,
    )

    result: list[LCDocument] = []
    for chunk_text in raw_chunks:
        chunk_text = chunk_text.strip()
        if not chunk_text:
            continue
        # Extract Điều title để prepend vào sub-chunks
        title_match = re.match(r"(Điều\s+\d+[^\n]*)", chunk_text, re.IGNORECASE)
        article_header = title_match.group(1).strip() if title_match else ""

        if len(chunk_text) <= 1200:
            result.append(LCDocument(page_content=chunk_text, metadata=dict(base_meta)))
        else:
            # Quá dài → tách tiếp nhưng giữ header
            sub_docs = fallback_splitter.split_text(chunk_text)
            for i, sub in enumerate(sub_docs):
                # Thêm header vào sub-chunks không phải sub đầu tiên
                content = sub if i == 0 or not article_header else f"[{article_header}] (tiếp)\n{sub}"
                result.append(LCDocument(page_content=content, metadata=dict(base_meta)))

    return result if result else [LCDocument(page_content=full_text[:2000], metadata=dict(base_meta))]


def _split_normal(pages: list[LCDocument]) -> list[LCDocument]:
    """Tách văn bản thông thường theo ký tự/dòng."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=_NORMAL_SEPARATORS,
    )
    return splitter.split_documents(pages)


class ChromaDBManager:
    def __init__(self):
        self.persist_directory = CHROMA_PERSIST_DIR
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.vectordb = Chroma(persist_directory=self.persist_directory, embedding_function=self.embeddings)

    def process_and_store_pdf(
        self,
        file_path: str,
        doc_id: int,
        owner_id: int,
        department_id: int,
        scope: str,
        tags: str,
        session_id: Optional[int] = None,
        force_admin_chunking: bool = False,
    ) -> int:
        """
        Load PDF, detect scanned pages, OCR nếu cần, then chunk và store.

        Strategy:
        - Load pages với PyMuPDFLoader
        - Detect trang scan (nếu extracted text quá ít)
        - OCR trang scan và augment text
        - Auto-detect loại văn bản và chunking phù hợp
        - Lưu vào ChromaDB

        Args:
            force_admin_chunking: Bắt buộc dùng chunking hành chính
        Returns:
            Số lượng chunks đã lưu
        """
        import fitz  # PyMuPDF
        
        loader = PyMuPDFLoader(file_path)
        pages = loader.load()

        if not pages:
            return 0

        # Enhance pages với OCR nếu detect scan
        pdf_doc = fitz.open(file_path)
        enhanced_pages = []
        
        for page_idx, page in enumerate(pages):
            original_text = page.page_content
            
            # Check nếu trang này là scan (thiếu text)
            if _is_page_scanned(original_text):
                logging.info(f"Page {page_idx} detected as scanned, running OCR...")
                try:
                    pdf_page = pdf_doc[page_idx]
                    ocr_text = _ocr_page_to_text(pdf_page)
                    
                    if ocr_text.strip():
                        # Merge: OCR text + original text (nếu có)
                        if original_text.strip():
                            page.page_content = f"{original_text}\n\n[OCR Result]\n{ocr_text}"
                        else:
                            page.page_content = ocr_text
                        logging.info(f"Page {page_idx} OCR success: {len(ocr_text)} chars extracted")
                    else:
                        logging.warning(f"Page {page_idx} OCR returned empty result")
                except Exception as e:
                    logging.error(f"OCR failed for page {page_idx}: {e}")
                    # Keep original text on OCR failure
            
            enhanced_pages.append(page)
        
        pdf_doc.close()

        # Nhận diện loại văn bản
        sample_text = "\n".join(p.page_content for p in enhanced_pages[:5])
        is_admin = force_admin_chunking or _is_administrative_text(sample_text)

        if is_admin:
            splits = _split_administrative(enhanced_pages)
            chunk_strategy = "administrative"
        else:
            splits = _split_normal(enhanced_pages)
            chunk_strategy = "normal"

        # Gắn metadata
        for split in splits:
            split.metadata.update(
                {
                    "doc_id": doc_id,
                    "owner_id": owner_id,
                    "department_id": department_id,
                    "scope": scope,
                    "tags": tags or "",
                    "session_id": session_id,
                    "chunk_strategy": chunk_strategy,
                }
            )

        self.vectordb.add_documents(documents=splits)
        return len(splits)
    
    def process_and_store_word(
        self,
        file_path: str,
        doc_id: int,
        owner_id: int,
        department_id: int,
        scope: str,
        tags: str,
        session_id: Optional[int] = None,
        force_admin_chunking: bool = False,
    ) -> int:
        """
        Load Word (.docx), auto-detect document type and apply chunking.

        Note: Word files rarely scanned, but support is added for consistency.

        Args:
            force_admin_chunking: Force administrative chunking even if not detected
        Returns:
            Number of chunks saved
        """
        loader = Docx2txtLoader(file_path)
        pages = loader.load()

        if not pages:
            return 0

        sample_text = "\n".join(p.page_content for p in pages[:5]) 
        is_admin = force_admin_chunking or _is_administrative_text(sample_text)

        if is_admin:
            splits = _split_administrative(pages)
            chunk_strategy = "administrative"
        else:
            splits = _split_normal(pages)
            chunk_strategy = "normal"

        for split in splits:
            split.metadata.update(
                {
                    "doc_id": doc_id,
                    "owner_id": owner_id,
                    "department_id": department_id,
                    "scope": scope,
                    "tags": tags or "",
                    "session_id": session_id,
                    "chunk_strategy": chunk_strategy,
                }
            )

        self.vectordb.add_documents(documents=splits)
        return len(splits)

    def search_context_with_filter(
        self,
        query: str,
        user_id: int,
        user_dept_id: int,
        search_scope: str = "personal",
        k: int = 5,
        session_id: Optional[int] = None,
        extra_doc_ids: Optional[list[int]] = None,
    ):
        """
        Tìm kiếm ngữ cảnh có filter theo scope và quyền.

        Args:
            extra_doc_ids: Danh sách doc_id được đính kèm thủ công vào session,
                           sẽ được OR-kết hợp với filter scope chính.
        """
        # Xây dựng điều kiện filter chính theo scope
        scope_conditions: dict = {}
        if search_scope == "personal":
            scope_conditions["owner_id"] = user_id
            if session_id is not None:
                scope_conditions["session_id"] = session_id
        elif search_scope == "department":
            scope_conditions["department_id"] = user_dept_id
        elif search_scope in ("sqp", "company"):
            scope_conditions["scope"] = "sqp"

        scope_filter = _build_chroma_filter(scope_conditions)

        # Tìm kiếm chính theo scope
        if scope_filter:
            docs = self.vectordb.similarity_search(query, k=k, filter=scope_filter)
        else:
            docs = self.vectordb.similarity_search(query, k=k)

        # Tìm thêm từ doc_ids đính kèm (nếu có)
        if extra_doc_ids:
            attached_docs = []
            for doc_id in extra_doc_ids:
                try:
                    results = self.vectordb.similarity_search(
                        query, k=2, filter={"doc_id": doc_id}
                    )
                    attached_docs.extend(results)
                except Exception:
                    pass
            # Merge, deduplicate
            existing_content = {d.page_content for d in docs}
            for d in attached_docs:
                if d.page_content not in existing_content:
                    docs.append(d)
                    existing_content.add(d.page_content)

        text_content = "\n\n".join([doc.page_content for doc in docs])
        sources = list(set([str(doc.metadata.get("doc_id", "N/A")) for doc in docs]))
        return text_content, sources

    def get_doc_ids_for_collection(self) -> list[int]:
        """Trả về tất cả doc_id đã được index trong ChromaDB."""
        try:
            collection = self.vectordb._collection
            results = collection.get(include=["metadatas"])
            ids = set()
            for meta in results.get("metadatas", []):
                if meta and "doc_id" in meta:
                    ids.add(int(meta["doc_id"]))
            return list(ids)
        except Exception:
            return []

    def delete_doc_from_index(self, doc_id: int) -> int:
        """Xóa tất cả chunks của một tài liệu khỏi ChromaDB theo doc_id."""
        try:
            collection = self.vectordb._collection
            results = collection.get(include=["metadatas"])
            ids_to_delete = [
                results["ids"][i]
                for i, meta in enumerate(results.get("metadatas", []))
                if meta and str(meta.get("doc_id")) == str(doc_id)
            ]
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
            return len(ids_to_delete)
        except Exception:
            return 0

    def admin_clear_db(self):
        self.vectordb.delete_collection()
        self.vectordb = Chroma(persist_directory=self.persist_directory, embedding_function=self.embeddings)
        return "Cleaned"
