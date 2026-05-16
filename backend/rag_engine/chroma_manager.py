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

from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL
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


class ChromaDBManager(VectorStoreInterface):
    def __init__(self, document_processor: DocumentProcessor | None = None):
        self.persist_directory = CHROMA_PERSIST_DIR
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.vectordb = Chroma(persist_directory=self.persist_directory, embedding_function=self.embeddings)
        self.document_processor = document_processor or DocumentProcessor()

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
        k: int = 5,
        session_id: Optional[int] = None,
        extra_doc_ids: Optional[list[int]] = None,
    ) -> tuple[str, list[str]]:
        scope_filter = self._scope_filter(user_id, user_dept_id, search_scope, session_id)
        docs = self._similarity_search(query, k, scope_filter)
        docs = self._merge_attached_docs(query, docs, extra_doc_ids)

        text_content = "\n\n".join(doc.page_content for doc in docs)
        sources = list({str(doc.metadata.get("doc_id", "N/A")) for doc in docs})
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
                    attached_docs.extend(self.get_doc_context_chunks(doc_id, limit=12))
                else:
                    attached_docs.extend(
                        self.vectordb.similarity_search(query, k=4, filter={"doc_id": doc_id})
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
            return [
                LCDocument(page_content=content, metadata=metadatas[index] or {})
                for index, content in enumerate(documents)
                if content
            ]
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
