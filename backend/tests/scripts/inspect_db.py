import os
import sys

# Ensure backend is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from rag_engine.chroma_manager import ChromaDBManager

def inspect_session(session_id):
    print("=" * 80)
    print(f"INSPECTING SESSION: {session_id}")
    print("=" * 80)
    
    manager = ChromaDBManager()
    
    # 1. Get scope filter
    scope_filter = manager._scope_filter(user_id=1, user_dept_id=1, search_scope="personal", session_id=session_id)
    print(f"Scope filter: {scope_filter}")
    
    # 2. Get chunks matching filter
    try:
        collection = manager.vectordb._collection
        results = collection.get(
            where=scope_filter,
            include=["metadatas", "documents"],
            limit=500,
        )
        metadatas = results.get("metadatas", []) or []
        documents = results.get("documents", []) or []
        print(f"Total chunks found: {len(metadatas)}")
        
        doc_ids = set()
        for idx, meta in enumerate(metadatas):
            if meta:
                doc_ids.add(meta.get("doc_id"))
                if idx < 5:
                    print(f"  Chunk {idx}: doc_id={meta.get('doc_id')}, parent_id={meta.get('parent_id')}, article_number={meta.get('article_number')}, title={meta.get('title') or meta.get('article_title')}")
                    print(f"    Content preview: {documents[idx][:100]}...")
        
        print(f"Distinct doc_ids: {list(doc_ids)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_session(59)
    inspect_session(60)
