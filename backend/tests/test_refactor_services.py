import os
import sys
from types import SimpleNamespace

import pytest
from langchain_core.documents import Document as LCDocument

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import models
from rag_engine.chroma_manager import ChromaDBManager, _is_structure_query, is_structure_context
from rag_engine.models import DocumentIndexMetadata
from rag_engine.ollama_ai import OllamaAI
from services.chat import context_service
from services.chat.context_service import build_recent_chat_history
from services.jobs.handlers import JobDispatcher
from services.rag.document_processor import DocumentProcessor, _postprocess_ocr_text
from services.rag.prompt_builder import PromptBuilder


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


def test_structure_context_answers_without_document_id_heading(monkeypatch):
    manager = ChromaDBManager.__new__(ChromaDBManager)

    monkeypatch.setattr(
        manager,
        "_metadata_for_structure",
        lambda where_filter: [
            {
                "doc_id": 97,
                "chapter_number": "I",
                "chapter_title": "QUY ĐỊNH CHUNG",
                "article_number": "1",
                "article_title": "Phạm vi điều chỉnh",
            }
        ],
    )

    context, sources = manager._structure_context({"owner_id": 1})

    assert is_structure_context(context)
    assert "Tài liệu #97" not in context
    assert context.startswith("Văn bản gồm các phần sau:")
    assert "- Tổng số điều: 1" in context
    assert "- Tổng số chương: 1" in context
    assert "- Chương I: QUY ĐỊNH CHUNG" in context
    assert "  - Điều 1: Phạm vi điều chỉnh" in context
    assert sources == ["97"]


def test_structure_query_detects_article_count_questions():
    assert _is_structure_query("Văn bản gồm bao nhiêu điều")
    assert _is_structure_query("Văn bản này có mấy điều?")
    assert _is_structure_query("Liệt kê các điều trong văn bản")


def test_document_processor_merges_ocr_pages_with_worker_results(monkeypatch):
    processor = DocumentProcessor()
    pages = [LCDocument(page_content="", metadata={}) for _ in range(3)]

    def fake_ocr_page(file_path: str, page_index: int) -> str:
        return f"OCR page {page_index}"

    monkeypatch.setattr(processor, "_ocr_pdf_page_by_index", fake_ocr_page)

    enhanced_pages = processor._enhance_pdf_pages_with_ocr("unused.pdf", pages)

    assert [page.page_content for page in enhanced_pages] == [
        "OCR page 0",
        "OCR page 1",
        "OCR page 2",
    ]


def test_ocr_postprocess_fixes_common_vietnamese_structure_errors():
    text = _postprocess_ocr_text(
        "Chương IV\n"
        "LỄ TANG ĐÓI VỚI QUẦN NHÂN CÓ CẤP BẬC TỪ ĐẠI TÁ TRỞ XUỐNG\n"
        "Điều 17. Phân cấp tỗ chức Lễ tang\n"
        "Điều 25. Chuẩn bị tin buồn, lời điền, đưa tin, đăng tin buồn\n"
        "Chương VI\n"
        "TỎ CHỨC THỰC HIỆN\n"
        "Điều 35. Kinh phí, xăng dầu bảo đám\n"
        "Chương VII\n"
        "ĐIỀU KHOẢN THỊ HÀNH5\n"
    )

    assert "ĐỐI VỚI QUÂN NHÂN" in text
    assert "Phân cấp tổ chức Lễ tang" in text
    assert "lời điếu" in text
    assert "TỔ CHỨC THỰC HIỆN" in text
    assert "bảo đảm" in text
    assert "ĐIỀU KHOẢN THI HÀNH" in text


def test_structure_context_cleans_titles_and_skips_backward_article(monkeypatch):
    manager = ChromaDBManager.__new__(ChromaDBManager)

    monkeypatch.setattr(
        manager,
        "_metadata_for_structure",
        lambda where_filter: [
            {
                "doc_id": 97,
                "chapter_number": "IV",
                "chapter_title": "LỄ TANG ĐÓI VỚI QUẦN NHÂN CÓ CẤP BẬC TỪ ĐẠI TÁ TRỞ XUỐNG",
                "article_number": "25",
                "article_title": "Chuẩn bị tin buồn, lời điền, đưa tin, đăng tin buồn",
            },
            {
                "doc_id": 97,
                "chapter_number": "VI",
                "chapter_title": "TỎ CHỨC THỰC HIỆN",
                "article_number": "35",
                "article_title": "Kinh phí, xăng dầu bảo đám",
            },
            {
                "doc_id": 97,
                "chapter_number": "VII",
                "chapter_title": "ĐIỀU KHOẢN THỊ HÀNH5",
                "article_number": "19",
                "article_title": "Hiệu lực thi hành",
            },
            {
                "doc_id": 97,
                "chapter_number": "VII",
                "chapter_title": "ĐIỀU KHOẢN THỊ HÀNH5",
                "article_number": "36",
                "article_title": "Hiệu lực thi hành",
            },
        ],
    )

    context, _ = manager._structure_context({"owner_id": 1})

    assert "ĐỐI VỚI QUÂN NHÂN" in context
    assert "lời điếu" in context
    assert "TỔ CHỨC THỰC HIỆN" in context
    assert "bảo đảm" in context
    assert "ĐIỀU KHOẢN THI HÀNH" in context
    assert "Điều 19" not in context
    assert "Điều 36: Hiệu lực thi hành" in context


