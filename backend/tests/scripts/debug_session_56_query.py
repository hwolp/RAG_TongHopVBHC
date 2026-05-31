import os
import sys
import time
import requests

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from database.db_config import SessionLocal
from database import models
from rag_engine.chroma_manager import ChromaDBManager
from rag_engine.ollama_ai import OllamaAI

QUESTION = "Để có nguồn kinh phí thực hiện cải cách tiền lương năm 2026, các tỉnh/thành phố trực thuộc trung ương được sử dụng những nguồn nào? (Liệt kê đầy đủ các nguồn)."
SESSION_ID = 56
USER_ID = 1  # Giả sử user_id=1, kiểm tra trong DB trước
DEPT_ID = 1

def main():
    db = SessionLocal()
    try:
        # Lấy thông tin user thực tế tạo ra job của session 56
        job = db.query(models.BackgroundJob).filter_by(session_id=SESSION_ID).first()
        if job and job.created_by:
            user_id = job.created_by
            user = db.query(models.User).filter_by(id=user_id).first()
            dept_id = user.department_id if user and user.department_id is not None else -1
            print(f"Using actual user_id={user_id}, dept_id={dept_id} from job history")
        else:
            user_id = 1
            dept_id = 1
            print("No job history found, using default user_id=1, dept_id=1")
    finally:
        db.close()

    print("\n--- Running Context Retrieval ---")
    manager = ChromaDBManager()
    
    # 1. Retrieve context
    t0 = time.time()
    context, sources = manager.search_context_with_filter(
        query=QUESTION,
        user_id=user_id,
        user_dept_id=dept_id,
        search_scope="personal",
        session_id=SESSION_ID,
    )
    t1 = time.time()
    
    print(f"Retrieval took: {t1 - t0:.3f} seconds")
    print(f"Sources found: {sources}")
    print(f"Context length: {len(context)} characters")
    
    # 2. Print preview of context
    print("\n--- Context Preview (first 1000 chars) ---")
    print(context[:1000])
    print("...")
    print("--- End Context Preview ---")

    # 3. Call Ollama directly to see what happens
    print("\n--- Testing Ollama direct invoke ---")
    ai = OllamaAI()
    formatted = ai.prompt_builder.build_answer_prompt(QUESTION, context, "")
    print(f"Formatted prompt length: {len(formatted)} chars")
    
    print("Invoking Ollama LLM (timeout = 60s)...")
    try:
        t0 = time.time()
        # Set a shorter timeout for this debug run so we don't hang forever
        ai.llm.timeout = 60
        answer = ai.llm.invoke(formatted)
        t1 = time.time()
        print(f"✅ Ollama call succeeded in {t1 - t0:.2f} seconds!")
        print("\n--- Ollama Answer ---")
        print(answer)
        print("--- End Answer ---")
    except Exception as e:
        t1 = time.time()
        print(f"❌ Ollama call failed after {t1 - t0:.2f} seconds.")
        print(f"Error type: {type(e)}")
        print(f"Error detail: {e}")

if __name__ == "__main__":
    main()
