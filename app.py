import streamlit as st
import google.generativeai as genai
import json
import random
import time

# --- 1. SAYFA AYARLARI (EN BAŞTA OLMALI) ---
st.set_page_config(page_title="Startup Survivor", page_icon="💀", layout="centered")

# --- 2. YARDIMCI FONKSİYONLAR ---
def safe_progress(value):
    """İlerleme çubuğunun 100'den büyük sayılarda çökmesini engeller."""
    try:
        val = float(value)
        if val > 100: return 1.0
        if val < 0: return 0.0
        return val / 100.0
    except:
        return 0.5

def clean_json(text):
    """JSON temizliği yapar."""
    text = text.replace("```json", "").replace("```", "").strip()
    # Bazen model çift parantez yollar, en dıştakini bulalım
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != 0:
        return text[start:end]
    return text

# --- 3. AKILLI MODEL SEÇİCİ (KEY TESTER MANTIĞI) ---
def get_best_model(api_key):
    genai.configure(api_key=api_key)
    
    # LİSTE GÜNCELLENDİ: Key Tester'da çalışan modelleri önceliklendirdik
    # 1.5-flash sorunlu olduğu için onu sona attık veya çıkardık.
    priority_list = [
        'gemini-2.0-flash',      # En Hızlısı
        'gemini-1.5-pro',        # En Akıllısı
        'gemini-pro'             # En Eskisi (Garanti Çalışır)
    ]
    
    try:
        # 1. Hızlı Liste Kontrolü
        for model_name in priority_list:
            try:
                model = genai.GenerativeModel(model_name)
                # Ufak test
                model.generate_content("T", request_options={"timeout": 3})
                return model
            except: continue
        
        # 2. Eğer listedekiler olmazsa sistemden bul
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Önce 'flash' ara
        for m_name in available_models:
            if 'flash' in m_name: return genai.GenerativeModel(m_name)
        
        # Yoksa herhangi birini al
        if available_models: 
            # model isminden 'models/' kısmını temizle
            clean_name = available_models[0].replace("models/", "")
            return genai.GenerativeModel(clean_name)
            
    except Exception: return None
    return None

# --- 4. CEVAP ÜRETME MERKEZİ ---
def get_ai_response_robust(prompt_history):
    if "GOOGLE_API_KEYS" not in st.secrets:
        st.error("HATA: Secrets dosyasında 'GOOGLE_API_KEYS' bulunamadı!")
        return None
        
    api_keys = st.secrets["GOOGLE_API_KEYS"]
    shuffled_keys = list(api_keys)
    random.shuffle(shuffled_keys)
    
    # Güvenlik Filtrelerini Kapat (Kriz senaryoları için)
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    last_error = ""
    
    for api_key in shuffled_keys:
        model = get_best_model(api_key)
        if model:
            try:
                response = model.generate_content(
                    prompt_history, 
                    safety_settings=safety_settings,
                    request_options={"timeout": 60} 
                )
                clean_text = clean_json(response.text)
                return json.loads(clean_text)
            except Exception as e:
                # Sadece gerçek hataları kaydet, denemeye devam et
                last_error = str(e)
                continue
    
    st.error(f"Sistem şu an cevap veremiyor. (Son Hata: {last_error})")
    return None

# --- 5. OYUN DEĞİŞKENLERİ ---
if "history" not in st.session_state: st.session_state.history = []
if "stats" not in st.session_state: st.session_state.stats = {"money": 50, "team": 50, "motivation": 50}
if "month" not in st.session_state: st.session_state.month = 0
if "game_over" not in st.session_state: st.session_state.game_over = False
if "game_over_reason" not in st.session_state: st.session_state.game_over_reason = ""

