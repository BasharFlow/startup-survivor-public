import streamlit as st
import google.generativeai as genai
import json
import random
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Startup Survivor", page_icon="💀", layout="wide")

# --- 2. CSS İLE GÖRSEL DÜZENLEMELER (YENİ) ---
# Burası Sidebar'ı daraltır ve yazı tiplerini güzelleştirir.
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        min-width: 200px;
        max-width: 250px;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-text {
        font-size: 1.1rem;
        color: #FAFAFA;
        text-align: center;
        margin-bottom: 2rem;
    }
    .rules-box {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #4F4F4F;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 3. YARDIMCI FONKSİYONLAR ---
def safe_progress(value):
    try:
        val = float(value)
        if val > 100: return 1.0
        if val < 0: return 0.0
        return val / 100.0
    except:
        return 0.5

def clean_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != 0:
        return text[start:end]
    return text

# --- 4. AKILLI MODEL SEÇİCİ ---
def get_best_model(api_key):
    genai.configure(api_key=api_key)
    priority_list = ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash']
    try:
        for model_name in priority_list:
            try:
                model = genai.GenerativeModel(model_name)
                model.generate_content("T", request_options={"timeout": 3})
                return model
            except: continue
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m_name in available_models:
            if 'flash' in m_name: return genai.GenerativeModel(m_name)
        if available_models: 
            return genai.GenerativeModel(available_models[0].replace("models/", ""))
    except Exception: return None
    return None

# --- 5. CEVAP ÜRETME MERKEZİ ---
def get_ai_response_robust(prompt_history):
    if "GOOGLE_API_KEYS" not in st.secrets:
        st.error("HATA: Secrets dosyasında 'GOOGLE_API_KEYS' bulunamadı!")
        return None
        
    api_keys = st.secrets["GOOGLE_API_KEYS"]
    shuffled_keys = list(api_keys)
    random.shuffle(shuffled_keys)
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    generation_config = {
        "temperature": 0.7,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json"
    }
    
    last_error = ""
    for api_key in shuffled_keys:
        model = get_best_model(api_key)
        if model:
            try:
                response = model.generate_content(
                    prompt_history, 
                    safety_settings=safety_settings,
                    generation_config=generation_config, 
                    request_options={"timeout": 90} 
                )
                clean_text = clean_json(response.text)
                return json.loads(clean_text)
            except Exception as e:
                last_error = f"Hata: {str(e)}"
                continue
    
    st.error(f"Sistem şu an cevap veremiyor. {last_error}")
    return None

# --- 6. OYUN DEĞİŞKENLERİ ---
if "history" not in st.session_state: st.session_state.history = []
if "stats" not in st.session_state: st.session_state.stats = {"money": 50, "team": 50, "motivation": 50}
if "month" not in st.session_state: st.session_state.month = 1
if "game_over" not in st.session_state: st.session_state.game_over = False
if "game_over_reason" not in st.session_state: st.session_state.game_over_reason = ""

# --- 7. SENARYO YÖNETİCİSİ ---
def run_game_turn(user_input):
    current_month = st.session_state.month
    
    system_prompt = f"""
    Sen 'Startup Survivor' oyunusun. ACIMASIZ bir oyun yöneticisisin.
    
    DURUM:
    - Ay: {current_month} / 12
    - Hedef: Şirketi batırmadan 12 ayı tamamlamak.
    
    GÖREVLERİN:
    1. Hamleyi yorumla.
    2. 12. ay bittiyse ve batmadıysa KAZANDIR ("game_over": true, "reason": "BAŞARDIN!").
    3. Değilse yeni KRİZ yaz.
    4. A ve B SEÇENEKLERİNİ SUN.
    
    GÖRSEL KURALLAR:
    - Şık başlıklarını **KALIN** yap.
    - Şıkların arasına BOŞ SATIR koy.
    
    ÇIKTI FORMATI (JSON):
    {{
        "text": "Hikaye... \n\n🔥 KRİZ: [Detay]... \n\nNe yapacaksın?\n\n**A) [Başlık]**\n[Detay...]\n\n**B) [Başlık]**\n[Detay...]",
        "month": {current_month + 1},
        "stats": {{"money": 50, "team": 50, "motivation": 50}},
        "game_over": false,
        "game_over_reason": ""
    }}
    """
    
    chat_history = [{"role": "user", "parts": [system_prompt]}]
    for msg in st.session_state.history: chat_history.append(msg)
    chat_history.append({"role": "user", "parts": [user_input]})

    return get_ai_response_robust(chat_history)

# --- 8. ARAYÜZ ---

# --- YENİ SIDEBAR (DAHA KÜÇÜK VE KOMPAKT) ---
with st.sidebar:
    st.markdown("### 📊 Durum") # Başlığı küçülttük
    
    if not st.session_state.game_over:
        st.caption(f"🗓️ Takvim: {st.session_state.month}. Ay")
        st.progress(min(st.session_state.month / 12.0, 1.0))
    
    st.divider()
    
    # Metrikleri daha kompakt göstermek için
    c1, c2 = st.columns([1, 3])
    with c1: st.write("💰")
    with c2: st.progress(safe_progress(st.session_state.stats['money']))
    st.caption(f"Nakit: %{st.session_state.stats['money']}")
    
    c1, c2 = st.columns([1, 3])
    with c1: st.write("👥")
    with c2: st.progress(safe_progress(st.session_state.stats['team']))
    st.caption(f"Ekip: %{st.session_state.stats['team']}")
    
    c1, c2 = st.columns([1, 3])
    with c1: st.write("🔥")
    with c2: st.progress(safe_progress(st.session_state.stats['motivation']))
    st.caption(f"Motivasyon: %{st.session_state.stats['motivation']}")
    
    st.divider()
    if st.button("🔄 Sıfırla", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- ANA EKRAN ---

# 1. Başlangıç Ekranı (Özel Tasarım)
if len(st.session_state.history) == 0:
    st.markdown('<div class="main-header">💀 Startup Survivor</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-text">Girişimcilik sadece parlak bir fikir değildir, kanlı bir hayatta kalma savaşıdır.</div>', unsafe_allow_html=True)

    # ÖZEL BİLGİLENDİRME KUTUSU (Senin istediğin metinler)
    st.markdown(
        """
        <div class="rules-box">
            <h4>🚀 Aklındaki Girişim Piyasaya Dayanabilir mi?</h4>
            <p>Kurmak istediğin şirketin hangi zorluklarla karşılaşacağını, yatırımcıların ne diyeceğini ve kriz anında nasıl kararlar vereceğini merak mı ediyorsun?</p>
            <p><strong>Burası güvenli bir simülasyon. Fikrini yaz ve kaderini test et!</strong></p>
            <hr>
            <h5>📜 Oyunun Kuralları:</h5>
            <ul>
                <li>🗓️ <strong>Hedef:</strong> Şirketini batırmadan <strong>12 Ay</strong> boyunca yönetmek.</li>
                <li>💀 <strong>Kaybetme Şartı:</strong> Aşağıdaki 3 değerden biri <strong>0'a düşerse</strong> oyun biter:
                    <ul>
                        <li>💰 <strong>Nakit:</strong> Paranız biterse iflas edersiniz.</li>
                        <li>👥 <strong>Ekip:</strong> Çalışan kalmazsa operasyon durur.</li>
                        <li>🔥 <strong>Motivasyon:</strong> İnancınız biterse pes edersiniz.</li>
                    </ul>
                </li>
            </ul>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    startup_idea = st.chat_input("Girişim fikrini buraya yaz ve maceraya başla...")
    
    if startup_idea:
        with st.chat_message("user"): st.write(startup_idea)
        st.session_state.history.append({"role": "user", "parts": [f"Girişim: {startup_idea}"]})
        
        with st.spinner("Piyasa analiz ediliyor..."):
            response = run_game_turn(f"Oyun başlasın. Fikrim: {startup_idea}")
            if response:
                st.session_state.history.append({"role": "model", "parts": [json.dumps(response)]})
                st.session_state.stats = response["stats"]
                st.session_state.month = response["month"]
                st.rerun()

# 2. Oyun Devam Ediyor
elif not st.session_state.game_over:
    st.header("💀 Startup Survivor")
    
    # Geçmiş Mesajlar
    for msg in st.session_state.history:
        if msg["role"] == "model":
            try: content = json.loads(msg["parts"][0])["text"]
            except: content = msg["parts"][0]
            with st.chat_message("ai"): st.write(content)
        else:
            if "Sen 'Startup Survivor'" not in msg["parts"][0]:
                with st.chat_message("user"): st.write(msg["parts"][0])

    if st.session_state.month > 12:
        st.balloons()
        st.success("🎉 TEBRİKLER! 12 AYI TAMAMLADIN VE ŞİRKETİ HALKA ARZ ETTİN! (EXIT)")
        if st.button("Yeni Macera"):
            st.session_state.clear()
            st.rerun()
    else:
        user_move = st.chat_input("Hamleni yap (A, B veya kendi stratejin)...")
        if user_move:
            with st.chat_message("user"): st.write(user_move)
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

# 3. Oyun Bitti
else:
    st.header("💀 Startup Survivor")
    for msg in st.session_state.history:
        if msg["role"] == "model":
            try: content = json.loads(msg["parts"][0])["text"]
            except: content = msg["parts"][0]
            with st.chat_message("ai"): st.write(content)
        else:
            if "Sen 'Startup Survivor'" not in msg["parts"][0]:
                with st.chat_message("user"): st.write(msg["parts"][0])
                
    st.error(f"💀 OYUN BİTTİ: {st.session_state.game_over_reason}")
    if st.button("Tekrar Dene"):
        st.session_state.clear()
        st.rerun()

st.write("<br><br>", unsafe_allow_html=True)