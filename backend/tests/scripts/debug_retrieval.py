r"""
Debug script: Xem chi tiet chunks duoc retrieve cho 1 query cu the.
Chay: .venv\Scripts\python.exe scripts/debug_retrieval.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from rag_engine.chroma_manager import ChromaDBManager

QUERY = "Điều 35 có nội dung gì"
SESSION_ID = 60
# Giả sử user_id=1, dept_id=1, scope personal — điều chỉnh nếu cần
USER_ID = 1
DEPT_ID = 1
SEARCH_SCOPE = "personal"


def main():
    print("=" * 80)
    print(f"DEBUG RETRIEVAL")
    print(f"  Query:      {QUERY}")
    print(f"  Session ID: {SESSION_ID}")
    print(f"  Scope:      {SEARCH_SCOPE}")
    print("=" * 80)

    manager = ChromaDBManager()

    # --- Bước 1: Xem scope filter ---
    scope_filter = manager._scope_filter(USER_ID, DEPT_ID, SEARCH_SCOPE, SESSION_ID)
    print(f"\n📋 Scope filter: {scope_filter}")

    # --- Bước 2: Kiểm tra có bao nhiêu chunks trong session này ---
    try:
        collection = manager.vectordb._collection
        results = collection.get(
            where=scope_filter,
            include=["metadatas"],
            limit=500,
        )
        total_chunks = len(results.get("documents", []) or results.get("ids", []))
        print(f"📦 Tổng chunks trong session {SESSION_ID}: {total_chunks}")

        # Liệt kê doc_ids
        doc_ids = set()
        for meta in results.get("metadatas", []) or []:
            if meta and meta.get("doc_id"):
                doc_ids.add(meta["doc_id"])
        print(f"📄 Doc IDs trong session: {sorted(doc_ids)}")
    except Exception as e:
        print(f"⚠️ Lỗi khi đếm chunks: {e}")

    # --- Bước 3: Chạy từng pipeline riêng ---
    detection_queries = manager._query_variants(None, QUERY)
    print(f"\n🔍 Detection queries: {detection_queries}")

    # Article direct search
    article_docs = manager._article_direct_search(QUERY, scope_filter)
    print(f"\n{'='*60}")
    print(f"🎯 ARTICLE DIRECT SEARCH: {len(article_docs)} chunks")
    for i, doc in enumerate(article_docs):
        meta = doc.metadata or {}
        print(f"  [{i}] Điều {meta.get('article_number', '?')} | "
              f"chunk_idx={meta.get('chunk_index')} | "
              f"parent_idx={meta.get('parent_index')} | "
              f"child_idx={meta.get('child_index')}")
        print(f"      Content: {doc.page_content[:120]}...")

    # Keyword routed search
    keyword_targets = manager._keyword_targets(detection_queries)
    keyword_docs = manager._keyword_routed_search(detection_queries, scope_filter)
    print(f"\n{'='*60}")
    print(f"🔑 KEYWORD ROUTED SEARCH: {len(keyword_docs)} chunks")
    print(f"   Keyword targets: {keyword_targets}")
    for i, doc in enumerate(keyword_docs):
        meta = doc.metadata or {}
        print(f"  [{i}] Điều {meta.get('article_number', '?')} | "
              f"title={meta.get('article_title', '')[:50]} | "
              f"chunk_idx={meta.get('chunk_index')}")
        print(f"      Content: {doc.page_content[:120]}...")

    # Lexical candidate search
    lexical_docs = manager._lexical_candidate_search(detection_queries, scope_filter, keyword_targets)
    print(f"\n{'='*60}")
    print(f"📝 LEXICAL SEARCH: {len(lexical_docs)} chunks")
    for i, doc in enumerate(lexical_docs[:8]):
        meta = doc.metadata or {}
        print(f"  [{i}] Điều {meta.get('article_number', '?')} | "
              f"title={meta.get('article_title', '')[:50]} | "
              f"chunk_idx={meta.get('chunk_index')}")
        print(f"      Content: {doc.page_content[:100]}...")
    if len(lexical_docs) > 8:
        print(f"  ... và {len(lexical_docs) - 8} chunks nữa")

    # Vector similarity search
    from rag_engine.chroma_manager import _VECTOR_CANDIDATE_K
    vector_docs = manager._similarity_search(QUERY, _VECTOR_CANDIDATE_K, scope_filter)
    print(f"\n{'='*60}")
    print(f"🧮 VECTOR SIMILARITY SEARCH: {len(vector_docs)} chunks (top {_VECTOR_CANDIDATE_K})")
    for i, doc in enumerate(vector_docs):
        meta = doc.metadata or {}
        print(f"  [{i}] Điều {meta.get('article_number', '?')} | "
              f"title={meta.get('article_title', '')[:50]} | "
              f"section={meta.get('section_path', '')}")
        print(f"      Content: {doc.page_content[:120]}...")

    # --- Bước 4: Chạy full pipeline và xem kết quả cuối cùng ---
    print(f"\n{'='*60}")
    print(f"🏆 FINAL CONTEXT (gửi lên LLM)")
    print(f"{'='*60}")

    final_context, sources = manager.search_context_with_filter(
        query=QUERY,
        user_id=USER_ID,
        user_dept_id=DEPT_ID,
        search_scope=SEARCH_SCOPE,
        session_id=SESSION_ID,
    )

    print(f"\n📌 Sources (doc_ids): {sources}")
    print(f"📏 Tổng độ dài context: {len(final_context)} ký tự")
    print(f"\n--- NỘI DUNG CONTEXT GỬI LÊN LLM ---")
    print(final_context)
    print(f"--- HẾT CONTEXT ---")


if __name__ == "__main__":
    main()
