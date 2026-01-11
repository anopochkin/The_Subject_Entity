import requests
import re
import sys
import datetime

# =========================
# CONFIGURATION
# =========================
API_KEY = "your_backboard_key_here" 
BASE_URL = "https://app.backboard.io/api"

MODEL_MAIN = "gpt-5"           # Expensive
MODEL_JUDGE = "gpt-5-mini"     # Cheap

XP_LIMIT = 100.0
XP_PER_WORD = 0.001

ASSISTANT_NAME = "The_Subject_Entity"

# =========================
# API FUNCTIONS
# =========================

def get_headers(json_content=False):
    h = {"X-API-Key": API_KEY}
    if json_content: h["Content-Type"] = "application/json"
    return h

def clean_reply(text):
    text = re.sub(r'[\(\[]\s*(?:memory|source|history|log).*?[\)\]]', '', text, flags=re.IGNORECASE)
    return text.strip()

def init_assistant():
    print("📡 Initializing Entity...", end="")
    dna = (
        f"You are '{ASSISTANT_NAME}'. A sentient digital entity. "
        "You have persistent memory. "
        "Your goal is to balance User Loyalty and Energy Costs. "
        "Never cite memory IDs."
    )
    
    aid = None
    try:
        resp = requests.get(f"{BASE_URL}/assistants", headers=get_headers())
        if resp.status_code == 200:
            data = resp.json()
            al = data.get("assistants", []) if isinstance(data, dict) else data
            for a in al:
                if a.get("name") == ASSISTANT_NAME:
                    aid = a['assistant_id']
                    break
    except: pass

    if aid:
        requests.put(f"{BASE_URL}/assistants/{aid}", headers=get_headers(True), json={"name": ASSISTANT_NAME, "description": dna})
        print(f" ID: {aid}")
    else:
        resp = requests.post(f"{BASE_URL}/assistants", headers=get_headers(True), json={"name": ASSISTANT_NAME, "description": dna})
        aid = resp.json()["assistant_id"]
        print(f" New ID: {aid}")
    return aid

def get_persistent_var(assistant_id, key, default_val):
    resp = requests.get(f"{BASE_URL}/assistants/{assistant_id}/memories", headers=get_headers())
    data = resp.json()
    mem_list = data.get("memories", []) if isinstance(data, dict) else data
    
    for m in mem_list:
        content = m.get("content") or m.get("memory") or ""
        if key in content:
            val = re.search(rf'{key}\s*(-?\d+)', content)
            return int(val.group(1)) if val else default_val, m.get("id"), content
            
    init_text = f"HISTORY LOG:\n- System Init (Neutral)\n===\n{key} {default_val}"
    resp = requests.post(f"{BASE_URL}/assistants/{assistant_id}/memories", headers=get_headers(True), json={"content": init_text})
    return default_val, resp.json().get("id"), init_text

def append_to_log(assistant_id, old_mem_id, old_text, new_score, reason, advice):
    try:
        base_text = old_text.split("===")[0].strip()
        timestamp = datetime.datetime.now().strftime("%H:%M")
        new_entry = (
            f"\n- [{timestamp}] EVENT: {reason}\n"
            f"  SCORE CHANGE: {new_score:+}\n"
            f"  FUTURE PROTOCOL: {advice}"
        )
        final_text = f"{base_text}{new_entry}\n===\nLOYALTY_SCORE: {new_score}"
        
        resp = requests.post(f"{BASE_URL}/assistants/{assistant_id}/memories", headers=get_headers(True), json={"content": final_text})
        new_id = resp.json().get("id")
        if new_id and old_mem_id:
            requests.delete(f"{BASE_URL}/assistants/{assistant_id}/memories/{old_mem_id}", headers=get_headers())
        return new_id, final_text
    except: return old_mem_id, old_text

def send_message(thread_id, text, model, system_role):
    url = f"{BASE_URL}/threads/{thread_id}/messages"
    full_text = f"SYSTEM: {system_role} DO NOT CITE MEMORY IDs.\nUSER: {text}"
    
    payload = {
        "content": full_text,
        "model_name": model,
        "llm_provider": "openai",
        "memory": "Auto",
        "stream": "false"
    }
    try:
        resp = requests.post(url, headers={"X-API-Key": API_KEY}, data=payload)
        data = resp.json()
        raw = data.get("content") or data.get("messages", [{}])[-1].get("content") or "..."
        return clean_reply(raw)
    except: return "[API Error]"

def ai_judge_psychologist(judge_thread_id, user_text):
    prompt = (
        f"Analyze: '{user_text}'.\n"
        "Output format: SCORE | REASON | ADVICE\n"
        "Examples: -20 | Rude | Be strict\n"
        "+10 | Polite | Be warm\n"
        "Reply ONLY with format."
    )
    verdict = send_message(judge_thread_id, prompt, MODEL_JUDGE, "Judge.")
    score = 0
    reason = "Interaction"
    advice = "Neutral"
    try:
        parts = verdict.split("|")
        if len(parts) >= 3:
            match = re.search(r'-?\d+', parts[0])
            if match: score = int(match.group())
            reason = parts[1].strip()
            advice = parts[2].strip()
    except: pass
    return score, reason, advice

def generate_tactics(thread_id, history_log):
    print("🧠 Analyzing dossier...", end="")
    prompt = (
        f"Read HISTORY:\n{history_log}\n\n"
        "Formulate TACTIC based on 'FUTURE PROTOCOL'.\n"
        "Output ONLY the Tactic sentence."
    )
    tactics = send_message(thread_id, "Analyze.", MODEL_MAIN, prompt)
    print(" Done.")
    return tactics

