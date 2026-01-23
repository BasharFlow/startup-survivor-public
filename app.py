import streamlit as st
import google.generativeai as genai
import json
import random
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Startup Survivor RPG", page_icon="💀", layout="wide")

# --- 2. AYARLAR & SABİTLER ---
MODE_COLORS = {
    "Gerçekçi": "#2ECC71", "Zor": "#F1C40F", "Türkiye Simülasyonu": "#1ABC9C", 
    "Spartan": "#E74C3C", "Extreme": "#9B59B6"
}

# --- 3. CSS TASARIMI (Responsive & Temiz) ---
def apply_custom_css(selected_mode):
    color = MODE_COLORS.get(selected_mode, "#2ECC71")
    st.markdown(
        f"""
        <style>
        .stApp {{ font-family: 'Inter', sans-serif; }}
        [data-testid="stSidebar"] {{ 
            min-width: 250px; max-width: 300px; 
            background-color: #1a1b21; border-right: 1px solid #333; 
        }}
        .hero-container {{
            text-align: center; padding: 40px 0;
        }}
        .hero-title {{
            font-size: 3.5rem; font-weight: 800;
            background: -webkit-linear-gradient(45deg, {color}, #ffffff);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin: 0;
        }}
        .hero-subtitle {{
            font-size: 1.2rem; color: #bbb; font-weight: 300; margin-top: 10px;
        }}
        .trait-card {{
            background-color: #262730; padding: 8px; border-radius: 6px;
            border-left: 3px solid {color}; margin-bottom: 5px; font-size: 0.9rem;
        }}
        /* Buton Gizleme (Eski butonlar kalmasın) */
        .stButton>button {{ width: 100%; }}
        </style>
        """, unsafe_allow_html=True,
    )

# --- 4. YARDIMCI FONKSİYONLAR ---
def clean_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end != 0: return text[start:end]
    return text

def format_currency(amount):
    return f"{amount:,.0f} ₺".replace(",", ".")

# --- 5. ŞANS KARTI MOTORU ---
def trigger_chance_card():
    if random.random() < 0.20:
        cards = [
            {"title": "📉 Vergi Affı!", "desc": "Devlet vergileri sildi.", "effect": "money", "val": 25000},
            {"title": "⛈️ Ofisi Su Bastı", "desc": "Tesisat patladı.", "effect": "money", "val": -15000},
            {"title": "👋 Toksik İstifa", "desc": "Negatif çalışan gitti.", "effect": "motivation", "val": 15},
            {"title": "🚀 Viral Oldunuz", "desc": "Influencer paylaşımı.", "effect": "money", "val": 50000},
            {"title": "📜 Mevzuat Krizi", "desc": "İşler yavaşladı.", "effect": "motivation", "val": -10},
        ]
        if st.session_state.get("selected_mode") == "Türkiye Simülasyonu":
            cards.append({"title": "💸 Kira Zammı", "desc": "Ofis sahibi kirayı katladı.", "effect": "money", "val": -30000})
            cards.append({"title": "🍲 Yemek Kartı", "desc": "Kartlar yatmadı, isyan var.", "effect": "team", "val": -15})
        return random.choice(cards)
    return None

# --- 6. AI MODEL BAĞLANTISI (HIZLANDIRILMIŞ) ---
def get_ai_response(prompt_history):
    if "GOOGLE_API_KEYS" not in st.secrets:
        st.error("HATA: API Key bulunamadı!")
        return None
    
    # HIZ AYARI: Tüm keyleri tek tek denemek yerine rastgele seçip bağlanır.
    api_keys = st.secrets["GOOGLE_API_KEYS"]
    key = random.choice(list(api_keys))
    genai.configure(api_key=key)
    
    # Sadece çalışan modelleri dene (1.5 SİLİNDİ)
    priority_models = ['gemini-2.5-flash', 'gemini-2.0-flash']
    
    selected_model = None
    for m_name in priority_models:
        try:
            model = genai.GenerativeModel(m_name)
            # Bağlantı testi yapmadan direkt isteği gönderiyoruz (Hız için)
            selected_model = model
            break 
        except: continue

    if not selected_model:
        st.error("Bağlantı kurulamadı. (Lütfen API Keylerinizi kontrol edin)")
        return None

    config = {
        "temperature": 0.8,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json"
    }
    
    try:
        response = selected_model.generate_content(prompt_history, generation_config=config)
        return json.loads(clean_json(response.text))
    except Exception as e:
        return None

# --- 7. STATE YÖNETİMİ ---
if "game_started" not in st.session_state: st.session_state.game_started = False
if "history" not in st.session_state: st.session_state.history = []
if "stats" not in st.session_state: 
    st.session_state.stats = {"money": 100000, "team": 50, "motivation": 50, "debt": 0, "monthly_pay": 0}
