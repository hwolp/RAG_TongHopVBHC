import os
import sys
import requests
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from database.db_config import SessionLocal
from database import models

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")

def check_ollama_server():
    print("=" * 60)
    print("CHECKING OLLAMA SERVER STATUS")
    print(f"Ollama URL: {OLLAMA_URL}")
    print(f"Target Model: {OLLAMA_MODEL}")
    print("=" * 60)
    
    # 1. Ping Ollama base URL
    try:
        r = requests.get(OLLAMA_URL, timeout=5)
        print(f"Ping {OLLAMA_URL}: Status {r.status_code} - {r.text.strip()}")
    except Exception as e:
        print(f"❌ Cannot connect to Ollama server at {OLLAMA_URL}. Error: {e}")
        return False
        
    # 2. Check tags (downloaded models)
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            data = r.json()
            models_list = [m["name"] for m in data.get("models", [])]
            print(f"✅ Downloaded Models: {models_list}")
            if OLLAMA_MODEL not in models_list:
                print(f"⚠️ Target model '{OLLAMA_MODEL}' is NOT in downloaded models list!")
        else:
            print(f"❌ Failed to get models list. Status: {r.status_code}")
    except Exception as e:
        print(f"❌ Error fetching models list: {e}")
        
    # 3. Check loaded models (/api/ps)
    try:
        r = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
        if r.status_code == 200:
            data = r.json()
            loaded = data.get("models", [])
            if loaded:
                print("🧠 Currently Loaded Models in Memory:")
                for m in loaded:
                    print(f"  - {m.get('name')}: Size={m.get('size')}, Size VRAM={m.get('size_vram')}")
            else:
                print("💤 No models currently loaded in memory.")
        else:
            print(f"❌ Failed to get loaded models. Status: {r.status_code}")
    except Exception as e:
        print(f"❌ Error checking loaded models: {e}")
        
    return True

def check_session_jobs():
    print("\n" + "=" * 60)
    print("CHECKING BACKGROUND JOBS FOR SESSION 56 AND RECENT")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Check session 56 jobs
        jobs = db.query(models.BackgroundJob).filter_by(session_id=56).order_by(models.BackgroundJob.created_at.desc()).all()
        print(f"Total jobs for Session 56: {len(jobs)}")
        for job in jobs:
            print(f"  Job ID: {job.id} | Type: {job.type} | Status: {job.status} | Progress: {job.progress}%")
            print(f"  Created At: {job.created_at} | Updated At: {job.updated_at}")
            if job.error:
                print(f"  Error: {job.error}")
            if job.payload:
                try:
                    payload_dict = json.loads(job.payload)
                    print(f"  Payload: {json.dumps(payload_dict, ensure_ascii=False)[:300]}...")
                except:
                    print(f"  Payload (raw): {job.payload[:300]}...")
            print("-" * 40)
            
        # Check active jobs (status=queued/running)
        active_jobs = db.query(models.BackgroundJob).filter(models.BackgroundJob.status.in_(["queued", "running"])).order_by(models.BackgroundJob.created_at.desc()).all()
        print(f"\nAll Currently Active/Pending Jobs in System: {len(active_jobs)}")
        for job in active_jobs:
            print(f"  Job ID: {job.id} | Session: {job.session_id} | Type: {job.type} | Status: {job.status} | Created At: {job.created_at}")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_ollama_server()
    check_session_jobs()
