import requests

# =========================
# CONFIGURATION
# =========================
API_KEY = "your_backboard_key_here" 
BASE_URL = "https://app.backboard.io/api"
ASSISTANT_NAME = "The_Subject_Entity"

def get_headers():
    return {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def wipe_memory():
    print(f"\n🧹 STARTING MEMORY WIPE FOR '{ASSISTANT_NAME}'...")
    
    # 1. Ищем ID
    aid = None
    try:
        resp = requests.get(f"{BASE_URL}/assistants", headers=get_headers())
        data = resp.json()
        al = data.get("assistants", []) if isinstance(data, dict) else data
        for a in al:
            if a.get("name") == ASSISTANT_NAME:
                aid = a['assistant_id']
                break
    except: pass

    if not aid:
        print("❌ Entity not found. Nothing to wipe.")
        return

    # 2. Скачиваем все воспоминания
    resp = requests.get(f"{BASE_URL}/assistants/{aid}/memories", headers=get_headers())
    memories = resp.json().get("memories", [])
    
    if not memories:
        print("✅ Memory is already empty.")
        return

    print(f"⚠️ Found {len(memories)} memory fragments. Deleting...")

    # 3. Удаляем по одному
    for m in memories:
        mid = m.get("id")
        requests.delete(f"{BASE_URL}/assistants/{aid}/memories/{mid}", headers=get_headers())
        print(f"   🗑️ Deleted fragment: {mid}")

    print("\n✨ BRAINWASH COMPLETE. The Entity is tabula rasa.")

if __name__ == "__main__":
    wipe_memory()