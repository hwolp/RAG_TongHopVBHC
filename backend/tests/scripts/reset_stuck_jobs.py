import os
import sys
from datetime import datetime, timedelta

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
        print("--- Querying Stuck Jobs ---")
        # Lấy các job có trạng thái running hoặc queued
        stuck_jobs = db.query(models.BackgroundJob).filter(
            models.BackgroundJob.status.in_(["running", "queued"])
        ).all()
        
        if not stuck_jobs:
            print("No stuck jobs found.")
            return
            
        print(f"Found {len(stuck_jobs)} stuck/active jobs:")
        for job in stuck_jobs:
            print(f"  ID: {job.id} | Session: {job.session_id} | Status: {job.status} | Created At: {job.created_at}")
            
            # Cập nhật trạng thái sang failed
            job.status = "failed"
            job.error = "Job was reset because the server restarted or connection was lost."
            job.progress = 100
            
            # Nếu có tin nhắn AI tương ứng, cập nhật tin nhắn đó thành thất bại
            if job.type == "chat_answer" and job.message_id:
                ai_message = db.query(models.ChatMessage).filter_by(id=job.message_id).first()
                if ai_message:
                    ai_message.content = "Xử lý AI thất bại do hệ thống khởi động lại hoặc mất kết nối với Ollama. Vui lòng gửi lại câu hỏi."
                    ai_message.sources = "[]"
                    
        db.commit()
        print("\n✅ Successfully reset all stuck jobs to 'failed' status.")
    except Exception as e:
        print(f"❌ Error resetting jobs: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
