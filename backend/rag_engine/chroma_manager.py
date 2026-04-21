import re
from typing import Optional

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
    r"(?=\nĐiều\s+\d+[\s\.\:])",   # Điều X:
    r"(?=\nKhoản\s+\d+[\s\.\:])",  # Khoản X:
    r"(?=\nĐiểm\s+[a-zđ]\))",      # Điểm a)
    r"\n\n",
    r"\n",
    r"\. ",
    r" ",
]

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
        Load PDF, tự động phát hiện loại văn bản và chunking phù hợp.

        - Văn bản hành chính (Điều/Khoản/Điểm) → chunk theo cấu trúc điều khoản
        - Văn bản thông thường → chunk theo ký tự (chunk_size=1000)

        Args:
            force_admin_chunking: Bắt buộc dùng chunking hành chính kể cả khi không detect được.
        Returns:
            Số lượng chunks đã lưu vào ChromaDB.
        """
        loader = PyMuPDFLoader(file_path)
        pages = loader.load()

        if not pages:
            return 0

        # Nhận diện loại văn bản
        sample_text = "\n".join(p.page_content for p in pages[:5])  # Sample 5 trang đầu
        is_admin = force_admin_chunking or _is_administrative_text(sample_text)

        if is_admin:
            splits = _split_administrative(pages)
            chunk_strategy = "administrative"
        else:
            splits = _split_normal(pages)
            chunk_strategy = "normal"

        # Gắn metadata cho tất cả các chunks
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
        Load Word (.docx), tự động phát hiện loại văn bản và chunking phù hợp.

        - Văn bản hành chính (Điều/Khoản/Điểm) → chunk theo cấu trúc điều khoản
        - Văn bản thông thường → chunk theo ký tự (chunk_size=1000)

        Args:
            force_admin_chunking: Bắt buộc dùng chunking hành chính kể cả khi không detect được.
        Returns:
            Số lượng chunks đã lưu vào ChromaDB.
        """
        loader = Docx2txtLoader(file_path)
        pages = loader.load()

        if not pages:
            return 0

        # Mặc định docx2txt thường gộp nội dung thành 1 page duy nhất, 
        # nhưng ta vẫn dùng vòng lặp để an toàn nếu dùng loader khác sau này.
        sample_text = "\n".join(p.page_content for p in pages[:5]) 
        is_admin = force_admin_chunking or _is_administrative_text(sample_text)

        if is_admin:
            splits = _split_administrative(pages)
            chunk_strategy = "administrative"
        else:
            splits = _split_normal(pages)
            chunk_strategy = "normal"

        # Gắn metadata cho tất cả các chunks
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
