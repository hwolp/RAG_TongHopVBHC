import os
import sys
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from database.db_config import SessionLocal
from database import models
from rag_engine.chroma_manager import ChromaDBManager

QUESTION = "Để có nguồn kinh phí thực hiện cải cách tiền lương năm 2026, các tỉnh/thành phố trực thuộc trung ương được sử dụng những nguồn nào? (Liệt kê đầy đủ các nguồn)."
SESSION_ID = 56

def main():
    db = SessionLocal()
    try:
        job = db.query(models.BackgroundJob).filter_by(session_id=SESSION_ID).first()
        if job and job.created_by:
            user_id = job.created_by
            user = db.query(models.User).filter_by(id=user_id).first()
            dept_id = user.department_id if user and user.department_id is not None else -1
        else:
            user_id = 1
            dept_id = 1
    finally:
        db.close()

    print(f"User ID: {user_id}, Dept ID: {dept_id}")
    manager = ChromaDBManager()
    
    print("Running search...")
    t0 = time.time()
    context, sources = manager.search_context_with_filter(
        query=QUESTION,
        user_id=user_id,
        user_dept_id=dept_id,
        search_scope="personal",
        session_id=SESSION_ID,
    )
    t1 = time.time()
    print(f"Done in {t1 - t0:.2f} seconds.")
    print(f"Sources: {sources}")
    print(f"Context character length: {len(context)}")
    
    # Let's count words or tokens approximately
    words = len(context.split())
    print(f"Approximate words: {words}")
    
    print("\n--- Document structure/metadata of retrieved sources ---")
    db = SessionLocal()
    try:
        for src in sources:
            doc = db.query(models.Document).filter_by(id=int(src)).first()
            if doc:
                print(f"  Doc ID {src}: name={doc.filename}, path={doc.file_path}, size={os.path.getsize(doc.file_path) if os.path.exists(doc.file_path) else 'N/A'}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
