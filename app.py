import streamlit as st
import google.generativeai as genai
import json
import random
import time
import re

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Startup Survivor", page_icon="💀", layout="centered")

# --- YARDIMCI: JSON TEMİZLEYİCİ ---
def clean_json(text):
    try:
        text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != 0:
            return text[start:end]
        return text
    except:
        return text

# --- AKILLI MODEL SEÇİCİ ---
def get_best_model(api_key):
    genai.configure(api_key=api_key)
    # Öncelik sırası: Hızlı olan Flash modelleri
    priority_list = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
    
    try:
        for model_name in priority_list:
            try:
                model = genai.GenerativeModel(model_name)
                # Ufak test
                model.generate_content("T", request_options={"timeout": 5})
                return model
            except: continue
        
        # Listeden bulma (Yedek plan)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m_name in available_models:
            if 'flash' in m_name: return genai.GenerativeModel(m_name)
        if available_models: return genai.GenerativeModel(available_models[0])
            
    except Exception: return None
    return None

# --- GÜÇLENDİRİLMİŞ CEVAP ALMA FONKSİYONU ---
def get_ai_response_robust(prompt_history):
    if "GOOGLE_API_KEYS" not in st.secrets:
        st.error("HATA: Secrets dosyasında 'GOOGLE_API_KEYS' bulunamadı!")
        return None
        
    api_keys = st.secrets["GOOGLE_API_KEYS"]
    shuffled_keys = list(api_keys)
    random.shuffle(shuffled_keys)
    
    # Güvenlik ayarlarını kapatıyoruz ki kriz senaryolarını engellemesin
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
                # BURASI KRİTİK: Süreyi 90 saniyeye çıkardık
                response = model.generate_content(
                    prompt_history, 
                    safety_settings=safety_settings,
                    request_options={"timeout": 90} 
                )
                
                clean_text = clean_json(response.text)
                return json.loads(clean_text)
                
            except Exception as e:
                error_msg = str(e)
                # Eğer 504 veya 429 hatasıysa diğer anahtarı dene
                if "504" in error_msg or "429" in error_msg:
                    last_error = f"Zaman aşımı veya kota ({api_key[:5]}...)"
                    continue 
                else:
                    last_error = error_msg
                    continue
    
    st.error(f"Sunucular şu an aşırı yoğun. Lütfen 10 saniye bekleyip tekrar deneyin. (Hata: {last_error})")
    return None

# --- OYUN DEĞİŞKENLERİ ---
if "history" not in st.session_state: st.session_state.history = []
if "stats" not in st.session_state: st.session_state.stats = {"money": 50, "team": 50, "motivation": 50}
if "month" not in st.session_state: st.session_state.month = 0
if "game_over" not in st.session_state: st.session_state.game_over = False
if "game_over_reason" not in st.session_state: st.session_state.game_over_reason = ""

# --- OYUN SENARYOSU (PROMPT) ---
def run_game_turn(user_input):
    system_prompt = """
    Sen 'Startup Survivor' oyunusun. ACIMASIZ bir oyun yöneticisisin.
    
    GÖREVLERİN:
    1. Kullanıcının girdiği hamleyi (A, B veya kendi yazdığı strateji) yorumla. Eğer mantıklıysa ödüllendir, saçmaysa cezalandır.
    2. Şirketin o anki durumuna uygun yeni bir KRİZ yarat.
    3. Kullanıcıya çıkış yolu olarak A ve B seçenekleri sun (Ama kullanıcı kendi fikrini de yazabilir, bunu unutma).
    
    ÇIKTI FORMATI (Sadece bu JSON formatını kullan):
    {
        "text": "Hamlenin sonucu... \n\n🔥 YENİ KRİZ: [Kriz detayları]... \n\nSeçeneklerin:\nA) [Riskli ama ucuz yol]\nB) [Güvenli ama pahalı yol]\n(Veya kendi stratejini yazabilirsin)",
        "month": (ay numarası),
        "stats": {"money": (yeni para), "team": (yeni ekip), "motivation": (yeni motivasyon)},
        "game_over": false,
        "game_over_reason": ""
    }
    """
    
    chat_history = [{"role": "user", "parts": [system_prompt]}]
    for msg in st.session_state.history: chat_history.append(msg)
    chat_history.append({"role": "user", "parts": [user_input]})

    return get_ai_response_robust(chat_history)

# --- ARAYÜZ ---
st.title("💀 Startup Survivor")
st.caption("Game Master Mode: Active | Timeout: 90s 🟢")
st.markdown("---")

col1, col2, col3 = st.columns(3)
col1.metric("💰 Nakit", f"%{st.session_state.stats['money']}")
col1.progress(st.session_state.stats['money'] / 100)
col2.metric("👥 Ekip", f"%{st.session_state.stats['team']}")
col2.progress(st.session_state.stats['team'] / 100)
col3.metric("🔥 Motivasyon", f"%{st.session_state.stats['motivation']}")
col3.progress(st.session_state.stats['motivation'] / 100)
st.markdown("---")

# Mesaj Geçmişi
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
        with st.spinner("Yatırımcılar fikrini analiz ediyor (Bu işlem 15-20 saniye sürebilir)..."):
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
else:
    st.error(f"OYUN BİTTİ: {st.session_state.game_over_reason}")
    if st.button("Tekrar Oyna"):
        st.session_state.clear()
        st.rerun()