import logging
import re
import unicodedata
from threading import Lock
from typing import Optional

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_core.documents import Document as LCDocument

from config import (
    CHROMA_PERSIST_DIR,
    EMBEDDING_DEVICE,
    EMBEDDING_MODEL,
    EMBEDDING_MODEL_ALLOW_DOWNLOAD,
    EMBEDDING_MODEL_CACHE_DIR,
)
from contracts.rag import VectorStoreInterface
from rag_engine.models import DocumentIndexMetadata
from services.rag.document_processor import (
    DocumentProcessor,
    _is_administrative_text,
    _split_administrative,
    _split_normal,
)

_SUMMARY_QUERY_PATTERNS = [
    r"\bt[oó]m\s+t[aắ]t\b",
    r"\bn[oộ]i\s+dung\s+ch[ií]nh\b",
    r"\bn[oó]i\s+v[eề]\s+",
    r"\bn[oộ]i\s+dung\s+(?:g[iì]|l[aà])\b",
    r"\bv[aă]n\s+b[aả]n.*\bn[oó]i\b",
    r"\bv[aă]n\s+b[aả]n.*\bn[oộ]i\s+dung\b",
    r"\b[yý]\s+ch[ií]nh\b",
    r"\bkh[aá]i\s+qu[aá]t\b",
    r"\bt[oà]ng\s+quan\b",
    r"\bli[eệ]t\s+k[eê].*\bn[oộ]i\s+dung\b",
    r"\bc[aá]c\s+n[oộ]i\s+dung\s+ch[ií]nh\b",
]
_STRUCTURE_QUERY_PATTERNS = [
    r"\bt[aấ]t\s+c[aả]\s+c[aá]c\s+ch[uư][ơo]ng\b",
    r"\bli[eệ]t\s+k[eê].*\bch[uư][ơo]ng\b",
    r"\bdanh\s+s[aá]ch.*\bch[uư][ơo]ng\b",
    r"\bli[eệ]t\s+k[eê].*\b[đd]i[eềệ]u\b",
    r"\bdanh\s+s[aá]ch.*\b[đd]i[eềệ]u\b",
    r"\bbao\s+nhi[eê]u\s+[đd]i[eềệ]u\b",
    r"\bc[oó]\s+m[aấ]y\s+[đd]i[eềệ]u\b",
    r"\bg[oồ]m\s+m[aấ]y\s+[đd]i[eềệ]u\b",
    r"\bg[oồ]m\s+bao\s+nhi[eê]u\s+[đd]i[eềệ]u\b",
    r"\bbao\s+nhi[eê]u\s+ch[uư][ơo]ng\b",
    r"\bc[oó]\s+m[aấ]y\s+ch[uư][ơo]ng\b",
    r"\bg[oồ]m\s+m[aấ]y\s+ch[uư][ơo]ng\b",
    r"\bg[oồ]m\s+bao\s+nhi[eê]u\s+ch[uư][ơo]ng\b",
    r"\bm[uụ]c\s+l[uụ]c\b",
    r"\bc[aấ]u\s+tr[uú]c\b",
]
_DEFAULT_RETRIEVAL_K = 4
_VECTOR_CANDIDATE_K = 12
_ATTACHED_DOC_RETRIEVAL_K = 3
_SUMMARY_DOC_CONTEXT_LIMIT = 16
_PARENT_CONTEXT_LIMIT = 2
_PARENT_EXPANSION_SEED_LIMIT = 6
_STRUCTURE_CONTEXT_METADATA_LIMIT = 5000
_STRUCTURE_CONTEXT_PREFIX = "Văn bản gồm các phần sau:"
_ARTICLE_DIRECT_RETRIEVAL_MAX = 2   # tối đa retrieve trực tiếp 2 Điều / query
_ARTICLE_DIRECT_CHUNK_LIMIT = 10    # một Điều hiếm khi có > 30 chunks
_MAX_CONTEXT_CHUNKS = 5  #Mac dinh 12 tối đa 5 chunks liên quan đến một Điều để tránh quá tải context khi Điều đó có nhiều khoản nhỏ
_MAX_CONTEXT_CHARS = 4000  # tối đa 4000 ký tự liên quan đến một Điều để tránh quá tải context khi Điều đó có nhiều khoản nhỏ
_KEYWORD_SCAN_LIMIT = 5000
_LEXICAL_CANDIDATE_LIMIT = 24
_ARTICLE_QUERY_PATTERN = re.compile(
    r"\bđi[eềệ]u\s+(\d+)\b",
    re.IGNORECASE,
)
_LEXICAL_STOP_WORDS = {
    "ai",
    "bi",
    "bo",
    "cac",
    "cai",
    "can",
    "cho",
    "co",
    "cua",
    "duoc",
    "gi",
    "gom",
    "hay",
    "la",
    "lam",
    "mot",
    "nao",
    "nay",
    "nhung",
    "noi",
    "quy",
    "theo",
    "thi",
    "trong",
    "tu",
    "van",
    "ve",
}
_KEYWORD_ROUTES = [
    (
        "doi_tuong_ap_dung",
        [
            "đối tượng áp dụng",
            "áp dụng cho ai",
            "áp dụng đối với",
            "thông tư này áp dụng",
            "văn bản áp dụng",
            "không áp dụng",
            "không áp dụng với",
        ],
        ["đối tượng áp dụng", "áp dụng đối với", "không áp dụng"],
    ),
    (
        "pham_vi_dieu_chinh",
        ["phạm vi điều chỉnh", "phạm vi áp dụng"],
        ["phạm vi điều chỉnh", "phạm vi áp dụng"],
    ),
    (
        "trang_phuc",
        ["trang phục", "quân phục", "lễ phục", "quần áo"],
        ["trang phục", "quân phục", "lễ phục"],
    ),
    (
        "hieu_luc",
        ["hiệu lực", "ngày có hiệu lực", "thi hành", "áp dụng từ khi nào"],
        ["hiệu lực", "thi hành"],
    ),
    (
        "trach_nhiem_thi_hanh",
        ["trách nhiệm thi hành", "tổ chức thực hiện"],
        ["trách nhiệm thi hành", "tổ chức thực hiện"],
    ),
    (
        "dung_ten_dua_tin_buon",
        ["đứng tên", "đưa tin buồn", "tin buồn"],
        ["đứng tên", "đưa tin buồn", "tin buồn"],
    ),
]