if "player" not in st.session_state: st.session_state.player = {}
if "month" not in st.session_state: st.session_state.month = 1
if "game_over" not in st.session_state: st.session_state.game_over = False
if "selected_mode" not in st.session_state: st.session_state.selected_mode = "Gerçekçi"
if "last_chance_card" not in st.session_state: st.session_state.last_chance_card = None
if "custom_traits_list" not in st.session_state: st.session_state.custom_traits_list = []

# --- 8. SENARYO MOTORU ---
def run_turn(user_input):
    mode = st.session_state.selected_mode
    player = st.session_state.player
    stats = st.session_state.stats
    
    chance_card = trigger_chance_card()
    chance_text = ""
    if chance_card:
        st.session_state.last_chance_card = chance_card
        if chance_card['effect'] == 'money': stats['money'] += chance_card['val']
        elif chance_card['effect'] == 'team': stats['team'] += chance_card['val']
        elif chance_card['effect'] == 'motivation': stats['motivation'] += chance_card['val']
        chance_text = f"\n\n🃏 **ŞANS KARTI:** {chance_card['title']}\n_{chance_card['desc']}_"

    traits_text = ""
    for t in player.get('custom_traits', []):
        traits_text += f"- [{t['title']}]: {t['desc']}\n"

    char_desc = f"""
    OYUNCU: {player.get('name')} ({player.get('gender')})
    YETENEKLER: Yazılım:{player['stats']['coding']}, Pazarlama:{player['stats']['marketing']}, Network:{player['stats']['network']}, Disiplin:{player['stats']['discipline']}, Karizma:{player['stats']['charisma']}.
    ÖZEL YETENEKLER: {traits_text}
    """

    system_prompt = f"""
    Sen 'Startup Survivor' oyunusun. Mod: {mode}.
    {char_desc}
    FİNANS: Kasa:{stats['money']} TL, Borç:{stats['debt']} TL, Gider:{stats['monthly_pay']} TL
    {chance_text}
    
    GÖREV:
    1. Hamleyi ve yetenekleri yorumla.
    2. Finansal hesabı yap.
    3. Kasa<0 veya Ekip/Motivasyon<0 ise BİTİR.
    4. Yeni olay kurgula.
    
    ÇIKTI (JSON):
    {{
        "text": "Hikaye... {chance_text} \n\n🔥 DURUM: ... \n\nNe yapacaksın?\n\n**A) ...**\n...\n\n**B) ...**\n...",
        "month": {st.session_state.month + 1},
        "stats": {{ "money": (int), "team": (int), "motivation": (int), "debt": (int), "monthly_pay": (int) }},
        "game_over": false, "game_over_reason": ""
    }}
    """
    
    chat_history = [{"role": "user", "parts": [system_prompt]}]
    for msg in st.session_state.history: chat_history.append(msg)
    chat_history.append({"role": "user", "parts": [user_input]})

    return get_ai_response(chat_history)

# --- 9. ARAYÜZ (GÜNCELLENDİ) ---
apply_custom_css(st.session_state.selected_mode)

