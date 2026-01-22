import streamlit as st
import google.generativeai as genai
import json
import random
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Startup Survivor", page_icon="💀", layout="wide")

# --- 2. MOD VE RENK AYARLARI ---
# Modlara göre renk kodları
MODE_COLORS = {
    "Gerçekçi": "#2ECC71",  # Yeşil
    "Zor": "#F1C40F",       # Sarı
    "Spartan": "#E74C3C",   # Kırmızı
    "Extreme": "#9B59B6"    # Mor
}

# --- 3. CSS İLE GÖRSEL DÜZENLEMELER (DİNAMİK) ---
def apply_custom_css(selected_mode):
    color = MODE_COLORS[selected_mode]
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"] {{
            min-width: 200px;
            max-width: 250px;
        }}
        .main-header {{
            font-size: 2.5rem;
            font-weight: 700;
            color: {color}; /* Başlık rengi moda göre değişir */
            text-align: center;
            margin-bottom: 0.5rem;
        }}
        .mode-badge {{
            background-color: {color};
            color: black;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 0.8rem;
            text-align: center;
            display: inline-block;
            margin-bottom: 1rem;
        }}
        .rules-box {{
            background-color: #262730;
            padding: 25px;
            border-radius: 10px;
            border: 1px solid {color}; /* Çerçeve rengi moda göre değişir */
            margin-bottom: 20px;
            font-size: 1.05rem;
        }}
        .example-box {{
            background-color: #1E1E1E;
            padding: 15px;
            border-left: 5px solid {color}; /* Sol çizgi rengi moda göre değişir */
            border-radius: 5px;
            margin-top: 10px;
            margin-bottom: 15px;
            font-style: italic;
            color: #E0E0E0;
            font-size: 0.95rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# --- 4. YARDIMCI FONKSİYONLAR ---
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

# --- 5. AKILLI MODEL SEÇİCİ ---
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

# --- 6. CEVAP ÜRETME MERKEZİ ---
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
        "temperature": 0.8, # Biraz daha yaratıcı olsun
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

# --- 7. OYUN DEĞİŞKENLERİ ---
if "history" not in st.session_state: st.session_state.history = []
if "stats" not in st.session_state: st.session_state.stats = {"money": 50, "team": 50, "motivation": 50}
if "month" not in st.session_state: st.session_state.month = 1
if "game_over" not in st.session_state: st.session_state.game_over = False
if "game_over_reason" not in st.session_state: st.session_state.game_over_reason = ""
if "selected_mode" not in st.session_state: st.session_state.selected_mode = "Gerçekçi"

# --- 8. SENARYO YÖNETİCİSİ (MODLARA GÖRE KİŞİLİK) ---
def run_game_turn(user_input):
    current_month = st.session_state.month
    mode = st.session_state.selected_mode
    
    # --- MODA GÖRE AI KİŞİLİĞİ ---
    if mode == "Gerçekçi":
        persona = """
        Sen DENGELİ ve GERÇEKÇİ bir oyun yöneticisisin. 
        Gerçek dünya standartlarına (enflasyon, rakip hamleleri, müşteri şikayetleri) uygun senaryolar üret. 
        Mantıklı hamleleri ödüllendir, saçma hamleleri cezalandır.
        """
    elif mode == "Zor":
        persona = """
        Sen ZORLAYICI ve DETAYCI bir oyun yöneticisisin.
        Kullanıcının önüne sunduğun A ve B seçenekleri 'Kötünün İyisi' (Dilemma) olmalı.
        Seçenekler ya çok pahalı olsun ya da büyük risk taşısın.
        Amacın: Kullanıcıyı A veya B'yi seçmek yerine KENDİ STRATEJİSİNİ yazmaya zorlamak.
        """
    elif mode == "Spartan":
        persona = """
        Sen ACIMASIZ ve ZALİM bir oyun yöneticisisin (Dark Souls Modu).
        Amacın oyuncuyu pes ettirmek. İmkansıza yakın hukuki, teknik veya finansal krizler yarat.
        Şans faktörü oyuncunun aleyhine işlesin. Başarı ihtimalini minimumda tut.
        """
    elif mode == "Extreme":
        persona = """
        Sen KAOTİK, EĞLENCELİ ve TAHMİN EDİLEMEZ bir oyun yöneticisisin.
        Mantığı çöpe at! Olay ufku sınırsız olsun.
        Örnek Olaylar: Ofise meteor düşmesi, uzaylıların gelip yatırım yapması, muhasebecinin tüm parayı coin'de batırması, haşere istilası, zaman yolcularının gelmesi.
        Bir turda oyuncuyu batırabilir, diğer turda milyoner yapabilirsin. Absürt ol!
        """
    
    system_prompt = f"""
    Sen 'Startup Survivor' oyunusun. Mod: {mode}.
    {persona}
    
    DURUM:
    - Ay: {current_month} / 12
    - Hedef: 12 Ay Hayatta Kalmak.
    
    GÖREVLERİN:
    1. Hamleyi moda uygun yorumla.
    2. 12. ay bittiyse ve batmadıysa KAZANDIR.
    3. Değilse moda uygun YENİ BİR KRİZ yaz.
    4. A ve B seçeneklerini sun.
    
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

# --- 9. ARAYÜZ VE SIDEBAR ---

# Sidebar: Mod Seçimi ve İstatistikler
with st.sidebar:
    st.markdown("### ⚙️ Oyun Ayarları")
    
    # Oyun başlamadıysa mod seçtir, başladıysa sadece göster (değiştirilemez)
    if len(st.session_state.history) == 0:
        selected_mode = st.selectbox(
            "Zorluk Seviyesi:", 
            ["Gerçekçi", "Zor", "Spartan", "Extreme"]
        )
        st.session_state.selected_mode = selected_mode
    else:
        st.info(f"🔒 Mod: **{st.session_state.selected_mode}** (Oyun sırasında değişmez)")
        selected_mode = st.session_state.selected_mode

    # CSS'i uygula (Rengi değiştir)
    apply_custom_css(selected_mode)
    
    st.divider()
    st.markdown("### 📊 Durum")
    
    if not st.session_state.game_over:
        st.caption(f"🗓️ Takvim: {st.session_state.month}. Ay")
        st.progress(min(st.session_state.month / 12.0, 1.0))
    
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

# 1. Başlangıç Ekranı
if len(st.session_state.history) == 0:
    st.markdown('<div class="main-header">💀 Startup Survivor</div>', unsafe_allow_html=True)
    
    # Moda göre açıklama metni değişir
    mode_desc = ""
    if selected_mode == "Gerçekçi":
        mode_desc = "Standart girişimcilik deneyimi. Dengeli ve öğretici."
        mode_badge = "🟢 GERÇEKÇİ MOD"
    elif selected_mode == "Zor":
        mode_desc = "Seçenekler yetersiz, krizler karmaşık. Kendi yolunu çizmek zorundasın."
        mode_badge = "🟡 ZOR MOD"
    elif selected_mode == "Spartan":
        mode_desc = "İmkansıza yakın. Oyun senin kaybetmeni istiyor. Sadece en inatçılar dayanabilir."
        mode_badge = "🔴 SPARTAN MOD"
    elif selected_mode == "Extreme":
        mode_desc = "Mantık yok, kaos var! Uzaylılar, meteorlar, absürt olaylar. Her an her şey olabilir."
        mode_badge = "🟣 EXTREME (KAOS) MOD"

    st.markdown(f'<div style="text-align: center;"><span class="mode-badge">{mode_badge}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-text">{mode_desc}</div>', unsafe_allow_html=True)

    # Rehber Kutusu
    st.markdown(
        """
        <div class="rules-box">
            <h4>🚀 Girişimini Tanımla</h4>
            <p>Seçtiğin moda uygun bir senaryo için yapay zekaya detay ver:</p>
            <ul>
                <li>💡 <strong>Fikir:</strong> Ne yapacaksın?</li>
                <li>💰 <strong>Bütçe & Kaynak:</strong> Ne kadar paran ve ekibin var?</li>
                <li>🎯 <strong>Hedef:</strong> Nereye varmak istiyorsun?</li>
            </ul>
            <div class="example-box">
                "Bir e-ticaret sitesi kuracağım. Cebimde 100.000 TL var, tek başımayım ve evden çalışıyorum."
            </div>
            <hr>
            <h5>💀 Kaybetme Şartları:</h5>
            <p>Nakit, Ekip veya Motivasyon <strong>0 olursa</strong> oyun biter.</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    startup_idea = st.chat_input("Girişimini anlat ve başlat...")
    
    if startup_idea:
        with st.chat_message("user"): st.write(startup_idea)
        st.session_state.history.append({"role": "user", "parts": [f"Girişim: {startup_idea}"]})
        
        with st.spinner(f"{selected_mode} modunda senaryo oluşturuluyor..."):
            response = run_game_turn(f"Oyun başlasın. Detaylar: {startup_idea}")
            if response:
                st.session_state.history.append({"role": "model", "parts": [json.dumps(response)]})
                st.session_state.stats = response["stats"]
                st.session_state.month = response["month"]
                st.rerun()

# 2. Oyun Devam Ediyor
elif not st.session_state.game_over:
    st.header("💀 Startup Survivor")
    
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
        st.success("🎉 TEBRİKLER! BU ZORLU YOLCULUĞU TAMAMLADIN!")
        if st.button("Yeni Macera"):
            st.session_state.clear()
            st.rerun()
    else:
        user_move = st.chat_input("Hamleni yap...")
        if user_move:
            with st.chat_message("user"): st.write(user_move)
            st.session_state.history.append({"role": "user", "parts": [user_move]})
            
            with st.spinner("Sonuçlar hesaplanıyor..."):
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