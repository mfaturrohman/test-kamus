import streamlit as st
import requests
from datetime import datetime
import uuid
import json
import os

# ========== Konstanta ==========
FILE_SESSION = "kamus_sessions.json"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
BASE_PROMPT = """
Kamu adalah Kamus Bahasa Interaktif. Tugasmu:
- Menerjemahkan kata/kalimat antar Bahasa Indonesia, Cirebon, dan Sunda
- Jika input hanya 1 kata: tampilkan artinya, sinonim, contoh kalimat, dan konteks
- Jika ada kesalahan ketik, tawarkan saran kata yang benar
"""

# ========== Streamlit Config ==========
st.set_page_config(page_title="Kamus Cirebon & Sunda", page_icon="📚")

# ========== Fungsi File ==========
def save_sessions_to_file(sessions):
    with open(FILE_SESSION, "w", encoding="utf-8") as f:
        json.dump(sessions, f, default=str, ensure_ascii=False, indent=2)

def load_sessions_from_file():
    if os.path.exists(FILE_SESSION):
        with open(FILE_SESSION, "r", encoding="utf-8") as f:
            data = json.load(f)
        for sid, session in data.items():
            if "created" in session:
                try:
                    session["created"] = datetime.fromisoformat(session["created"])
                except Exception:
                    pass
        return data
    return {}

# ========== Inisialisasi ==========
if "sessions" not in st.session_state:
    st.session_state.sessions = load_sessions_from_file()

if not st.session_state.sessions:
    sid = str(uuid.uuid4())
    st.session_state.sessions[sid] = {
        "title": "Sesi Kamus Baru",
        "created": datetime.now(),
        "messages": []
    }
    st.session_state.current_sid = sid

if "current_sid" not in st.session_state:
    st.session_state.current_sid = list(st.session_state.sessions.keys())[0]

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# ========== Sidebar ==========
st.sidebar.title("📚 Kamus Cirebon & Sunda")

st.sidebar.markdown("#### 🔑 API Key OpenRouter")
st.session_state.api_key = st.sidebar.text_input(
    "Masukkan API Key kamu:",
    value=st.session_state.api_key,
    type="password",
    placeholder="sk-or-..."
)

# Model default (tidak bisa diganti)
MODEL = "deepseek/deepseek-chat-v3-0324:free"
st.sidebar.markdown("---")

# Pilih arah terjemahan
arah_terjemahan = st.sidebar.selectbox("🔄 Arah Terjemahan", [
    "Deteksi Otomatis",
    "Indonesia ➜ Cirebon",
    "Indonesia ➜ Sunda",
    "Cirebon ➜ Indonesia",
    "Sunda ➜ Indonesia"
])

# Sistem prompt dinamis
system_prompt = BASE_PROMPT + f"\n\nArah terjemahan: {arah_terjemahan}"

# Riwayat sesi
to_delete = None
for sid, session in st.session_state.sessions.items():
    title = session["title"]
    is_current = (sid == st.session_state.current_sid)
    with st.sidebar.container():
        col1, col2 = st.columns([8, 1])
        if col1.button(("👉 " if is_current else "") + title, key="select_" + sid):
            st.session_state.current_sid = sid
            st.rerun()
        if col2.button("⋯", key="menu_" + sid):
            st.session_state["open_menu_sid"] = sid if st.session_state.get("open_menu_sid") != sid else None
        if st.session_state.get("open_menu_sid") == sid:
            with st.sidebar.expander("🔧 Opsi"):
                new_title = st.text_input("Ubah Judul", value=title, key="rename_" + sid)
                if st.button("✅ Simpan", key="save_" + sid):
                    st.session_state.sessions[sid]["title"] = new_title
                    st.session_state["open_menu_sid"] = None
                    save_sessions_to_file(st.session_state.sessions)
                if st.button("🗑️ Hapus", key="delete_" + sid):
                    to_delete = sid

if to_delete:
    del st.session_state.sessions[to_delete]
    if st.session_state.current_sid == to_delete:
        if st.session_state.sessions:
            st.session_state.current_sid = list(st.session_state.sessions.keys())[0]
        else:
            sid = str(uuid.uuid4())
            st.session_state.sessions[sid] = {
                "title": "Sesi Kamus Baru",
                "created": datetime.now(),
                "messages": []
            }
            st.session_state.current_sid = sid
    save_sessions_to_file(st.session_state.sessions)
    st.rerun()

if st.sidebar.button("➕ Buat Sesi Baru"):
    sid = str(uuid.uuid4())
    st.session_state.sessions[sid] = {
        "title": "Sesi Kamus Baru",
        "created": datetime.now(),
        "messages": []
    }
    st.session_state.current_sid = sid
    save_sessions_to_file(st.session_state.sessions)
    st.rerun()

# ========== Halaman Utama ==========
st.title("📚 Chatbot Kamus Bahasa Cirebon & Sunda")
st.markdown(f"###### Model aktif: `{MODEL}`")

sid = st.session_state.current_sid
session_data = st.session_state.sessions[sid]

# Reset sistem prompt jika berubah
if not session_data["messages"] or session_data["messages"][0]["role"] != "system":
    session_data["messages"].insert(0, {"role": "system", "content": system_prompt})

# Tampilkan chat
for msg in session_data["messages"]:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "timestamp" in msg:
            st.markdown(f"<span style='font-size:0.75em;color:gray'>{msg['timestamp']}</span>", unsafe_allow_html=True)

# Input pengguna
user_input = st.chat_input("Tanyakan arti kata atau kalimat...")

if user_input:
    if not st.session_state.api_key.strip():
        st.error("❌ Masukkan API Key OpenRouter terlebih dahulu.")
        st.stop()

    st.chat_message("user").markdown(user_input)
    session_data["messages"].append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_sessions_to_file(st.session_state.sessions)

    with st.spinner("Sedang menerjemahkan..."):
        headers = {
            "Authorization": f"Bearer {st.session_state.api_key.strip()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Kamus Cirebon Sunda"
        }
        payload = {
            "model": MODEL,
            "messages": session_data["messages"]
        }
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            if response.status_code == 200:
                reply = response.json()["choices"][0]["message"]["content"]
            elif response.status_code == 429:
                reply = "❌ Batas penggunaan model gratis harian tercapai."
            elif response.status_code == 401:
                reply = "❌ API Key salah atau expired."
            else:
                reply = f"❌ Error: {response.status_code} - {response.text}"
        except Exception as e:
            reply = f"❌ Terjadi kesalahan: {e}"

    st.chat_message("assistant").markdown(reply)
    session_data["messages"].append({
        "role": "assistant",
        "content": reply,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": MODEL
    })
    save_sessions_to_file(st.session_state.sessions)