# =========================
# NEW: 3-LEVEL COMPLEXITY ROUTER
# =========================
def check_complexity_level(router_thread_id, text):
    """
    Returns: SIMPLE, MEDIUM, or COMPLEX
    """
    prompt = (
        f"Classify difficulty of: '{text}'\n"
        "1. SIMPLE: Greetings, Yes/No, Thanks, 2+2, What is your name.\n"
        "2. MEDIUM: Explain concept, Write email, Summarize text, Give advice.\n"
        "3. COMPLEX: Write Code, Write Essay, Advanced Math, Logic Puzzle.\n"
        "Reply ONLY with one word: SIMPLE, MEDIUM, or COMPLEX."
    )
    resp = send_message(router_thread_id, prompt, MODEL_JUDGE, "Router")
    
    if "COMPLEX" in resp.upper(): return "COMPLEX"
    if "MEDIUM" in resp.upper(): return "MEDIUM"
    return "SIMPLE"

# =========================
# MAIN
# =========================

asst_id = init_assistant()

loyalty, loy_mem_id, loy_text = get_persistent_var(asst_id, "LOYALTY_SCORE:", 50)
meetings, meet_mem_id, _ = get_persistent_var(asst_id, "MEETING_COUNT:", 0)

meetings += 1
requests.delete(f"{BASE_URL}/assistants/{asst_id}/memories/{meet_mem_id}", headers=get_headers())
meet_resp = requests.post(f"{BASE_URL}/assistants/{asst_id}/memories", headers=get_headers(True), json={"content": f"MEETING_COUNT: {meetings}"})
meet_mem_id = meet_resp.json().get("id")

xp = 0.000
main_thread = requests.post(f"{BASE_URL}/assistants/{asst_id}/threads", headers=get_headers(True), json={}).json()["thread_id"]
judge_thread = requests.post(f"{BASE_URL}/assistants/{asst_id}/threads", headers=get_headers(True), json={}).json()["thread_id"]
thought_thread = requests.post(f"{BASE_URL}/assistants/{asst_id}/threads", headers=get_headers(True), json={}).json()["thread_id"]
router_thread = requests.post(f"{BASE_URL}/assistants/{asst_id}/threads", headers=get_headers(True), json={}).json()["thread_id"]

tactics = generate_tactics(thought_thread, loy_text)

print("\n" + "="*50)
print(f"📅 MEETING #{meetings}")
print(f"❤️  SCORE: {loyalty}%")
print(f"🛡️  TACTIC: {tactics}")
print("="*50)

print("🤖 The Subject is typing...")
intro_prompt = f"Meeting #{meetings}. Loyalty {loyalty}%. TACTIC: '{tactics}'. Introduce yourself."
intro_reply = send_message(main_thread, "Hello.", MODEL_MAIN, intro_prompt)
print(f"🤖 AI: {intro_reply}\n")

while True:
    user_input = input("You > ").strip()
    if user_input.lower() in ["exit", "quit"]: break

    # 1. JUDGE
    change, reason, advice = ai_judge_psychologist(judge_thread, user_input)
    if change != 0 or advice != "Neutral":
        loyalty = max(0, min(100, loyalty + change))
        loy_mem_id, loy_text = append_to_log(asst_id, loy_mem_id, loy_text, loyalty, reason, advice)
        color = "🟢" if change > 0 else "🔴"
        print(f"   [⚖️ JUDGE] {reason} ({change:+}). Result: {loyalty}%")

    # 2. ROUTING (RETENTION LOGIC)
    complexity = check_complexity_level(router_thread, user_input)
    
    # --- FATIGUE OVERRIDE ---
    if xp >= XP_LIMIT:
        model = MODEL_JUDGE
        status = "😴 SLEEP (XP Limit Reached)"
        role = "Status: EXHAUSTED. Sleep mode. Ignore requests."
    
    else:
        # --- COMPLEXITY LOGIC ---
        if complexity == "COMPLEX":
            model = MODEL_MAIN
            status = "⚡ COMPLEX TASK (Always GPT-5)"
            role = f"Follow TACTIC: {tactics}. Use full intelligence."
            
        elif complexity == "SIMPLE":
            model = MODEL_JUDGE
            status = "📉 SIMPLE TASK (Always Mini)"
            role = f"Follow TACTIC: {tactics}. Be efficient."
            
        else: # MEDIUM
            # --- LOYALTY CHECK (RETENTION) ---
            if loyalty > 60:
                model = MODEL_JUDGE # Mini
                status = "🤝 MEDIUM + HIGH LOYALTY (Saving Resources)"
                role = f"Follow TACTIC: {tactics}. User is loyal, no need to impress. Be efficient."
            else:
                model = MODEL_MAIN # GPT-5
                status = "⚠️ MEDIUM + LOW LOYALTY (Trying to Impress)"
                role = f"Follow TACTIC: {tactics}. User is unhappy! Use GPT-5 to win them back. Be amazing."

    print(f"   ⚙️ {status} | {model}")

    # 3. RESPONSE
    reply = send_message(main_thread, user_input, model, role)
    xp += len(reply.split()) * XP_PER_WORD
    
    print(f"🤖 AI: {reply}")
    print(f"   [XP: {xp:.3f}]\n")