# --- 6. SENARYO YÖNETİCİSİ ---
def run_game_turn(user_input):
    system_prompt = """
    Sen 'Startup Survivor' oyunusun. ACIMASIZ bir oyun yöneticisisin.
    
    GÖREVLERİN:
    1. Hamleyi yorumla.
    2. KRİZ senaryosu yaz.
    3. A ve B SEÇENEKLERİNİ SUN.
    
    GÖRSEL KURAL:
    - Şıkların başlıklarını **KALIN** yap.
    - Şıkların arasına BOŞ SATIR koy.
    - Metinleri sıkıştırma.
    
    ÇIKTI FORMATI (JSON):
    {
        "text": "Hikaye... \n\n🔥 KRİZ: [Detay]... \n\nNe yapacaksın?\n\n**A) [Başlık]**\n[Detay...]\n\n**B) [Başlık]**\n[Detay...]",
        "month": (ay),
        "stats": {"money": 50, "team": 50, "motivation": 50},
        "game_over": false,
        "game_over_reason": ""
    }
    """
    
    chat_history = [{"role": "user", "parts": [system_prompt]}]
    for msg in st.session_state.history: chat_history.append(msg)
    chat_history.append({"role": "user", "parts": [user_input]})

    return get_ai_response_robust(chat_history)

# --- 7. ARAYÜZ (GÖRSEL DÜZENLEMELER) ---
st.title("💀 Startup Survivor")
st.caption("v3.0 Stable | Turbo Mode ⚡")
st.markdown("---")

col1, col2, col3 = st.columns(3)
col1.metric("💰 Nakit", f"{st.session_state.stats['money']}")
col1.progress(safe_progress(st.session_state.stats['money']))
col2.metric("👥 Ekip", f"%{st.session_state.stats['team']}")
col2.progress(safe_progress(st.session_state.stats['team']))
col3.metric("🔥 Motivasyon", f"%{st.session_state.stats['motivation']}")
col3.progress(safe_progress(st.session_state.stats['motivation']))

st.markdown("---")

# Sohbet Geçmişi
for msg in st.session_state.history:
    if msg["role"] == "model":
        try: content = json.loads(msg["parts"][0])["text"]
        except: content = msg["parts"][0]
        with st.chat_message("ai"): st.write(content)
    else:
        if "Sen 'Startup Survivor'" not in msg["parts"][0]:
            with st.chat_message("user"): st.write(msg["parts"][0])

# Oyun Akışı
if st.session_state.month == 0:
    st.info("Hoş geldin! Girişim fikrin ne?")
    startup_idea = st.chat_input("Örn: Yapay zeka destekli kedi maması...")
    if startup_idea:
        with st.spinner("Yatırımcılar fikrini analiz ediyor..."):
            response = run_game_turn(f"Oyun başlasın. Fikrim: {startup_idea}")
            if response:
                st.session_state.history.append({"role": "user", "parts": [f"Girişim: {startup_idea}"]})
                st.session_state.history.append({"role": "model", "parts": [json.dumps(response)]})
                st.session_state.stats = response["stats"]
                st.session_state.month = response["month"]
                st.rerun()

elif not st.session_state.game_over:
    user_move = st.chat_input("Hamleni yap (A, B veya kendi stratejin)...")
    if user_move:
        st.session_state.history.append({"role": "user", "parts": [user_move]})
        with st.spinner("Piyasa tepki veriyor..."):
            response = run_game_turn(user_move)
            if response:
                st.session_state.history.append({"role": "model", "parts": [json.dumps(response)]})
                st.session_state.stats = response["stats"]
                st.session_state.month = response["month"]
                if response.get("game_over"):
                    st.session_state.game_over = True
                    st.session_state.game_over_reason = response.get("game_over_reason")
                st.rerun()
    
    # --- SCROLL (KAYDIRMA) ÇÖZÜMÜ ---
    st.write("<br><br><br>", unsafe_allow_html=True) 

else:
    st.error(f"OYUN BİTTİ: {st.session_state.game_over_reason}")
    if st.button("Tekrar Oyna"):
        st.session_state.clear()
        st.rerun()