import streamlit as st
import google.generativeai as genai
import json
import random
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Startup Survivor", page_icon="💀", layout="wide")

# --- 2. MOD VE RENK AYARLARI ---
MODE_COLORS = {
    "Gerçekçi": "#2ECC71",  # Yeşil
    "Zor": "#F1C40F",       # Sarı
    "Spartan": "#E74C3C",   # Kırmızı
    "Extreme": "#9B59B6"    # Mor
}

# --- 3. PREMIUM CSS TASARIMI ---
def apply_custom_css(selected_mode):
    color = MODE_COLORS[selected_mode]
    st.markdown(
        f"""
        <style>
        /* Genel Font ve Arkaplan */
        .stApp {{
            font-family: 'Inter', sans-serif;
        }}
        
        /* Sidebar Ayarı */
        [data-testid="stSidebar"] {{
            min-width: 220px;
            max-width: 260px;
            background-color: #1a1b21;
            border-right: 1px solid #333;
        }}

        /* Hero Başlık (Gradient Efekt) */
        .hero-title {{
            font-size: 3rem;
            font-weight: 800;
            background: -webkit-linear-gradient(45deg, {color}, #ffffff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0px;
        }}
        .hero-subtitle {{
            font-size: 1.2rem;
            color: #b0b3b8;
            margin-bottom: 30px;
            font-weight: 300;
        }}

        /* Bilgi Kartları (Card Design) */
        .info-card {{
            background-color: #262730;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #363945;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 15px;
            transition: transform 0.2s;
        }}
        .info-card:hover {{
            transform: translateY(-2px);
            border-color: {color};
        }}
        
        /* Adım Başlıkları */
        .step-header {{
            font-size: 1.1rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
        }}
        .step-icon {{
            margin-right: 10px;
            background: {color};
            color: #000;
            width: 25px;
            height: 25px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            font-weight: bold;
        }}

        /* Küçük Kaybetme Şartları */
        .loss-condition-box {{
            background-color: #15161A;
            padding: 15px;
            border-radius: 8px;
            border-left: 3px solid {color};
            font-size: 0.85rem;
            color: #888;
            margin-top: 20px;
        }}
        .loss-item {{
            display: inline-block;
            margin-right: 15px;
            color: #ccc;
        }}
        
        /* Mod Rozeti */
        .mode-badge {{
            background-color: {color}20; /* %20 Opaklık */
            color: {color};
            border: 1px solid {color};
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
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
        "temperature": 0.8,
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

# --- 8. SENARYO YÖNETİCİSİ ---
def run_game_turn(user_input):
    current_month = st.session_state.month
    mode = st.session_state.selected_mode
    
    if mode == "Gerçekçi":
        persona = "Sen DENGELİ ve PROFESYONEL bir simülasyon motorusun. Gerçek dünya piyasa koşullarını, enflasyonu ve rekabeti simüle et. Mantıklı kararları ödüllendir."
    elif mode == "Zor":
        persona = "Sen ZORLAYICI bir finansal denetçisin. Kullanıcıya sunduğun seçenekler her zaman bir bedel (trade-off) içermeli. Kolay çıkış yolu bırakma."
    elif mode == "Spartan":
        persona = "Sen ACIMASIZ bir piyasa koşulusun (Bear Market). Oyuncunun batması için hukuki, teknik ve finansal engelleri en üst düzeye çıkar. Şans faktörü minimumda."
    elif mode == "Extreme":
        persona = "Sen KAOS TEORİSİSİN. Mantığı unut. Beklenmedik, absürt, komik veya felaket olaylar yarat (Meteor düşmesi, Uzaylı istilası, Viral kedi videoları sayesinde satış patlaması vb.)."
    
    system_prompt = f"""
    Sen 'Startup Survivor' simülasyonusun. Mod: {mode}.
    {persona}
    
    MEVCUT DURUM:
    - Ay: {current_month} / 12
    - Hedef: 12. Ayı tamamlamak (Exit Stratejisi).
    
    GÖREVLERİN:
    1. Kullanıcı girdisini analiz et.
    2. Hamleyi simüle et ve sonuçlarını yaz.
    3. 12. ay bittiyse ve şirket batmadıysa KAZANMA MESAJI ver.
    4. Değilse yeni bir OLAĞANÜSTÜ DURUM (Kriz/Fırsat) yarat.
    5. A ve B stratejik seçeneklerini sun.
    
    GÖRSEL FORMAT:
    - Başlıkları **KALIN** yap.
    - Satır aralarında boşluk bırak.
    
    ÇIKTI FORMATI (JSON):
    {{
        "text": "Simülasyon Raporu... \n\n🔥 DURUM: [Olay Detayı]... \n\nStratejin nedir?\n\n**A) [Strateji Adı]**\n[Açıklama...]\n\n**B) [Strateji Adı]**\n[Açıklama...]",
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

# --- 9. ARAYÜZ ---

# --- SIDEBAR (SADELEŞTİRİLDİ) ---
with st.sidebar:
    st.markdown("### ⚙️ Simülasyon Ayarları")
    
    # Sadece Dropdown (Yazı yok, temiz)
    if len(st.session_state.history) == 0:
        selected_mode = st.selectbox(
            "Zorluk Modu", 
            ["Gerçekçi", "Zor", "Spartan", "Extreme"],
            label_visibility="collapsed" # Başlığı gizle, daha temiz dursun
        )
        st.session_state.selected_mode = selected_mode
        
        # Seçilen modun ne olduğunu altına ufak not düşelim
        mode_descriptions = {
            "Gerçekçi": "Dengeli piyasa koşulları.",
            "Zor": "Sınırlı kaynaklar, zor kararlar.",
            "Spartan": "Acımasız, hata affetmez.",
            "Extreme": "Kaos ve rastgele olaylar."
        }
        st.caption(f"ℹ️ {mode_descriptions[selected_mode]}")
        
    else:
        # Oyun başladıysa kilitli göster
        st.success(f"Mod: {st.session_state.selected_mode}")
        selected_mode = st.session_state.selected_mode

    # CSS Uygula
    apply_custom_css(selected_mode)
    
    st.divider()
    
    # İstatistikler
    if not st.session_state.game_over:
        st.caption(f"🗓️ Süreç: {st.session_state.month}. Ay")
        st.progress(min(st.session_state.month / 12.0, 1.0))
    
    c1, c2 = st.columns([1, 3])
    with c1: st.write("💰")
    with c2: st.progress(safe_progress(st.session_state.stats['money']))
    
    c1, c2 = st.columns([1, 3])
    with c1: st.write("👥")
    with c2: st.progress(safe_progress(st.session_state.stats['team']))
    
    c1, c2 = st.columns([1, 3])
    with c1: st.write("🔥")
    with c2: st.progress(safe_progress(st.session_state.stats['motivation']))
    
    st.divider()
    if st.button("Yeniden Başlat", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- ANA EKRAN ---

# 1. LANDING PAGE (PROFESYONEL KARŞILAMA)
if len(st.session_state.history) == 0:
    
    # Hero Bölümü
    st.markdown('<div class="hero-title">Startup Survivor</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Gelişmiş Girişimcilik ve Kriz Yönetimi Simülasyonu</div>', unsafe_allow_html=True)

    # 3 Adımlı "Nasıl Çalışır?" Kartları (Profesyonel Görünüm)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(
            """
            <div class="info-card">
                <div class="step-header"><span class="step-icon">1</span> Girişimi Tanımla</div>
                <p style="color:#aaa; font-size:0.9rem;">
                    Sektör, bütçe ve ekip yapısını sisteme gir. Yapay zeka, bu verilere göre benzersiz bir pazar simülasyonu oluşturur.
                </p>
            </div>
            """, unsafe_allow_html=True
        )
        
    with col2:
        st.markdown(
            """
            <div class="info-card">
                <div class="step-header"><span class="step-icon">2</span> Krizleri Yönet</div>
                <p style="color:#aaa; font-size:0.9rem;">
                    Her ay finansal, operasyonel veya kaotik bir krizle karşılaşırsın. A/B stratejilerini seç veya kendi çözümünü yaz.
                </p>
            </div>
            """, unsafe_allow_html=True
        )
        
    with col3:
        st.markdown(
            """
            <div class="info-card">
                <div class="step-header"><span class="step-icon">3</span> Hayatta Kal</div>
                <p style="color:#aaa; font-size:0.9rem;">
                    Hedef 12 ay boyunca şirketi batırmadan (Exit) noktasına ulaşmak. Kaynaklarını dengeli kullan.
                </p>
            </div>
            """, unsafe_allow_html=True
        )

    # Input Alanı (Daha Temiz)
    startup_idea = st.chat_input("Girişim fikriniz, bütçeniz ve hedefiniz nedir?")
    
    # Alt Bilgi (Footer Tarzı Küçük Yazı)
    st.markdown(
        f"""
        <div class="loss-condition-box">
            <strong>⚠️ Simülasyon Başarısızlık Kriterleri:</strong><br>
            <span class="loss-item">💰 Nakit < 0</span>
            <span class="loss-item">👥 Ekip < 0</span>
            <span class="loss-item">🔥 Motivasyon < 0</span>
        </div>
        """, unsafe_allow_html=True
    )

    if startup_idea:
        with st.chat_message("user"): st.write(startup_idea)
        st.session_state.history.append({"role": "user", "parts": [f"Girişim Detayları: {startup_idea}"]})
        
        with st.spinner("Piyasa simülasyonu başlatılıyor..."):
            response = run_game_turn(f"Oyun başlasın. Detaylar: {startup_idea}")
            if response:
                st.session_state.history.append({"role": "model", "parts": [json.dumps(response)]})
                st.session_state.stats = response["stats"]
                st.session_state.month = response["month"]
                st.rerun()

# 2. OYUN EKRANI
elif not st.session_state.game_over:
    st.markdown(f'<span class="mode-badge">{st.session_state.selected_mode} MOD</span>', unsafe_allow_html=True)
    st.markdown("---")
    
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
        st.success("🏆 SİMÜLASYON BAŞARIYLA TAMAMLANDI! (EXIT)")
        if st.button("Yeni Simülasyon"):
            st.session_state.clear()
            st.rerun()
    else:
        user_move = st.chat_input("Kararınız nedir?")
        if user_move:
            with st.chat_message("user"): st.write(user_move)
            st.session_state.history.append({"role": "user", "parts": [user_move]})
            
            with st.spinner("Analiz ediliyor..."):
                response = run_game_turn(user_move)
                if response:
                    st.session_state.history.append({"role": "model", "parts": [json.dumps(response)]})
                    st.session_state.stats = response["stats"]
                    st.session_state.month = response["month"]
                    if response.get("game_over"):
                        st.session_state.game_over = True
                        st.session_state.game_over_reason = response.get("game_over_reason")
                    st.rerun()

# 3. OYUN SONU EKRANI
else:
    st.error(f"SİMÜLASYON SONLANDI: {st.session_state.game_over_reason}")
    if st.button("Tekrar Dene"):
        st.session_state.clear()
        st.rerun()

st.write("<br><br>", unsafe_allow_html=True)