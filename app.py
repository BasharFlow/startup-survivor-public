import streamlit as st
import google.generativeai as genai
import json
import random
import time

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Startup Survivor", page_icon="🚀", layout="centered")

# --- AKILLI MODEL SEÇİCİ (Sorunu Çözen Kısım) ---
def get_best_model(api_key):
    """
    Bu fonksiyon, verilen anahtarın kullanabileceği modelleri listeler
    ve 'flash' içeren en yeni modeli otomatik seçer.
    """
    genai.configure(api_key=api_key)
    
    # Öncelikli olarak denenecek modeller (Senin listene göre)
    priority_list = [
        'gemini-2.5-flash', 
        'gemini-2.0-flash', 
        'gemini-1.5-flash',
        'gemini-1.5-pro'
    ]
    
    try:
        # Önce hızlıca favorileri deneyelim (Listeleme yapmadan)
        for model_name in priority_list:
            try:
                model = genai.GenerativeModel(model_name)
                # Ufak bir test atışı
                model.generate_content("Test", request_options={"timeout": 5})
                return model # Çalıştı! Bunu kullan.
            except:
                continue # Bu çalışmadı, sonrakine geç.
        
        # Eğer favoriler çalışmazsa, hesabın tüm listesini çekip bakalım
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # Listeden 'flash' içeren ilkini kap
        for m_name in available_models:
            if 'flash' in m_name:
                return genai.GenerativeModel(m_name)
                
        # Hiçbiri yoksa listeden ilkini al
        if available_models:
            return genai.GenerativeModel(available_models[0].name)
            
    except Exception as e:
        return None
    
    return None

# --- ÇOKLU ANAHTAR YÖNETİMİ ---
def get_ai_response_robust(prompt_history):
    if "GOOGLE_API_KEYS" not in st.secrets:
        st.error("HATA: Secrets dosyasında 'GOOGLE_API_KEYS' bulunamadı!")
        return None
        
    api_keys = st.secrets["GOOGLE_API_KEYS"]
    shuffled_keys = list(api_keys)
    random.shuffle(shuffled_keys) # Yük dengeleme
    
    for api_key in shuffled_keys:
        # Bu anahtar için en iyi modeli bul
        model = get_best_model(api_key)
        
        if model:
            try:
                # Modeli bulduk, şimdi asıl soruyu soralım
                response = model.generate_content(prompt_history, request_options={"timeout": 15})
                text = response.text.replace("```json", "").replace("```", "").strip()
                return json.loads(text)
            except Exception:
                continue # Bu anahtarda veya modelde sorun çıktı, diğer anahtara geç.
    
    st.error("Sistem şu an çok yoğun. Lütfen 1 dakika sonra tekrar deneyin.")
    return None

# --- OYUN DEĞİŞKENLERİ ---
if "history" not in st.session_state: st.session_state.history = []
if "stats" not in st.session_state: st.session_state.stats = {"money": 50, "team": 50, "motivation": 50}
if "month" not in st.session_state: st.session_state.month = 0
if "game_over" not in st.session_state: st.session_state.game_over = False
if "game_over_reason" not in st.session_state: st.session_state.game_over_reason = ""

# --- ANA OYUN FONKSİYONU ---
def run_game_turn(user_input):
    system_prompt = """
    Sen 'Startup Survivor' adında zorlu bir girişimcilik simülasyonusun.
    Görevin: Kullanıcının startup'ını 12 ay boyunca hayatta tutmaya çalışmak.
    Kurallar: 1. Her turda kriz yarat. 2. İstatistikleri (Money, Team, Motivation) yönet. 3. Biri 0 olursa Game Over.
    Cevabını SADECE şu JSON formatında ver:
    {"text": "Hikaye...", "month": (ay), "stats": {"money": 50, "team": 50, "motivation": 50}, "game_over": false, "game_over_reason": ""}
    """
    
    chat_history = [{"role": "user", "parts": [system_prompt]}]
    for msg in st.session_state.history: chat_history.append(msg)
    chat_history.append({"role": "user", "parts": [user_input]})

    return get_ai_response_robust(chat_history)

# --- ARAYÜZ ---
st.title("🚀 Startup Survivor")
st.caption("Auto-Model Detection Active 🟢")
st.markdown("---")

col1, col2, col3 = st.columns(3)
col1.metric("💰 Nakit", f"%{st.session_state.stats['money']}")
col1.progress(st.session_state.stats['money'] / 100)
col2.metric("👥 Ekip", f"%{st.session_state.stats['team']}")
col2.progress(st.session_state.stats['team'] / 100)
col3.metric("🔥 Motivasyon", f"%{st.session_state.stats['motivation']}")
col3.progress(st.session_state.stats['motivation'] / 100)
st.markdown("---")

for msg in st.session_state.history:
    if msg["role"] == "model":
        try: content = json.loads(msg["parts"][0])["text"]
        except: content = msg["parts"][0]
        with st.chat_message("ai"): st.write(content)
    else:
        if "Sen 'Startup Survivor'" not in msg["parts"][0]:
            with st.chat_message("user"): st.write(msg["parts"][0])

if st.session_state.month == 0:
    st.info("Hoş geldin! Şirketinin adı ne?")
    startup_idea = st.chat_input("Girişim fikrini yaz...")
    if startup_idea:
        with st.spinner("Yatırımcılar fikrini inceliyor..."):
            response = run_game_turn(f"Oyun başlasın. Fikrim: {startup_idea}")
            if response:
                st.session_state.history.append({"role": "user", "parts": [f"Girişim: {startup_idea}"]})
                st.session_state.history.append({"role": "model", "parts": [json.dumps(response)]})
                st.session_state.stats = response["stats"]
                st.session_state.month = response["month"]
                st.rerun()
elif not st.session_state.game_over:
    user_move = st.chat_input("Ne yapacaksın?")
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