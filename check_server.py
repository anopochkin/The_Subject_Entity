import requests
import json

# =========================
# КОНФИГУРАЦИЯ
# =========================
API_KEY = "your_backboard_key_here" 
BASE_URL = "https://app.backboard.io/api"
ASSISTANT_NAME = "The_Subject_Entity"

def get_headers():
    return {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def inspect_cloud():
    print(f"\n🕵️‍♂️ INSPECTING CLOUD DATABASE ({BASE_URL})...")
    
    # 1. Ищем Ассистента
    aid = None
    try:
        resp = requests.get(f"{BASE_URL}/assistants", headers=get_headers())
        data = resp.json()
        al = data.get("assistants", []) if isinstance(data, dict) else data
        
        for a in al:
            if a.get("name") == ASSISTANT_NAME:
                aid = a['assistant_id']
                print(f"✅ FOUND ENTITY: '{ASSISTANT_NAME}' (ID: {aid})")
                break
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {e}")
        return

    if not aid:
        print(f"❌ ENTITY '{ASSISTANT_NAME}' NOT FOUND IN CLOUD.")
        return

    # 2. Скачиваем Память
    print("\n📥 DOWNLOADING MEMORIES FROM VECTOR DB...")
    resp = requests.get(f"{BASE_URL}/assistants/{aid}/memories", headers=get_headers())
    memories = resp.json()
    mem_list = memories.get("memories", []) if isinstance(memories, dict) else memories

    if not mem_list:
        print("   [EMPTY] No memories found.")
    else:
        for m in mem_list:
            content = m.get("content") or m.get("memory") or "???"
            # Красивый вывод
            print("-" * 40)
            print(f"📄 MEMORY ID: {m.get('id')}")
            print(f"📝 CONTENT:\n{content}")
            print("-" * 40)

    print("\n✅ VERIFICATION COMPLETE.")

if __name__ == "__main__":
    inspect_cloud()