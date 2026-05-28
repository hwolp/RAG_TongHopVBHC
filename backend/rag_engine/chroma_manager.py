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

from langchain_core.documents import Document as LCDocument

from config import (
    CHROMA_PERSIST_DIR,
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
    r"\b[yý]\s+ch[ií]nh\b",
    r"\bkh[aá]i\s+qu[aá]t\b",
    r"\bt[oà]ng\s+quan\b",
]
_STRUCTURE_QUERY_PATTERNS = [
    r"\bt[aấ]t\s+c[aả]\s+c[aá]c\s+ch[uư][ơo]ng\b",
    r"\bli[eệ]t\s+k[eê].*\bch[uư][ơo]ng\b",
    r"\bdanh\s+s[aá]ch.*\bch[uư][ơo]ng\b",
    r"\bm[uụ]c\s+l[uụ]c\b",
    r"\bc[aấ]u\s+tr[uú]c\b",
]
_DEFAULT_RETRIEVAL_K = 8
_ATTACHED_DOC_RETRIEVAL_K = 6
_SUMMARY_DOC_CONTEXT_LIMIT = 16
_PARENT_CONTEXT_LIMIT = 8
_STRUCTURE_CONTEXT_METADATA_LIMIT = 5000
_STRUCTURE_CONTEXT_PREFIX = "Văn bản gồm các phần sau:"
_ARTICLE_DIRECT_RETRIEVAL_MAX = 2   # tối đa retrieve trực tiếp 2 Điều / query
_ARTICLE_DIRECT_CHUNK_LIMIT = 30    # một Điều hiếm khi có > 30 chunks
_ARTICLE_QUERY_PATTERN = re.compile(
    r"\bđi[eềệ]u\s+(\d+)\b",
    re.IGNORECASE,
)


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
    def __init__(self, document_processor: DocumentProcessor | None = None):
        self.persist_directory = CHROMA_PERSIST_DIR
        self.embeddings = self._load_embeddings()
        self.vectordb = Chroma(persist_directory=self.persist_directory, embedding_function=self.embeddings)
        self.document_processor = document_processor or DocumentProcessor()

    def _load_embeddings(self) -> HuggingFaceEmbeddings:
        model_options = {
            "model_name": EMBEDDING_MODEL,
            "cache_folder": EMBEDDING_MODEL_CACHE_DIR,
        }
        try:
            return HuggingFaceEmbeddings(
                **model_options,
                model_kwargs={"local_files_only": True},
            )
        except Exception:
            if not EMBEDDING_MODEL_ALLOW_DOWNLOAD:
                raise
            return HuggingFaceEmbeddings(**model_options)

    def add_documents(self, documents: list[LCDocument]) -> int:
        if not documents:
            return 0
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
    ) -> tuple[str, list[str]]:
        scope_filter = self._scope_filter(user_id, user_dept_id, search_scope, session_id)
        if _is_structure_query(query):
            structure_context, structure_sources = self._structure_context(scope_filter, extra_doc_ids)
            if structure_context:
                return structure_context, structure_sources

        docs = self._article_aware_search(query, scope_filter, k)
        docs = self._merge_attached_docs(query, docs, extra_doc_ids)
        docs = self._expand_parent_context(docs)

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
