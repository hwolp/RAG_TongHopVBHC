import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from database.db_config import SessionLocal
from database import models

def main():
    db = SessionLocal()
    try:
        print("--- Querying Chat Session 56 ---")
        session = db.query(models.ChatSession).filter_by(id=56).first()
        if not session:
            print("ChatSession with ID 56 does not exist in the database.")
            # Let's list the most recent sessions to see what exists
            print("\nRecent chat sessions:")
            sessions = db.query(models.ChatSession).order_by(models.ChatSession.id.desc()).limit(10).all()
            for s in sessions:
                print(f"  ID: {s.id}, Title: {s.title}, User ID: {s.user_id}, Created: {s.created_at}")
        else:
            print(f"ID: {session.id}")
            print(f"Title: {session.title}")
            print(f"User ID: {session.user_id}")
            print(f"Created At: {session.created_at}")
            
            print("\n--- Messages in Session 56 ---")
            messages = db.query(models.ChatMessage).filter_by(session_id=56).order_by(models.ChatMessage.created_at).all()
            print(f"Total messages: {len(messages)}")
            for msg in messages:
                print(f"  [{msg.sender.upper()}] ID: {msg.id}, Created: {msg.created_at}")
                print(f"  Content: {msg.content[:200]}...")
                print(f"  Sources: {msg.sources}")
                print("-" * 40)
            
        print("\n--- Background Jobs related to Session 56 ---")
        jobs = db.query(models.BackgroundJob).filter_by(session_id=56).order_by(models.BackgroundJob.created_at.desc()).limit(5).all()
        print(f"Total jobs: {len(jobs)}")
        for job in jobs:
            print(f"  Job ID: {job.id}")
            print(f"  Type: {job.type}")
            print(f"  Status: {job.status}")
            print(f"  Progress: {job.progress}")
            print(f"  Created At: {job.created_at}")
            print(f"  Updated At: {job.updated_at}")
            print(f"  Finished At: {job.finished_at}")
            print(f"  Error: {job.error}")
            print(f"  Payload: {job.payload}")
            print(f"  Result: {job.result}")
            print("-" * 40)

        print("\n--- All Active/Pending Background Jobs ---")
        active_jobs = db.query(models.BackgroundJob).filter(models.BackgroundJob.status.in_(["queued", "running"])).order_by(models.BackgroundJob.created_at.desc()).all()
        print(f"Total active/pending jobs: {len(active_jobs)}")
        for job in active_jobs:
            print(f"  Job ID: {job.id}, Session ID: {job.session_id}, Type: {job.type}, Status: {job.status}, Created At: {job.created_at}")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
