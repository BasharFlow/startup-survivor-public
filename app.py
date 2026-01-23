import streamlit as st
import google.generativeai as genai
import json
import random
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Startup Survivor RPG", page_icon="💀", layout="wide")

# --- 2. AYARLAR & SABİTLER ---
MODE_COLORS = {
    "Gerçekçi": "#2ECC71",  # Yeşil
    "Zor": "#F1C40F",       # Sarı
    "Türkiye Simülasyonu": "#1ABC9C", # Turkuaz
    "Spartan": "#E74C3C",   # Kırmızı
    "Extreme": "#9B59B6"    # Mor
}

# --- 3. CSS TASARIMI ---
def apply_custom_css(selected_mode):
    color = MODE_COLORS.get(selected_mode, "#2ECC71")
    st.markdown(
        f"""
        <style>
        .stApp {{ font-family: 'Inter', sans-serif; }}
        [data-testid="stSidebar"] {{ 
            min-width: 280px; 
            max-width: 320px; 
            background-color: #1a1b21; 
            border-right: 1px solid #333; 
        }}
        .hero-title {{
            font-size: 3rem; font-weight: 800;
            background: -webkit-linear-gradient(45deg, {color}, #ffffff);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 0px; text-align: center;
        }}
        .trait-card {{
            background-color: #262730; padding: 10px; border-radius: 8px;
            border-left: 3px solid {color}; margin-bottom: 5px;
        }}
        .trait-title {{ font-weight: bold; color: #fff; }}
        .trait-desc {{ font-size: 0.9rem; color: #ccc; font-style: italic; }}
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
            {"title": "📉 Vergi Affı!", "desc": "Devlet bu ayki vergileri ve bazı borçları sildi.", "effect": "money", "val": 25000},
            {"title": "⛈️ Ofisi Su Bastı", "desc": "Tesisat patladı, bilgisayarlar zarar gördü.", "effect": "money", "val": -15000},
            {"title": "👋 Toksik Çalışan İstifası", "desc": "Ekibi zehirleyen o kişi işten çıktı! Yerine hevesli bir stajyer geldi.", "effect": "motivation", "val": 15},
            {"title": "🚀 Viral Oldunuz", "desc": "Bir influencer ürününüzü paylaştı.", "effect": "money", "val": 50000},
            {"title": "📜 Mevzuat Değişikliği", "desc": "Bürokratik bir engel işleri yavaşlattı.", "effect": "motivation", "val": -10},
        ]
        if st.session_state.selected_mode == "Türkiye Simülasyonu":
            cards.append({"title": "💸 Kira Zammı", "desc": "Ofis sahibi 'Oğlum Almanya'dan gelecek' diyip kirayı 3 katına çıkardı.", "effect": "money", "val": -30000})
            cards.append({"title": "🍲 Yemek Kartı Krizi", "desc": "Yemek kartları yatmayınca yazılımcılar isyan etti.", "effect": "team", "val": -15})
            
        selected_card = random.choice(cards)
        return selected_card
    return None

# --- 6. AI MODEL BAĞLANTISI (GÜNCELLENDİ: 1.5 FLASH SİLİNDİ) ---
def get_ai_response(prompt_history):
    if "GOOGLE_API_KEYS" not in st.secrets:
        st.error("HATA: Secrets dosyasında API Key bulunamadı!")
        return None
    
    # API Keyleri karıştır ki yük dağılsın
    api_keys = st.secrets["GOOGLE_API_KEYS"]
    shuffled_keys = list(api_keys)
    random.shuffle(shuffled_keys)
    
    # --- YENİ MODEL LİSTESİ (2.0 ÖNCELİKLİ) ---
    priority_models = [
        'gemini-2.0-flash',       # En yeni ve hızlı
        'gemini-2.0-flash-exp',   # Deneysel sürüm (Genelde açıktır)
        'gemini-1.5-pro',         # Stabil ve zeki
        'gemini-1.5-pro-latest'   # Yedek
    ]

    selected_model = None
    active_key = None

    # Doğru modeli ve çalışan anahtarı bulma döngüsü
    for key in shuffled_keys:
        genai.configure(api_key=key)
        for m_name in priority_models:
            try:
                model = genai.GenerativeModel(m_name)
                # Ufak bir bağlantı testi
                model.generate_content("Test", request_options={"timeout": 2})
                selected_model = model
                active_key = key
                break # Model çalıştı, döngüden çık
            except:
                continue # Bu model bu anahtarda çalışmadı, sıradakine bak
        
        if selected_model: break # Çalışan ikili bulunduysa ana döngüden çık

    if not selected_model:
        st.error("Hiçbir model (Gemini 2.0/1.5 Pro) çalıştırılamadı. API Keylerinizi veya kotanızı kontrol edin.")
        return None

    # Üretim Ayarları
    config = {
        "temperature": 0.8,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json"
    }
    
    try:
        response = selected_model.generate_content(prompt_history, generation_config=config)
        return json.loads(clean_json(response.text))
    except Exception as e:
        st.error(f"Yapay Zeka Hatası: {e}")
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
    OYUNCU PROFİLİ:
    - İsim: {player.get('name')} ({player.get('gender')})
    - Yetenekler (0-10): Yazılım: {player['stats']['coding']}, Pazarlama: {player['stats']['marketing']}, 
      Network: {player['stats']['network']}, Disiplin: {player['stats']['discipline']}, 
      Karizma: {player['stats']['charisma']}.
    - ÖZEL YETENEKLER:\n{traits_text}
    """

    system_prompt = f"""
    Sen 'Startup Survivor' oyunusun. Mod: {mode}.
    {char_desc}
    
    FİNANSAL DURUM:
    - Kasa: {stats['money']} TL
    - Toplam Borç: {stats['debt']} TL
    - Aylık Gider: {stats['monthly_pay']} TL
    
    {chance_text}
    
    GÖREVLERİN:
    1. Oyuncunun hamlesini, yeteneklerini ve ÖZEL YETENEKLERİNİ dikkate alarak yorumla.
    2. Finansal hesaplamayı yap.
    3. Kasa < 0 veya Ekip/Motivasyon < 0 ise BİTİR.
    4. Yeni kriz/fırsat sun.
    
    ÇIKTI (JSON):
    {{
        "text": "Hikaye... {chance_text} \n\n🔥 DURUM: ... \n\nNe yapacaksın?\n\n**A) ...**\n...\n\n**B) ...**\n...",
        "month": {st.session_state.month + 1},
        "stats": {{
            "money": (yeni kasa), "team": (0-100), "motivation": (0-100),
            "debt": (kalan borç), "monthly_pay": (yeni gider)
        }},
        "game_over": false, "game_over_reason": ""
    }}
    """
    
    chat_history = [{"role": "user", "parts": [system_prompt]}]
    for msg in st.session_state.history: chat_history.append(msg)
    chat_history.append({"role": "user", "parts": [user_input]})

    return get_ai_response(chat_history)

# --- 9. ARAYÜZ ---
apply_custom_css(st.session_state.selected_mode)

# === BÖLÜM 1: KARAKTER YARATMA (LOBBY) ===
if not st.session_state.game_started:
    st.markdown('<div class="hero-title">Startup Survivor RPG</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#888;'>Karakterini yarat, özelliklerini seç ve maceraya başla.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("### 🎭 Kimlik")
        p_name = st.text_input("Girişimci Adı", "İsimsiz Kahraman")
        p_gender = st.selectbox("Cinsiyet", ["Erkek", "Kadın", "Belirtmek İstemiyorum"])
        p_mode = st.selectbox("Oyun Modu", ["Gerçekçi", "Türkiye Simülasyonu", "Zor", "Extreme", "Spartan"])
        st.session_state.selected_mode = p_mode
        
    with col2:
        st.markdown("### 🏦 Sermaye")
        c_1, c_2 = st.columns(2)
        with c_1: start_money = st.number_input("Başlangıç Kasası (TL)", 1000, 1000000, 100000, step=10000)
        with c_2: start_loan = st.number_input("Çekilen Kredi (TL)", 0, 1000000, 0, step=10000)

    st.divider()

    customize_on = st.toggle("🛠️ Karakteri Detaylı Kişiselleştir (Yetenekler & Özellikler)")
    
    s_coding, s_marketing, s_network, s_discipline, s_charisma = 5, 5, 5, 5, 5
    
    if customize_on:
        st.info("Karakterinin güçlü ve zayıf yönlerini belirle.")
        c_stat1, c_stat2 = st.columns(2)
        with c_stat1:
            s_coding = st.slider("💻 Yazılım / Teknik", 0, 10, 5)
            s_marketing = st.slider("📢 Pazarlama / Satış", 0, 10, 5)
            s_network = st.slider("🤝 Network (Dayı Faktörü)", 0, 10, 5)
        with c_stat2:
            s_discipline = st.slider("⏱️ Disiplin / Yönetim", 0, 10, 5)
            s_charisma = st.slider("✨ Karizma (Tip & Ses)", 0, 10, 5)
            
        st.markdown("### ✨ Özel Yetenek Ekle (Max 5)")
        with st.container(border=True):
            col_add1, col_add2 = st.columns([1, 2])
            with col_add1:
                new_trait_title = st.text_input("Özellik Başlığı (Örn: Uykusuz)")
            with col_add2:
                new_trait_desc = st.text_input("Açıklama (Örn: Az uyur çok çalışır)")
            
            if st.button("➕ Özellik Ekle"):
                if len(st.session_state.custom_traits_list) < 5:
                    if new_trait_title and new_trait_desc:
                        st.session_state.custom_traits_list.append({"title": new_trait_title, "desc": new_trait_desc})
                        st.success(f"'{new_trait_title}' eklendi!")
                    else:
                        st.warning("Başlık ve açıklama boş olamaz.")
                else:
                    st.error("En fazla 5 özellik ekleyebilirsin.")

        if st.session_state.custom_traits_list:
            st.write("📜 **Eklenen Özellikler:**")
            for t in st.session_state.custom_traits_list:
                st.markdown(f"""
                <div class="trait-card">
                    <span class="trait-title">{t['title']}</span><br>
                    <span class="trait-desc">{t['desc']}</span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.caption("ℹ️ Standart 'Ortalama İnsan' profiliyle başlanacak (Tüm yetenekler 5/10).")

    st.divider()

    if st.button("🚀 ŞİRKETİ KUR VE BAŞLA", type="primary", use_container_width=True):
        st.session_state.player = {
            "name": p_name, "gender": p_gender,
            "stats": {
                "coding": s_coding, "marketing": s_marketing, "network": s_network,
                "discipline": s_discipline, "charisma": s_charisma
            },
            "custom_traits": st.session_state.custom_traits_list
        }
        st.session_state.stats = {
            "money": start_money + start_loan,
            "team": 50, "motivation": 50,
            "debt": start_loan,
            "monthly_pay": (start_loan * 0.05) + (5000 if start_money < 50000 else 15000) 
        }
        
        st.session_state.game_started = True
        
        intro_prompt = f"Oyun başlıyor. Girişimim henüz belli değil, ilk sorunda bana sor."
        with st.spinner("Karakterin yeteneklerine göre dünya oluşturuluyor..."):
            resp = run_turn(intro_prompt)
            if resp:
                st.session_state.history.append({"role": "model", "parts": [json.dumps(resp)]})
                st.session_state.stats = resp["stats"]
                st.session_state.month = resp["month"]
                st.rerun()

# === BÖLÜM 2: OYUN EKRANI ===
elif not st.session_state.game_over:
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.player['name']}")
        st.progress(min(st.session_state.month / 12.0, 1.0), text=f"🗓️ Ay: {st.session_state.month}/12")
        st.divider()
        st.metric("💵 Kasa", format_currency(st.session_state.stats['money']))
        st.caption(f"🔻 Aylık Gider: -{format_currency(st.session_state.stats['monthly_pay'])}")
        if st.session_state.stats['debt'] > 0: st.warning(f"🏦 Borç: {format_currency(st.session_state.stats['debt'])}")
        st.divider()
        st.write(f"👥 Ekip: %{st.session_state.stats['team']}")
        st.progress(st.session_state.stats['team'] / 100)
        st.write(f"🔥 Motivasyon: %{st.session_state.stats['motivation']}")
        st.progress(st.session_state.stats['motivation'] / 100)
        
        if st.session_state.player['custom_traits']:
            with st.expander("✨ Yeteneklerin"):
                for t in st.session_state.player['custom_traits']:
                    st.caption(f"**{t['title']}**: {t['desc'][:30]}...")

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