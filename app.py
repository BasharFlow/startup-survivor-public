import streamlit as st
import google.generativeai as genai
import json
import random
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Startup Survivor", page_icon="💀", layout="wide") 
# Not: Layout="wide" yaptık ki yan panel ve chat rahat sığsın.

# --- 2. YARDIMCI FONKSİYONLAR ---
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

# --- 3. AKILLI MODEL SEÇİCİ ---
def get_best_model(api_key):
    genai.configure(api_key=api_key)
    # 2.0 Flash ve 1.5 Pro en stabil modeller
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

# --- 4. CEVAP ÜRETME MERKEZİ ---
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

# --- 5. OYUN DEĞİŞKENLERİ ---
if "history" not in st.session_state: st.session_state.history = []
if "stats" not in st.session_state: st.session_state.stats = {"money": 50, "team": 50, "motivation": 50}
if "month" not in st.session_state: st.session_state.month = 1
if "game_over" not in st.session_state: st.session_state.game_over = False
if "game_over_reason" not in st.session_state: st.session_state.game_over_reason = ""

# --- 6. SENARYO YÖNETİCİSİ ---
def run_game_turn(user_input):
    current_month = st.session_state.month
    
    system_prompt = f"""
    Sen 'Startup Survivor' oyunusun. ACIMASIZ bir oyun yöneticisisin.
    
    DURUM:
    - Ay: {current_month} / 12
    - Hedef: Şirketi batırmadan 12 ayı tamamlamak.
    
    GÖREVLERİN:
    1. Hamleyi yorumla.
    2. Eğer 12. ay bittiyse ve batmadıysa KAZANDIR ("game_over": true, "reason": "BAŞARDIN!").
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
    
    # Geçmişi kopyala ve yeni mesajı ekle (AI'ya göndermek için)
    chat_history = [{"role": "user", "parts": [system_prompt]}]
    for msg in st.session_state.history: chat_history.append(msg)
    chat_history.append({"role": "user", "parts": [user_input]})

    return get_ai_response_robust(chat_history)

# --- 7. ARAYÜZ ---

# --- YENİLİK 1: SABİT YAN PANEL (SIDEBAR) ---
# İstatistikler artık burada sabit duracak, sayfa kaydıkça kaybolmayacak.
with st.sidebar:
    st.title("📊 Şirket Durumu")
    
    # Zaman Çubuğu
    if not st.session_state.game_over:
        progress_val = min(st.session_state.month / 12.0, 1.0)
        st.progress(progress_val, text=f"🗓️ Ay: {st.session_state.month} / 12")
    
    st.markdown("---")
    
    # Metrikler (Alt alta)
    st.metric("💰 Nakit", f"%{st.session_state.stats['money']}")
    st.progress(safe_progress(st.session_state.stats['money']))
    
    st.metric("👥 Ekip", f"%{st.session_state.stats['team']}")
    st.progress(safe_progress(st.session_state.stats['team']))
    
    st.metric("🔥 Motivasyon", f"%{st.session_state.stats['motivation']}")
    st.progress(safe_progress(st.session_state.stats['motivation']))
    
    st.markdown("---")
    if st.button("🔄 Oyunu Sıfırla"):
        st.session_state.clear()
        st.rerun()

# --- ANA EKRAN (CHAT) ---
st.header("💀 Startup Survivor")

# 1. Önce Geçmiş Mesajları Yazdır
for msg in st.session_state.history:
    if msg["role"] == "model":
        try: content = json.loads(msg["parts"][0])["text"]
        except: content = msg["parts"][0]
        with st.chat_message("ai"): st.write(content)
    else:
        # Sistem promptlarını gizle, sadece kullanıcının yazdıklarını göster
        if "Sen 'Startup Survivor'" not in msg["parts"][0]:
            with st.chat_message("user"): st.write(msg["parts"][0])

# --- OYUN MANTIĞI VE HIZLI MESAJLAŞMA ---

# Durum 1: Oyun Yeni Başlıyor
if len(st.session_state.history) == 0:
    st.info("👋 Hoş geldin! 12 Ay boyunca hayatta kalmaya çalış. İlk 3 ay çok kritik!")
    startup_idea = st.chat_input("Girişim fikrin ne? (Örn: Uçan Kargo Drone'ları)")
    
    if startup_idea:
        # YENİLİK 2: Mesajı anında ekranda göster (Kullanıcı beklerken sıkılmasın)
        with st.chat_message("user"):
            st.write(startup_idea)
        
        # Geçmişe ekle
        st.session_state.history.append({"role": "user", "parts": [f"Girişim: {startup_idea}"]})
        
        with st.spinner("Yatırımcılar fikrini inceliyor..."):
            response = run_game_turn(f"Oyun başlasın. Fikrim: {startup_idea}")
            if response:
                st.session_state.history.append({"role": "model", "parts": [json.dumps(response)]})
                st.session_state.stats = response["stats"]
                st.session_state.month = response["month"]
                st.rerun() # Sayfayı yenile ki yeni cevap ve istatistikler güncellensin

# Durum 2: Oyun Devam Ediyor
elif not st.session_state.game_over:
    if st.session_state.month > 12:
        st.balloons()
        st.success("🎉 TEBRİKLER! 12 AYI TAMAMLADIN VE ŞİRKETİ HALKA ARZ ETTİN! (EXIT)")
    else:
        user_move = st.chat_input("Hamleni yap (A, B veya kendi stratejin)...")
        
        if user_move:
            # YENİLİK 2: Mesajı anında ekranda göster
            with st.chat_message("user"):
                st.write(user_move)
            
            # Geçmişe ekle
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

# Durum 3: Oyun Bitti
else:
    st.error(f"💀 OYUN BİTTİ: {st.session_state.game_over_reason}")
    if st.button("Tekrar Dene"):
        st.session_state.clear()
        st.rerun()

# Scroll (Kaydırma) Çözümü - En alta boşluk bırak
st.write("<br><br>", unsafe_allow_html=True)