def test_document_processor_indexes_roman_numbered_list_structure():
    processor = DocumentProcessor()
    metadata = DocumentIndexMetadata(
        doc_id=88,
        owner_id=1,
        department_id=1,
        scope="personal",
        tags="",
        session_id=1,
    )
    pages = [
        LCDocument(
            page_content=(
                "triển khai thi hành Luật với các nội dung sau.\n\n"
                "I. MỤC ĐÍCH, YÊU CẦU\n\n"
                "1. Mục đích\n\n"
                "a) Xác định rõ trách nhiệm của cơ quan chủ trì và cơ quan phối hợp.\n\n"
                "2. Yêu cầu\n\n"
                "a) Bảo đảm thực hiện đúng tiến độ.\n"
            ),
            metadata={"source": "sample.pdf"},
        )
    ]

    chunks = processor._chunk_and_tag(pages, metadata, force_admin_chunking=False)

    list_chunk = next(chunk for chunk in chunks if chunk.metadata["parent_type"] == "list_item")

    assert list_chunk.metadata["chunk_strategy"] == "administrative"
    assert list_chunk.metadata["list_section_number"] == "I"
    assert list_chunk.metadata["list_section_title"] == "MỤC ĐÍCH, YÊU CẦU"
    assert list_chunk.metadata["list_item_number"] == "1"
    assert list_chunk.metadata["list_item_title"] == "Mục đích"
    assert list_chunk.metadata["section_path"] == "Mục I > 1."


def test_structure_context_renders_roman_numbered_list(monkeypatch):
    manager = ChromaDBManager.__new__(ChromaDBManager)

    monkeypatch.setattr(
        manager,
        "_metadata_for_structure",
        lambda where_filter: [
            {
                "doc_id": 88,
                "list_section_number": "I",
                "list_section_title": "MỤC ĐÍCH, YÊU CẦU",
                "list_item_number": "1",
                "list_item_title": "Mục đích",
            },
            {
                "doc_id": 88,
                "list_section_number": "I",
                "list_section_title": "MỤC ĐÍCH, YÊU CẦU",
                "list_item_number": "2",
                "list_item_title": "Yêu cầu",
            },
        ],
    )

    context, sources = manager._structure_context({"owner_id": 1})

    assert "- I. MỤC ĐÍCH, YÊU CẦU" in context
    assert "  - 1. Mục đích" in context
    assert "  - 2. Yêu cầu" in context
    assert sources == ["88"]


def test_recent_chat_history_keeps_latest_valid_turns(monkeypatch):
    messages = [
        SimpleNamespace(id=8, sender="ai", content="Đáp án mới nhất"),
        SimpleNamespace(id=7, sender="user", content="Câu hỏi mới nhất"),
        SimpleNamespace(id=6, sender="ai", content="Tôi không tìm thấy thông tin này trong văn bản đã nạp."),
        SimpleNamespace(id=5, sender="user", content="Câu hỏi lỗi"),
        SimpleNamespace(id=4, sender="ai", content="Đáp án cũ"),
        SimpleNamespace(id=3, sender="user", content="Câu hỏi cũ"),
        SimpleNamespace(id=2, sender="ai", content="Đáp án rất cũ"),
        SimpleNamespace(id=1, sender="user", content="Câu hỏi rất cũ"),
    ]

    class FakeChatRepository:
        def __init__(self, db):
            pass

        def list_recent_messages(self, session_id, limit, exclude_message_id=None):
            return messages[:limit]

    monkeypatch.setattr(context_service, "ChatRepository", FakeChatRepository)

    history = build_recent_chat_history(object(), 12, limit=2)

    assert "Câu hỏi lỗi" not in history
    assert history.startswith("Nguoi dung: Câu hỏi cũ")
    assert "AI: Đáp án cũ" in history
    assert "Nguoi dung: Câu hỏi mới nhất" in history
    assert history.rstrip().endswith("AI: Đáp án mới nhất")


def test_rewrite_query_falls_back_when_llm_returns_answer_like_text():
    class FakeLLM:
        def invoke(self, prompt):
            return "Câu trả lời: Văn bản này có 7 điều."

    ai = OllamaAI.__new__(OllamaAI)
    ai.llm = FakeLLM()
    ai.prompt_builder = PromptBuilder()

    question = "Văn bản gồm bao nhiêu điều?"
    history = "Nguoi dung: Nội dung chính là gì?\nAI: Văn bản quy định về lương cơ sở.\n"

    assert ai.rewrite_query(question, history) == question


def test_rerank_prioritizes_title_match_over_vector_only_chunk():
    manager = ChromaDBManager.__new__(ChromaDBManager)
    title_doc = LCDocument(
        page_content="[Điều 2] Nội dung về các nhóm đối tượng được áp dụng.",
        metadata={
            "doc_id": 1,
            "chunk_index": 5,
            "article_number": "2",
            "article_title": "Đối tượng áp dụng",
        },
    )
    vector_doc = LCDocument(
        page_content="Một đoạn khác có vài từ áp dụng nhưng không phải tiêu đề chính.",
        metadata={
            "doc_id": 1,
            "chunk_index": 9,
            "article_number": "4",
            "article_title": "Kinh phí thực hiện",
        },
    )

    ranked = manager._rank_and_pack_context(
        queries=["Đối tượng áp dụng là ai?"],
        keyword_targets=["đối tượng áp dụng"],
        extra_doc_ids=None,
        article_docs=[],
        keyword_docs=[title_doc],
        lexical_docs=[],
        attached_docs=[],
        vector_docs=[vector_doc],
    )

    assert ranked[0].metadata["article_title"] == "Đối tượng áp dụng"
    assert ranked[0].metadata["_retrieval_group"] == "keyword"
