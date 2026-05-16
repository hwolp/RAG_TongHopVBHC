from sqlalchemy.orm import Session

from config import CHROMA_PERSIST_DIR
from database import models


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

        manager = ChromaDBManager()
        manager.admin_clear_db()

        docs = db.query(models.Document).filter(models.Document.is_indexed == False).all()
        total_chunks = 0
        for doc in docs:
            if not doc.file_path.lower().endswith(".pdf"):
                continue

            chunks = manager.process_and_store_pdf(
                doc.file_path,
                doc.id,
                doc.owner_id or 0,
                doc.department_id or -1,
                doc.scope.value if hasattr(doc.scope, "value") else doc.scope,
                "",
            )
            doc.is_indexed = True
            total_chunks += chunks

        db.commit()
        return {"status": "success", "reindexed_docs": len(docs), "total_chunks": total_chunks}

