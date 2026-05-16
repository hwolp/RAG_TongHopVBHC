import os
import sys

import pytest
from langchain_core.documents import Document as LCDocument

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import models
from rag_engine.models import DocumentIndexMetadata
from services.jobs.handlers import JobDispatcher
from services.rag.document_processor import DocumentProcessor


def test_document_processor_tags_normal_chunks_with_index_metadata():
    processor = DocumentProcessor()
    metadata = DocumentIndexMetadata(
        doc_id=42,
        owner_id=7,
        department_id=3,
        scope="personal",
        tags="policy",
        session_id=9,
    )
    pages = [LCDocument(page_content="Short plain text document.", metadata={"source": "sample.txt"})]

    chunks = processor._chunk_and_tag(pages, metadata, force_admin_chunking=False)

    assert chunks
    assert chunks[0].metadata["doc_id"] == 42
    assert chunks[0].metadata["owner_id"] == 7
    assert chunks[0].metadata["department_id"] == 3
    assert chunks[0].metadata["scope"] == "personal"
    assert chunks[0].metadata["tags"] == "policy"
    assert chunks[0].metadata["session_id"] == 9
    assert chunks[0].metadata["chunk_strategy"] == "normal"
    assert chunks[0].metadata["source"] == "sample.txt"


def test_job_dispatcher_rejects_unknown_job_type():
    class DummyDb:
        pass

    job = models.BackgroundJob(id=1, type="unknown_job")

    with pytest.raises(ValueError, match="Unsupported job type"):
        JobDispatcher(DummyDb()).dispatch(job)