# === LOBBY (GİRİŞ EKRANI) ===
if not st.session_state.game_started:
    st.markdown('<div class="hero-container"><h1 class="hero-title">Startup Survivor RPG</h1><div class="hero-subtitle">Kendi karakterini yarat, hayalindeki şirketi kur ve krizlere meydan oku.</div></div>', unsafe_allow_html=True)
    
    # --- AYARLAR MENÜSÜ (GİZLENEBİLİR EXPANDER) ---
    with st.expander("🛠️ Karakterini ve Ayarları Özelleştir (Tıkla)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            p_name = st.text_input("Adın", "İsimsiz Kahraman")
            p_gender = st.selectbox("Cinsiyet", ["Erkek", "Kadın", "Belirtmek İstemiyorum"])
            p_mode = st.selectbox("Mod Seç", ["Gerçekçi", "Türkiye Simülasyonu", "Zor", "Extreme", "Spartan"])
            st.session_state.selected_mode = p_mode
        with c2:
            start_money = st.number_input("Kasa (TL)", 1000, 1000000, 100000, step=10000)
            start_loan = st.number_input("Kredi (TL)", 0, 1000000, 0, step=10000)
        
        st.divider()
        st.write("🧠 **Yetenek Puanları (0-10)**")
        c3, c4 = st.columns(2)
        with c3:
            s_coding = st.slider("💻 Yazılım", 0, 10, 5)
            s_marketing = st.slider("📢 Pazarlama", 0, 10, 5)
            s_network = st.slider("🤝 Network", 0, 10, 5)
        with c4:
            s_discipline = st.slider("⏱️ Disiplin", 0, 10, 5)
            s_charisma = st.slider("✨ Karizma", 0, 10, 5)
            
        st.write("✨ **Özel Özellik Ekle**")
        ca1, ca2, ca3 = st.columns([2,2,1])
        with ca1: nt_title = st.text_input("Özellik Adı", placeholder="Örn: Uykusuz")
        with ca2: nt_desc = st.text_input("Açıklama", placeholder="Günde 4 saat uyur")
        with ca3: 
            if st.button("Ekle"):
                if nt_title: st.session_state.custom_traits_list.append({"title": nt_title, "desc": nt_desc})
        
        for t in st.session_state.custom_traits_list:
            st.caption(f"🔸 **{t['title']}**: {t['desc']}")

    # --- SOHBET BAŞLANGIÇ ---
    st.info("👇 Oyuna başlamak için aşağıdaki kutuya fikrini yaz ve Enter'a bas.")
    startup_idea = st.chat_input("Girişim fikrin ne? (Örn: Yapay zeka destekli kedi maması...)")
    
    if startup_idea:
        # Değişken atamaları (Expander açılmasa bile çalışsın diye)
        if 'p_name' not in locals(): p_name = "İsimsiz Kahraman"
        if 'p_gender' not in locals(): p_gender = "Belirtmek İstemiyorum"
        if 's_coding' not in locals(): s_coding, s_marketing, s_network, s_discipline, s_charisma = 5, 5, 5, 5, 5
        if 'start_money' not in locals(): start_money = 100000
        if 'start_loan' not in locals(): start_loan = 0
        if 'p_mode' not in locals(): p_mode = "Gerçekçi"
        
        st.session_state.player = {
            "name": p_name, "gender": p_gender,
            "stats": {"coding": s_coding, "marketing": s_marketing, "network": s_network, "discipline": s_discipline, "charisma": s_charisma},
            "custom_traits": st.session_state.custom_traits_list
        }
        st.session_state.stats = {
            "money": start_money + start_loan,
            "team": 50, "motivation": 50, "debt": start_loan, 
            "monthly_pay": (start_loan * 0.05) + (5000 if start_money < 50000 else 15000)
        }
        st.session_state.selected_mode = p_mode
        st.session_state.game_started = True
        
        st.session_state.history.append({"role": "user", "parts": [f"Girişim Fikrim: {startup_idea}"]})
        
        with st.spinner("Simülasyon başlatılıyor..."):
            resp = run_turn(f"Oyun başlasın. Fikrim: {startup_idea}")
            if resp:
                st.session_state.history.append({"role": "model", "parts": [json.dumps(resp)]})
                st.session_state.stats = resp["stats"]
                st.session_state.month = resp["month"]
                st.rerun()

# === OYUN EKRANI ===
elif not st.session_state.game_over:
    
    with st.sidebar:
        st.header(f"👤 {st.session_state.player['name']}")
        st.progress(min(st.session_state.month / 12.0, 1.0), text=f"Ay: {st.session_state.month}/12")
        st.divider()
        st.metric("💵 Kasa", format_currency(st.session_state.stats['money']), delta=f"-{format_currency(st.session_state.stats['monthly_pay'])} Gider", delta_color="inverse")
        if st.session_state.stats['debt'] > 0: st.warning(f"🏦 Borç: {format_currency(st.session_state.stats['debt'])}")
        st.divider()
        st.write(f"👥 Ekip: %{st.session_state.stats['team']}")
        st.progress(st.session_state.stats['team'] / 100)
        st.write(f"🔥 Motivasyon: %{st.session_state.stats['motivation']}")
        st.progress(st.session_state.stats['motivation'] / 100)
        
        if st.session_state.player['custom_traits']:
            with st.expander("✨ Yeteneklerin"):
                for t in st.session_state.player['custom_traits']:
                    st.markdown(f"""<div class="trait-card"><b>{t['title']}</b><br>{t['desc']}</div>""", unsafe_allow_html=True)

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
        st.success("🎉 TEBRİKLER! BAŞARILI EXIT!")
        if st.button("Yeni Kariyer"):
            st.session_state.clear()
            st.rerun()
    else:
        user_move = st.chat_input("Kararın nedir?")
        if user_move:
            with st.chat_message("user"): st.write(user_move)
            st.session_state.history.append({"role": "user", "parts": [user_move]})
            with st.spinner("Hesaplanıyor..."):
                response = run_turn(user_move)
                if response:
                    st.session_state.history.append({"role": "model", "parts": [json.dumps(response)]})
                    st.session_state.stats = response["stats"]
                    st.session_state.month = response["month"]
                    if response.get("game_over"):
                        st.session_state.game_over = True
                        st.session_state.game_over_reason = response.get("game_over_reason")
                    st.rerun()

else:
    st.error(f"💀 OYUN BİTTİ: {st.session_state.game_over_reason}")
    if st.button("Tekrar Dene"):
        st.session_state.clear()
        st.rerun()