from sqlalchemy.orm import Session

from config import CHROMA_PERSIST_DIR
from repositories.document_repository import DocumentRepository


class VectorAdminService:
    def status(self) -> dict:
        import chromadb

        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        total = 0
        for collection_ref in client.list_collections():
            collection = (
                client.get_collection(collection_ref)
                if isinstance(collection_ref, str)
                else collection_ref
            )
            total += collection.count()
        return {"total_vectors": total, "persist_dir": CHROMA_PERSIST_DIR}

    def reindex(self, db: Session) -> dict:
        from rag_engine.chroma_manager import ChromaDBManager

        manager = ChromaDBManager(db=db)
        manager.admin_clear_db()

        documents = DocumentRepository(db)
        docs = documents.list_unindexed()
        total_chunks = 0
        reindexed_docs = 0
        for doc in docs:
            file_path = (doc.file_path or "").lower()
            if file_path.endswith(".pdf"):
                chunks = manager.process_and_store_pdf(
                    doc.file_path,
                    doc.id,
                    doc.owner_id or 0,
                    doc.department_id or -1,
                    doc.scope.value if hasattr(doc.scope, "value") else doc.scope,
                    "",
                )
            elif file_path.endswith(".docx"):
                chunks = manager.process_and_store_word(
                    doc.file_path,
                    doc.id,
                    doc.owner_id or 0,
                    doc.department_id or -1,
                    doc.scope.value if hasattr(doc.scope, "value") else doc.scope,
                    "",
                )
            else:
                continue
            doc.is_indexed = True
            reindexed_docs += 1
            total_chunks += chunks

        documents.commit()
        return {"status": "success", "reindexed_docs": reindexed_docs, "total_chunks": total_chunks}