def _build_chroma_filter(conditions: dict) -> Optional[dict]:
    """Build Chroma where filter with a single root operator when needed."""
    clean_conditions = {key: value for key, value in conditions.items() if value is not None}
    if not clean_conditions:
        return None
    if len(clean_conditions) == 1:
        return clean_conditions
    return {"$and": [{key: value} for key, value in clean_conditions.items()]}


def _is_summary_query(query: str) -> bool:
    return any(re.search(pattern, query or "", re.IGNORECASE) for pattern in _SUMMARY_QUERY_PATTERNS)


def _is_structure_query(query: str) -> bool:
    return any(re.search(pattern, query or "", re.IGNORECASE) for pattern in _STRUCTURE_QUERY_PATTERNS)


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", without_marks.replace("đ", "d").replace("Đ", "D").lower()).strip()


def _tokenize_text(value: str) -> set[str]:
    normalized = _normalize_text(value)
    tokens = set(re.findall(r"[a-z0-9]+", normalized))
    return {token for token in tokens if len(token) >= 2 and token not in _LEXICAL_STOP_WORDS}


def is_structure_context(context: str) -> bool:
    return context.startswith(_STRUCTURE_CONTEXT_PREFIX) or context.startswith("Cấu trúc tài liệu được index:")


def _natural_sort_key(value: str) -> tuple[int, str]:
    normalized = str(value or "").strip()
    if normalized.isdigit():
        return int(normalized), ""
    roman_values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    previous = 0
    for char in reversed(normalized.upper()):
        current = roman_values.get(char, 0)
        if current < previous:
            total -= current
        else:
            total += current
            previous = current
    return (total or 9999), normalized


def _article_sort_number(value: str) -> Optional[int]:
    normalized = str(value or "").strip()
    return int(normalized) if normalized.isdigit() else None


def _clean_structure_title(value: str) -> str:
    title = re.sub(r"\s+", " ", value or "").strip()
    replacements = [
        (r"\b[ĐđD][ÓỐóố]I\s+V[Ớớ]I\b", "ĐỐI VỚI"),
        (r"\bQUẦN\s+NHÂN\b", "QUÂN NHÂN"),
        (r"\bTỎ\s+CHỨC\b", "TỔ CHỨC"),
        (r"\bTHỊ\s+HÀNH\d*\b", "THI HÀNH"),
        (r"\btỗ chức\b", "tổ chức"),
        (r"\bPhân cấp tỗ chức\b", "Phân cấp tổ chức"),
        (r"\blời điền\b", "lời điếu"),
        (r"\bNhân đân\b", "Nhân dân"),
        (r"\bnhân đân\b", "nhân dân"),
        (r"\bbảo đám\b", "bảo đảm"),
    ]
    for pattern, replacement in replacements:
        title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
    title = re.sub(r"^[*®\s]+", "", title)
    title = re.sub(r"[“”‘’\"'®ế\d\s]+$", "", title)
    return title.strip(" .:-")


class ChromaDBManager(VectorStoreInterface):
    _embeddings_cache: dict[tuple[str, str, str], HuggingFaceEmbeddings] = {}
    _embeddings_lock = Lock()

    def __init__(self, document_processor: DocumentProcessor | None = None):
        self.persist_directory = CHROMA_PERSIST_DIR
        self.embeddings = self._load_embeddings()
        self.vectordb = Chroma(persist_directory=self.persist_directory, embedding_function=self.embeddings)
        self.document_processor = document_processor or DocumentProcessor()

    def _load_embeddings(self) -> HuggingFaceEmbeddings | None:
        cache_key = (EMBEDDING_MODEL, EMBEDDING_MODEL_CACHE_DIR, EMBEDDING_DEVICE)
        cached_embeddings = self._embeddings_cache.get(cache_key)
        if cached_embeddings is not None:
            return cached_embeddings

        with self._embeddings_lock:
            cached_embeddings = self._embeddings_cache.get(cache_key)
            if cached_embeddings is not None:
                return cached_embeddings

            try:
                embeddings = self._create_embeddings()
            except OSError:
                logging.warning(
                    "Embedding model '%s' could not be loaded in the current memory budget; falling back to metadata-driven retrieval only.",
                    EMBEDDING_MODEL,
                )
                return None
            self._embeddings_cache[cache_key] = embeddings
            return embeddings

    def _create_embeddings(self) -> HuggingFaceEmbeddings:
        model_options = {
            "model_name": EMBEDDING_MODEL,
            "cache_folder": EMBEDDING_MODEL_CACHE_DIR,
        }
        model_kwargs = {}
        device = self._resolve_embedding_device()
        if device:
            model_kwargs["device"] = device
        if EMBEDDING_MODEL == "dangvantuan/vietnamese-document-embedding":
            model_kwargs["trust_remote_code"] = True
        try:
            embeddings = HuggingFaceEmbeddings(
                **model_options,
                model_kwargs={**model_kwargs, "local_files_only": True},
            )
        except Exception:
            if not EMBEDDING_MODEL_ALLOW_DOWNLOAD:
                raise
            embeddings = HuggingFaceEmbeddings(**model_options, model_kwargs=model_kwargs)
        self._repair_embedding_model(embeddings)
        return embeddings

    @staticmethod
    def _resolve_embedding_device() -> str:
        requested_device = (EMBEDDING_DEVICE or "auto").strip().lower()
        if requested_device not in {"auto", "cuda", "cpu"}:
            requested_device = "auto"
        if requested_device == "cpu":
            return "cpu"
        try:
            import torch

            cuda_available = torch.cuda.is_available()
        except Exception:
            cuda_available = False
        if requested_device == "cuda" and not cuda_available:
            return "cpu"
        return "cuda" if cuda_available else "cpu"

    @staticmethod
    def _repair_embedding_model(embeddings: HuggingFaceEmbeddings) -> None:
        client = getattr(embeddings, "_client", None) or getattr(embeddings, "client", None)
        if not client or EMBEDDING_MODEL != "dangvantuan/vietnamese-document-embedding":
            return
        try:
            import torch

            transformer = client[0] if hasattr(client, "__getitem__") else None
            auto_model = getattr(transformer, "auto_model", None)
            model = getattr(auto_model, "Vietnamese", auto_model)
            embedding_layer = getattr(model, "embeddings", None)
            config = getattr(auto_model, "config", None)
            max_positions = getattr(config, "max_position_embeddings", None)
            word_embeddings = getattr(embedding_layer, "word_embeddings", None)
            if not embedding_layer or not max_positions or not word_embeddings:
                return
            position_ids = torch.arange(max_positions, device=word_embeddings.weight.device)
            embedding_layer.register_buffer("position_ids", position_ids, persistent=False)
        except Exception:
            return

    def add_documents(self, documents: list[LCDocument]) -> int:
        if not documents:
            return 0
        if self.embeddings is None:
            raise RuntimeError("Embedding model is required to index documents but could not be loaded")
        self.vectordb.add_documents(documents=documents)
        return len(documents)

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
        metadata = DocumentIndexMetadata(
            doc_id=doc_id,
            owner_id=owner_id,
            department_id=department_id,
            scope=scope,
            tags=tags,
            session_id=session_id,
        )
        splits = self.document_processor.process_pdf(file_path, metadata, force_admin_chunking)
        return self.add_documents(splits)

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
        metadata = DocumentIndexMetadata(
            doc_id=doc_id,
            owner_id=owner_id,
            department_id=department_id,
            scope=scope,
            tags=tags,
            session_id=session_id,
        )
        splits = self.document_processor.process_word(file_path, metadata, force_admin_chunking)
        return self.add_documents(splits)

    def search_context_with_filter(
        self,
        query: str,
        user_id: int,
        user_dept_id: int,
        search_scope: str = "personal",
        k: int = _DEFAULT_RETRIEVAL_K,
        session_id: Optional[int] = None,
        extra_doc_ids: Optional[list[int]] = None,
        original_query: Optional[str] = None,
    ) -> tuple[str, list[str]]:
        scope_filter = self._scope_filter(user_id, user_dept_id, search_scope, session_id)
        detection_queries = self._query_variants(original_query, query)
        structure_query = " ".join(detection_queries)
        if _is_structure_query(structure_query):
            structure_context, structure_sources = self._structure_context(scope_filter, extra_doc_ids)
            if structure_context:
                return structure_context, structure_sources
        if _is_summary_query(structure_query):
            summary_context, summary_sources = self._summary_overview_context(scope_filter, extra_doc_ids)
            if summary_context:
                self._log_retrieval(
                    question=original_query or query,
                    rewritten_query=query,
                    session_id=session_id,
                    extra_doc_ids=extra_doc_ids,
                    article_docs=[],
                    keyword_docs=[],
                    lexical_docs=[],
                    vector_docs=[],
                    final_docs=[],
                )
                return summary_context, summary_sources
            summary_docs = self._summary_context_docs(scope_filter, extra_doc_ids)
            if summary_docs:
                docs = self._trim_context_docs(summary_docs)
                return self._format_context_response(docs)

        keyword_targets = self._keyword_targets(detection_queries)
        keyword_docs = self._keyword_routed_search(detection_queries, scope_filter)
        article_docs = self._article_direct_search(structure_query, scope_filter)
        lexical_docs = self._lexical_candidate_search(detection_queries, scope_filter, keyword_targets)
        attached_docs = self._attached_docs(query, extra_doc_ids)
        vector_docs = self._similarity_search(query, max(k, _VECTOR_CANDIDATE_K), scope_filter)
        docs = self._rank_and_pack_context(
            queries=detection_queries,
            keyword_targets=keyword_targets,
            extra_doc_ids=extra_doc_ids,
            article_docs=article_docs,
            keyword_docs=keyword_docs,
            lexical_docs=lexical_docs,
            attached_docs=attached_docs,
            vector_docs=vector_docs,
        )
        self._log_retrieval(
            question=original_query or query,
            rewritten_query=query,
            session_id=session_id,
            extra_doc_ids=extra_doc_ids,
            article_docs=article_docs,
            keyword_docs=keyword_docs,
            lexical_docs=lexical_docs,
            vector_docs=vector_docs,
            final_docs=docs,
        )

        return self._format_context_response(docs)

    @staticmethod
    def _format_context_response(docs: list[LCDocument]) -> tuple[str, list[str]]:
        text_content = "\n\n".join(doc.page_content for doc in docs)
        sources = []
        seen_sources = set()
        for doc in docs:
            doc_id = doc.metadata.get("doc_id")
            if doc_id is None:
                continue
            source = str(doc_id)
            if source in seen_sources:
                continue
            sources.append(source)
            seen_sources.add(source)
        return text_content, sources

    @staticmethod
    def _query_variants(*queries: Optional[str]) -> list[str]:
        variants = []
        seen = set()
        for query in queries:
            clean = (query or "").strip()
            if not clean:
                continue
            normalized = _normalize_text(clean)
            if normalized in seen:
                continue
            variants.append(clean)
            seen.add(normalized)
        return variants

    def _scope_filter(
        self,
        user_id: int,
        user_dept_id: int,
        search_scope: str,
        session_id: Optional[int],
    ) -> Optional[dict]:
        scope_conditions: dict = {}
        if search_scope == "personal":
            scope_conditions["owner_id"] = user_id
            if session_id is not None:
                scope_conditions["session_id"] = session_id
        elif search_scope == "department":
            scope_conditions["department_id"] = user_dept_id
        elif search_scope in ("sqp", "company"):
            scope_conditions["scope"] = "sqp"
        return _build_chroma_filter(scope_conditions)

    def _similarity_search(self, query: str, k: int, scope_filter: Optional[dict]) -> list[LCDocument]:
        if self.embeddings is None:
            return []
        if scope_filter:
            return self.vectordb.similarity_search(query, k=k, filter=scope_filter)
        return self.vectordb.similarity_search(query, k=k)

    def _extract_article_numbers(self, query: str) -> list[str]:
        """Trích xuất danh sách số Điều được nhắc trong câu hỏi.

        Ví dụ: 'Điều 6 có nội dung gì?'  → ['6']
                 'Điều 3 và Điều 5'       → ['3', '5']
        Giới hạn tối đa _ARTICLE_DIRECT_RETRIEVAL_MAX Điều.
        """
        matches = _ARTICLE_QUERY_PATTERN.findall(query or "")
        return matches[:_ARTICLE_DIRECT_RETRIEVAL_MAX]

    def _combine_with_scope(
        self,
        scope_filter: Optional[dict],
        extra_condition: dict,
    ) -> dict:
        """Kết hợp scope_filter sẵn có với một điều kiện metadata bổ sung.

        Xử lý 3 trường hợp:
        - scope_filter là None              → chỉ dùng extra_condition
        - scope_filter là {"$and": [...]}   → thêm extra_condition vào mảng $and
        - scope_filter là {"field": value}  → bọc cả hai trong $and
        """
        if not scope_filter:
            return extra_condition
        if "$and" in scope_filter:
            return {"$and": scope_filter["$and"] + [extra_condition]}
        return {"$and": [scope_filter, extra_condition]}

    def _combine_conditions(self, scope_filter: Optional[dict], *conditions: dict) -> dict:
        combined = scope_filter
        for condition in conditions:
            combined = self._combine_with_scope(combined, condition)
        return combined or {}

    def _get_article_chunks(self, where_filter: dict) -> list[LCDocument]:
        """Lấy toàn bộ chunks của một Điều trực tiếp từ ChromaDB theo metadata filter.

        Kết quả được sắp xếp theo parent_index → child_index để đảm bảo
        nội dung liên tục, đúng thứ tự trong văn bản gốc.
        """
        try:
            collection = self.vectordb._collection
            results = collection.get(
                where=where_filter,
                include=["documents", "metadatas"],
                limit=_ARTICLE_DIRECT_CHUNK_LIMIT,
            )
            documents = results.get("documents", []) or []
            metadatas = results.get("metadatas", []) or []
            docs = [
                LCDocument(page_content=content, metadata=metadatas[i] or {})
                for i, content in enumerate(documents)
                if content
            ]
            return sorted(
                docs,
                key=lambda d: (
                    int(d.metadata.get("parent_index") or 0),
                    int(d.metadata.get("child_index") or 0),
                ),
            )
        except Exception:
            return []

    def _article_aware_search(
        self,
        query: str,
        scope_filter: Optional[dict],
        k: int,
    ) -> list[LCDocument]:
        """Tìm kiếm thông minh: nếu query đề cập Điều cụ thể, lấy toàn bộ
        chunks của Điều đó trực tiếp từ metadata thay vì dùng similarity search.

        Lý do: similarity_search(k=8) có thể bỏ sót chunk của một Khoản nếu
        nội dung khoản đó có độ tương đồng vector thấp với câu hỏi.
        Truy vấn trực tiếp theo metadata đảm bảo lấy đủ mọi khoản.

        Fallback: nếu không tìm thấy chunk nào qua metadata,
        quay lại similarity search bình thường.
        """
        article_numbers = self._extract_article_numbers(query)
        if not article_numbers:
            return self._similarity_search(query, k, scope_filter)

        direct_docs: list[LCDocument] = []
        seen_content: set[str] = set()

        for article_number in article_numbers:
            article_filter = self._combine_with_scope(
                scope_filter,
                {"article_number": article_number},
            )
            for doc in self._get_article_chunks(article_filter):
                if doc.page_content not in seen_content:
                    direct_docs.append(doc)
                    seen_content.add(doc.page_content)

        if direct_docs:
            # Bổ sung similarity search để có thêm context liên quan
            for doc in self._similarity_search(query, k, scope_filter):
                if doc.page_content not in seen_content:
                    direct_docs.append(doc)
                    seen_content.add(doc.page_content)
            return direct_docs

        # Fallback: không tìm thấy qua metadata (ví dụ: chưa có article_number)
        import logging as _log
        _log.info(
            "Article-aware search found no direct chunks for %s, falling back to similarity",
            article_numbers,
        )
        return self._similarity_search(query, k, scope_filter)

    def _article_direct_search(self, query: str, scope_filter: Optional[dict]) -> list[LCDocument]:
        article_numbers = self._extract_article_numbers(query)
        if not article_numbers:
            return []

        direct_docs: list[LCDocument] = []
        for article_number in article_numbers:
            article_filter = self._combine_with_scope(scope_filter, {"article_number": article_number})
            direct_docs = self._merge_document_lists(direct_docs, self._get_article_chunks(article_filter))
        if not direct_docs:
            logging.info("Article-aware search found no direct chunks for %s", article_numbers)
        return direct_docs

    def _keyword_routed_search(self, queries: list[str], scope_filter: Optional[dict]) -> list[LCDocument]:
        targets = self._keyword_targets(queries)
        if not targets:
            return []

        try:
            collection = self.vectordb._collection
            kwargs = {
                "include": ["documents", "metadatas"],
                "limit": _KEYWORD_SCAN_LIMIT,
            }
            if scope_filter:
                kwargs["where"] = scope_filter
            results = collection.get(**kwargs)
        except Exception:
            return []

        routed_docs: list[LCDocument] = []
        seen_articles = set()
        documents = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []
        candidates = [
            LCDocument(page_content=content, metadata=metadatas[index] or {})
            for index, content in enumerate(documents)
            if content
        ]

        title_matches = []
        content_matches = []
        for doc in candidates:
            metadata = doc.metadata or {}
            haystack_title = " ".join(
                str(metadata.get(key) or "")
                for key in ("article_title", "chapter_title", "list_section_title", "list_item_title")
            )
            haystack_text = f"{haystack_title} {doc.page_content}"
            if self._matches_any_keyword(haystack_title, targets):
                title_matches.append(doc)
            elif self._matches_any_keyword(haystack_text, targets):
                content_matches.append(doc)

        for doc in title_matches + content_matches:
            metadata = doc.metadata or {}
            doc_id = metadata.get("doc_id")
            article_number = metadata.get("article_number")
            if doc_id is not None and article_number:
                article_key = (str(doc_id), str(article_number))
                if article_key in seen_articles:
                    continue
                seen_articles.add(article_key)
                article_filter = self._combine_conditions(
                    scope_filter,
                    {"doc_id": int(doc_id)},
                    {"article_number": str(article_number)},
                )
                routed_docs = self._merge_document_lists(routed_docs, self._get_article_chunks(article_filter))
            else:
                routed_docs = self._merge_document_lists(routed_docs, [doc])

        return routed_docs

    @staticmethod
    def _keyword_targets(queries: list[str]) -> list[str]:
        normalized_queries = " ".join(_normalize_text(query) for query in queries)
        targets = []
        for _, triggers, route_targets in _KEYWORD_ROUTES:
            if any(_normalize_text(trigger) in normalized_queries for trigger in triggers):
                targets.extend(route_targets)
        result = []
        seen = set()
        for target in targets:
            normalized = _normalize_text(target)
            if normalized in seen:
                continue
            result.append(target)
            seen.add(normalized)
        return result

    @staticmethod
    def _matches_any_keyword(value: str, keywords: list[str]) -> bool:
        normalized_value = _normalize_text(value)
        return any(_normalize_text(keyword) in normalized_value for keyword in keywords)

    def _lexical_candidate_search(
        self,
        queries: list[str],
        scope_filter: Optional[dict],
        keyword_targets: list[str],
    ) -> list[LCDocument]:
        query_tokens = self._query_tokens(queries, keyword_targets)
        if not query_tokens and not keyword_targets:
            return []

        candidates = self._scoped_documents(scope_filter, _KEYWORD_SCAN_LIMIT)
        scored: list[tuple[float, LCDocument]] = []
        for doc in candidates:
            score = self._lexical_score(doc, query_tokens, keyword_targets)
            if score <= 0:
                continue
            scored.append((score, doc))

        scored.sort(
            key=lambda item: (
                -item[0],
                int(item[1].metadata.get("doc_id") or 0),
                int(item[1].metadata.get("chunk_index") or 0),
            )
        )
        return [doc for _, doc in scored[:_LEXICAL_CANDIDATE_LIMIT]]

    def _scoped_documents(self, scope_filter: Optional[dict], limit: int) -> list[LCDocument]:
        try:
            collection = self.vectordb._collection
            kwargs = {
                "include": ["documents", "metadatas"],
                "limit": limit,
            }
            if scope_filter:
                kwargs["where"] = scope_filter
            results = collection.get(**kwargs)
        except Exception:
            return []

        documents = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []
        return [
            LCDocument(page_content=content, metadata=metadatas[index] or {})
            for index, content in enumerate(documents)
            if content
        ]

    def _rank_and_pack_context(
        self,
        queries: list[str],
        keyword_targets: list[str],
        extra_doc_ids: Optional[list[int]],
        article_docs: list[LCDocument],
        keyword_docs: list[LCDocument],
        lexical_docs: list[LCDocument],
        attached_docs: list[LCDocument],
        vector_docs: list[LCDocument],
    ) -> list[LCDocument]:
        query_tokens = self._query_tokens(queries, keyword_targets)
        attached_ids = {str(doc_id) for doc_id in extra_doc_ids or []}
        article_numbers = self._extract_article_numbers(" ".join(queries))
        scored: dict[tuple[str, str, str, str], tuple[float, LCDocument]] = {}

        def add_group(group: str, docs: list[LCDocument]) -> None:
            for rank, doc in enumerate(docs):
                score = self._retrieval_score(
                    doc=doc,
                    group=group,
                    rank=rank,
                    query_tokens=query_tokens,
                    keyword_targets=keyword_targets,
                    article_numbers=article_numbers,
                    attached_ids=attached_ids,
                )
                self._add_scored_doc(scored, doc, group, score)

        add_group("article", article_docs)
        add_group("keyword", keyword_docs)
        add_group("lexical", lexical_docs)
        add_group("attached", attached_docs)
        add_group("vector", vector_docs)

        ranked = self._sort_scored_docs(scored)
        parent_seeds = ranked[:_PARENT_EXPANSION_SEED_LIMIT]
        parent_docs = self._expand_parent_context(parent_seeds)
        for doc in parent_docs:
            if any(self._doc_key(doc) == self._doc_key(seed) for seed in parent_seeds):
                continue
            seed_score = self._best_parent_seed_score(doc, parent_seeds)
            self._add_scored_doc(scored, doc, "parent", max(20.0, seed_score - 8.0))

        ranked = self._sort_scored_docs(scored)
        return self._trim_context_docs(ranked)

    @staticmethod
    def _query_tokens(queries: list[str], keyword_targets: list[str]) -> set[str]:
        combined = " ".join(list(queries) + list(keyword_targets))
        return _tokenize_text(combined)

    def _lexical_score(self, doc: LCDocument, query_tokens: set[str], keyword_targets: list[str]) -> float:
        metadata = doc.metadata or {}
        title_text = self._metadata_title_text(metadata)
        content_text = doc.page_content or ""
        haystack = f"{title_text} {content_text}"
        haystack_tokens = _tokenize_text(haystack)
        score = 0.0
        if query_tokens:
            overlap = len(query_tokens & haystack_tokens) / max(len(query_tokens), 1)
            score += overlap * 30.0
        normalized_title = _normalize_text(title_text)
        normalized_text = _normalize_text(haystack)
        for target in keyword_targets:
            normalized_target = _normalize_text(target)
            if normalized_target and normalized_target in normalized_title:
                score += 25.0
            elif normalized_target and normalized_target in normalized_text:
                score += 12.0
        return score

    def _retrieval_score(
        self,
        doc: LCDocument,
        group: str,
        rank: int,
        query_tokens: set[str],
        keyword_targets: list[str],
        article_numbers: list[str],
        attached_ids: set[str],
    ) -> float:
        group_base = {
            "article": 100.0,
            "keyword": 82.0,
            "lexical": 55.0,
            "attached": 45.0,
            "vector": 36.0,
            "parent": 25.0,
        }.get(group, 20.0)
        metadata = doc.metadata or {}
        score = group_base + self._lexical_score(doc, query_tokens, keyword_targets)
        if str(metadata.get("doc_id") or "") in attached_ids:
            score += 8.0
        article_number = str(metadata.get("article_number") or "").strip()
        if article_number and article_number in article_numbers:
            score += 20.0
        if group == "vector":
            score += max(0.0, _VECTOR_CANDIDATE_K - rank)
        else:
            score += max(0.0, 6.0 - min(rank, 6))
        return score

    @staticmethod
    def _metadata_title_text(metadata: dict) -> str:
        return " ".join(
            str(metadata.get(key) or "")
            for key in ("article_title", "chapter_title", "list_section_title", "list_item_title", "title")
        )

    @staticmethod
    def _doc_key(doc: LCDocument) -> tuple[str, str, str, str]:
        metadata = doc.metadata or {}
        return (
            str(metadata.get("doc_id") or ""),
            str(metadata.get("chunk_index") or ""),
            str(metadata.get("parent_id") or ""),
            (doc.page_content or "")[:120],
        )

    def _add_scored_doc(
        self,
        scored: dict[tuple[str, str, str, str], tuple[float, LCDocument]],
        doc: LCDocument,
        group: str,
        score: float,
    ) -> None:
        key = self._doc_key(doc)
        existing = scored.get(key)
        if existing and existing[0] >= score:
            return
        metadata = dict(doc.metadata or {})
        metadata["_retrieval_group"] = group
        metadata["_retrieval_score"] = round(score, 3)
        scored[key] = (score, LCDocument(page_content=doc.page_content, metadata=metadata))

    @staticmethod
    def _sort_scored_docs(scored: dict[tuple[str, str, str, str], tuple[float, LCDocument]]) -> list[LCDocument]:
        # 1. Nhóm các chunk theo (doc_id, parent_id)
        groups: dict[tuple[int, str], list[tuple[float, LCDocument]]] = {}
        for score, doc in scored.values():
            meta = doc.metadata or {}
            doc_id = int(meta.get("doc_id") or 0)
            parent_id = str(meta.get("parent_id") or "")
            groups.setdefault((doc_id, parent_id), []).append((score, doc))

        # 2. Điểm đại diện của nhóm = Điểm cao nhất của chunk trong nhóm đó
        group_max_scores: dict[tuple[int, str], float] = {
            key: max(score for score, _ in items)
            for key, items in groups.items()
        }

        # 3. Sắp xếp nhóm theo điểm đại diện giảm dần, rồi xếp các chunk trong nhóm theo thứ tự tự nhiên
        sorted_docs = []
        for (doc_id, parent_id), items in sorted(
            groups.items(),
            key=lambda x: (
                -group_max_scores[x[0]],  # Nhóm điểm cao nhất lên đầu
                x[0][0],                  # doc_id
                x[0][1],                  # parent_id
            )
        ):
            # Sắp xếp các chunk nội bộ theo thứ tự xuất hiện gốc trong văn bản
            sorted_items = sorted(
                items,
                key=lambda item: (
                    int(item[1].metadata.get("parent_index") or 0),
                    int(item[1].metadata.get("child_index") or 0),
                    int(item[1].metadata.get("chunk_index") or 0),
                )
            )
            for _, doc in sorted_items:
                sorted_docs.append(doc)
        return sorted_docs

    def _best_parent_seed_score(self, doc: LCDocument, seeds: list[LCDocument]) -> float:
        metadata = doc.metadata or {}
        doc_id = str(metadata.get("doc_id") or "")
        parent_id = str(metadata.get("parent_id") or "")
        best = 25.0
        for seed in seeds:
            seed_meta = seed.metadata or {}
            if str(seed_meta.get("doc_id") or "") != doc_id:
                continue
            if str(seed_meta.get("parent_id") or "") != parent_id:
                continue
            best = max(best, float(seed_meta.get("_retrieval_score") or 25.0))
        return best

    def _merge_attached_docs(
        self,
        query: str,
        docs: list[LCDocument],
        extra_doc_ids: Optional[list[int]],
    ) -> list[LCDocument]:
        if not extra_doc_ids:
            return docs

        attached_docs: list[LCDocument] = []
        summary_query = _is_summary_query(query)
        for doc_id in extra_doc_ids:
            try:
                if summary_query:
                    attached_docs.extend(self.get_doc_context_chunks(doc_id, limit=_SUMMARY_DOC_CONTEXT_LIMIT))
                elif self.embeddings is None:
                    attached_docs.extend(self.get_doc_context_chunks(doc_id, limit=_ATTACHED_DOC_RETRIEVAL_K))
                else:
                    attached_docs.extend(
                        self.vectordb.similarity_search(
                            query,
                            k=_ATTACHED_DOC_RETRIEVAL_K,
                            filter={"doc_id": doc_id},
                        )
                    )
            except Exception:
                continue

        existing_content = {doc.page_content for doc in docs}
        for doc in attached_docs:
            if doc.page_content in existing_content:
                continue
            docs.append(doc)
            existing_content.add(doc.page_content)
        return docs

    def _attached_docs(self, query: str, extra_doc_ids: Optional[list[int]]) -> list[LCDocument]:
        if not extra_doc_ids:
            return []
        return self._merge_attached_docs(query, [], extra_doc_ids)

    def _summary_context_docs(
        self,
        scope_filter: Optional[dict],
        extra_doc_ids: Optional[list[int]],
    ) -> list[LCDocument]:
        docs: list[LCDocument] = []
        doc_ids = extra_doc_ids or self._doc_ids_for_filter(scope_filter)
        for doc_id in doc_ids:
            docs = self._merge_document_lists(docs, self.get_doc_context_chunks(int(doc_id), limit=_SUMMARY_DOC_CONTEXT_LIMIT))
        if docs:
            return docs

        try:
            collection = self.vectordb._collection
            kwargs = {
                "include": ["documents", "metadatas"],
                "limit": _SUMMARY_DOC_CONTEXT_LIMIT,
            }
            if scope_filter:
                kwargs["where"] = scope_filter
            results = collection.get(**kwargs)
            documents = results.get("documents", []) or []
            metadatas = results.get("metadatas", []) or []
            docs = [
                LCDocument(page_content=content, metadata=metadatas[index] or {})
                for index, content in enumerate(documents)
                if content
            ]
            return sorted(docs, key=lambda item: int(item.metadata.get("chunk_index") or 0))
        except Exception:
            return []

    def _summary_overview_context(
        self,
        scope_filter: Optional[dict],
        extra_doc_ids: Optional[list[int]],
    ) -> tuple[str, list[str]]:
        metadatas = self._metadata_for_structure(scope_filter)
        for doc_id in extra_doc_ids or []:
            metadatas.extend(self._metadata_for_structure({"doc_id": doc_id}))
        if not metadatas:
            return "", []

        docs: dict[str, dict] = {}
        preamble_by_doc: dict[str, list[tuple[int, str]]] = {}
        for meta in metadatas:
            if not meta or not meta.get("doc_id"):
                continue
            doc_id = str(meta.get("doc_id"))
            entry = docs.setdefault(doc_id, {"title": "", "articles": {}})
            title = _clean_structure_title(str(meta.get("title") or "").strip())
            if title and not entry["title"]:
                entry["title"] = title
            article_number = str(meta.get("article_number") or "").strip()
            article_title = _clean_structure_title(str(meta.get("article_title") or "").strip())
            if article_number and article_title:
                entry["articles"].setdefault(article_number, article_title)

        # Add a few opening chunks because scanned PDFs often store the true document
        # title in OCR text instead of PDF metadata.
        for doc_id in docs:
            for doc in self.get_doc_context_chunks(int(doc_id), limit=4):
                index = int(doc.metadata.get("chunk_index") or 0)
                preview = self._summary_preview(doc.page_content)
                if preview:
                    preamble_by_doc.setdefault(doc_id, []).append((index, preview))

        lines = ["Tổng quan nội dung văn bản:"]
        sources = []
        for doc_id in sorted(docs, key=_natural_sort_key):
            sources.append(doc_id)
            entry = docs[doc_id]
            lines.append(f"- Tài liệu {doc_id}:")
            if entry["title"]:
                lines.append(f"  - Nhan đề/metadata: {entry['title']}")
            for _, preview in sorted(preamble_by_doc.get(doc_id, []))[:3]:
                lines.append(f"  - Phần mở đầu: {preview}")
            if entry["articles"]:
                lines.append("  - Các nội dung/điều chính:")
                for article_number in sorted(entry["articles"], key=_natural_sort_key)[:20]:
                    lines.append(f"    - Điều {article_number}: {entry['articles'][article_number]}")

        return "\n".join(lines), sources

    @staticmethod
    def _summary_preview(content: str) -> str:
        text = re.sub(r"\s+", " ", content or "").strip()
        if not text:
            return ""
        useful_patterns = [
            r"(THÔNG TƯ .{0,500})",
            r"(V/v .{0,500})",
            r"(Quy định .{0,500})",
            r"(Triển khai .{0,500})",
        ]
        for pattern in useful_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()[:700]
        if "Người ký:" in text and len(text) < 260:
            return ""
        return text[:500]

    def _doc_ids_for_filter(self, scope_filter: Optional[dict]) -> list[int]:
        try:
            collection = self.vectordb._collection
            kwargs = {
                "include": ["metadatas"],
                "limit": _STRUCTURE_CONTEXT_METADATA_LIMIT,
            }
            if scope_filter:
                kwargs["where"] = scope_filter
            results = collection.get(**kwargs)
            ids = []
            seen = set()
            for metadata in results.get("metadatas", []) or []:
                doc_id = metadata.get("doc_id") if metadata else None
                if doc_id is None or str(doc_id) in seen:
                    continue
                ids.append(int(doc_id))
                seen.add(str(doc_id))
            return ids
        except Exception:
            return []

    def _expand_parent_context(self, docs: list[LCDocument]) -> list[LCDocument]:
        if not docs:
            return docs

        existing_content = {doc.page_content for doc in docs}
        expanded_docs = list(docs)
        seen_parents = set()
        for doc in docs:
            metadata = doc.metadata or {}
            doc_id = metadata.get("doc_id")
            parent_id = metadata.get("parent_id")
            if doc_id is None or not parent_id:
                continue
            parent_key = (str(doc_id), str(parent_id))
            if parent_key in seen_parents:
                continue
            seen_parents.add(parent_key)

            for parent_doc in self._get_parent_chunks(doc_id, str(parent_id)):
                if parent_doc.page_content in existing_content:
                    continue
                expanded_docs.append(parent_doc)
                existing_content.add(parent_doc.page_content)

        return expanded_docs

    @staticmethod
    def _merge_document_lists(*groups: list[LCDocument]) -> list[LCDocument]:
        merged: list[LCDocument] = []
        seen = set()
        for group in groups:
            for doc in group:
                metadata = doc.metadata or {}
                key = (
                    str(metadata.get("doc_id") or ""),
                    str(metadata.get("chunk_index") or ""),
                    str(metadata.get("parent_id") or ""),
                    doc.page_content[:120],
                )
                if key in seen:
                    continue
                merged.append(doc)
                seen.add(key)
        return merged

    @staticmethod
    def _trim_context_docs(docs: list[LCDocument]) -> list[LCDocument]:
        trimmed = []
        total_chars = 0
        for doc in docs:
            if len(trimmed) >= _MAX_CONTEXT_CHUNKS:
                break
            next_chars = len(doc.page_content or "")
            if trimmed and total_chars + next_chars > _MAX_CONTEXT_CHARS:
                break
            trimmed.append(doc)
            total_chars += next_chars
        return trimmed

    @staticmethod
    def _log_retrieval(
        question: str,
        rewritten_query: str,
        session_id: Optional[int],
        extra_doc_ids: Optional[list[int]],
        article_docs: list[LCDocument],
        keyword_docs: list[LCDocument],
        lexical_docs: list[LCDocument],
        vector_docs: list[LCDocument],
        final_docs: list[LCDocument],
    ) -> None:
        article_refs = []
        groups: dict[str, int] = {}
        for doc in final_docs:
            metadata = doc.metadata or {}
            group = str(metadata.get("_retrieval_group") or "unknown")
            groups[group] = groups.get(group, 0) + 1
            article = metadata.get("article_number")
            title = metadata.get("article_title")
            if article or title:
                score = metadata.get("_retrieval_score")
                article_refs.append(f"{article or '?'}:{title or ''}:{score or ''}")
        logging.info(
            "RAG retrieval question=%r rewritten=%r session_id=%s extra_doc_ids=%s "
            "article_hits=%s keyword_hits=%s lexical_hits=%s vector_hits=%s "
            "final_chunks=%s groups=%s articles=%s",
            question[:120],
            rewritten_query[:120],
            session_id,
            extra_doc_ids or [],
            len(article_docs),
            len(keyword_docs),
            len(lexical_docs),
            len(vector_docs),
            len(final_docs),
            groups,
            article_refs[:8],
        )

    def _get_parent_chunks(self, doc_id: int | str, parent_id: str) -> list[LCDocument]:
        try:
            collection = self.vectordb._collection
            results = collection.get(
                where={"$and": [{"doc_id": int(doc_id)}, {"parent_id": parent_id}]},
                include=["documents", "metadatas"],
                limit=_PARENT_CONTEXT_LIMIT,
            )
            documents = results.get("documents", []) or []
            metadatas = results.get("metadatas", []) or []
            parent_docs = [
                LCDocument(page_content=content, metadata=metadatas[index] or {})
                for index, content in enumerate(documents)
                if content
            ]
            return sorted(
                parent_docs,
                key=lambda item: (
                    int(item.metadata.get("parent_index") or 0),
                    int(item.metadata.get("child_index") or 0),
                    int(item.metadata.get("chunk_index") or 0),
                ),
            )
        except Exception:
            return []

    def _structure_context(
        self,
        scope_filter: Optional[dict],
        extra_doc_ids: Optional[list[int]] = None,
    ) -> tuple[str, list[str]]:
        metadatas = self._metadata_for_structure(scope_filter)
        for doc_id in extra_doc_ids or []:
            metadatas.extend(self._metadata_for_structure({"doc_id": doc_id}))

        structures: dict[str, dict] = {}
        for meta in metadatas:
            if not meta or not meta.get("doc_id"):
                continue
            doc_id = str(meta.get("doc_id"))
            doc_structure = structures.setdefault(doc_id, {"chapters": {}, "articles": {}, "list_sections": {}})

            chapter_number = str(meta.get("chapter_number") or "").strip()
            chapter_title = _clean_structure_title(str(meta.get("chapter_title") or "").strip())
            if chapter_number:
                chapter = doc_structure["chapters"].setdefault(
                    chapter_number,
                    {"title": chapter_title, "articles": {}},
                )
                if chapter_title and not chapter["title"]:
                    chapter["title"] = chapter_title

            article_number = str(meta.get("article_number") or "").strip()
            article_title = _clean_structure_title(str(meta.get("article_title") or "").strip())
            if article_number:
                article = {"title": article_title, "chapter_number": chapter_number}
                doc_structure["articles"].setdefault(article_number, article)
                if article_title and not article["title"]:
                    article["title"] = article_title
                if chapter_number:
                    doc_structure["chapters"][chapter_number]["articles"].setdefault(article_number, article)

            list_section_number = str(meta.get("list_section_number") or "").strip()
            list_section_title = _clean_structure_title(str(meta.get("list_section_title") or "").strip())
            list_item_number = str(meta.get("list_item_number") or "").strip()
            list_item_title = _clean_structure_title(str(meta.get("list_item_title") or "").strip())
            if list_section_number:
                section = doc_structure["list_sections"].setdefault(
                    list_section_number,
                    {"title": list_section_title, "items": {}},
                )
                if list_section_title and not section["title"]:
                    section["title"] = list_section_title
                if list_item_number:
                    item = section["items"].setdefault(list_item_number, {"title": list_item_title})
                    if list_item_title and not item["title"]:
                        item["title"] = list_item_title

        lines = [_STRUCTURE_CONTEXT_PREFIX]
        sources = []
        for doc_id in sorted(structures, key=_natural_sort_key):
            structure = structures[doc_id]
            sources.append(doc_id)
            article_count = len(structure["articles"])
            chapter_count = len(structure["chapters"])
            if article_count:
                lines.append(f"- Tổng số điều: {article_count}")
            if chapter_count:
                lines.append(f"- Tổng số chương: {chapter_count}")
            last_article_number = 0
            if structure["chapters"]:
                for chapter_number in sorted(structure["chapters"], key=_natural_sort_key):
                    chapter = structure["chapters"][chapter_number]
                    title = f": {chapter['title']}" if chapter["title"] else ""
                    lines.append(f"- Chương {chapter_number}{title}")
                    for article_number in sorted(chapter["articles"], key=_natural_sort_key):
                        numeric_article = _article_sort_number(article_number)
                        if numeric_article is not None and numeric_article <= last_article_number:
                            continue
                        if numeric_article is not None:
                            last_article_number = numeric_article
                        article = chapter["articles"][article_number]
                        article_title = f": {article['title']}" if article["title"] else ""
                        lines.append(f"  - Điều {article_number}{article_title}")
            elif structure["list_sections"]:
                for section_number in sorted(structure["list_sections"], key=_natural_sort_key):
                    section = structure["list_sections"][section_number]
                    title = f" {section['title']}" if section["title"] else ""
                    lines.append(f"- {section_number}.{title}")
                    for item_number in sorted(section["items"], key=_natural_sort_key):
                        item = section["items"][item_number]
                        item_title = f" {item['title']}" if item["title"] else ""
                        lines.append(f"  - {item_number}.{item_title}")
            elif structure["articles"]:
                for article_number in sorted(structure["articles"], key=_natural_sort_key):
                    article = structure["articles"][article_number]
                    article_title = f": {article['title']}" if article["title"] else ""
                    lines.append(f"- Điều {article_number}{article_title}")

        if len(lines) == 1:
            return "", []
        return "\n".join(lines), sources

    def _metadata_for_structure(self, where_filter: Optional[dict]) -> list[dict]:
        try:
            collection = self.vectordb._collection
            kwargs = {
                "include": ["metadatas"],
                "limit": _STRUCTURE_CONTEXT_METADATA_LIMIT,
            }
            if where_filter:
                kwargs["where"] = where_filter
            results = collection.get(**kwargs)
            return results.get("metadatas", []) or []
        except Exception:
            return []

    def get_doc_context_chunks(self, doc_id: int, limit: int = 12) -> list[LCDocument]:
        """Lấy trực tiếp các chunk đầu của một tài liệu, phù hợp cho câu hỏi tóm tắt/nội dung chính."""
        try:
            collection = self.vectordb._collection
            results = collection.get(
                where={"doc_id": doc_id},
                include=["documents", "metadatas"],
                limit=limit,
            )
            documents = results.get("documents", []) or []
            metadatas = results.get("metadatas", []) or []
            docs = [
                LCDocument(page_content=content, metadata=metadatas[index] or {})
                for index, content in enumerate(documents)
                if content
            ]
            return sorted(
                docs,
                key=lambda item: (
                    int(item.metadata.get("chunk_index") or 0),
                    int(item.metadata.get("child_index") or 0),
                ),
            )
        except Exception:
            return []

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
                results["ids"][index]
                for index, meta in enumerate(results.get("metadatas", []))
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
