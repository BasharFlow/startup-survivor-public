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

# --- 3. CSS TASARIMI (PREMIUM) ---
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
        .stat-box {{
            background-color: #262730; padding: 10px; border-radius: 8px;
            border: 1px solid #444; margin-bottom: 10px; text-align: center;
        }}
        .delta-pos {{ color: #2ecc71; font-size: 0.8rem; font-weight: bold; }}
        .delta-neg {{ color: #e74c3c; font-size: 0.8rem; font-weight: bold; }}
        .chance-card {{
            background-color: #2c3e50; border: 2px solid {color};
            padding: 20px; border-radius: 15px; margin: 20px 0;
            animation: fadeIn 1s;
        }}
        @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
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
    # %20 ihtimalle şans kartı çıkar
    if random.random() < 0.20:
        cards = [
            {"title": "📉 Vergi Affı!", "desc": "Devlet bu ayki vergileri ve bazı borçları sildi.", "effect": "money", "val": 25000},
            {"title": "⛈️ Ofisi Su Bastı", "desc": "Tesisat patladı, bilgisayarlar zarar gördü.", "effect": "money", "val": -15000},
            {"title": "👋 Toksik Çalışan İstifası", "desc": "Ekibi zehirleyen o kişi işten çıktı! Yerine hevesli bir stajyer geldi.", "effect": "motivation", "val": 15},
            {"title": "🚀 Viral Oldunuz", "desc": "Bir influencer ürününüzü paylaştı.", "effect": "money", "val": 50000},
            {"title": "📜 Mevzuat Değişikliği", "desc": "Bürokratik bir engel işleri yavaşlattı.", "effect": "motivation", "val": -10},
        ]
        
        # Türkiye Moduna Özel Kartlar
        if st.session_state.selected_mode == "Türkiye Simülasyonu":
            cards.append({"title": "💸 Kira Zammı", "desc": "Ofis sahibi 'Oğlum Almanya'dan gelecek' diyip kirayı 3 katına çıkardı.", "effect": "money", "val": -30000})
            cards.append({"title": "🍲 Yemek Kartı Krizi", "desc": "Yemek kartları yatmayınca yazılımcılar isyan etti.", "effect": "team", "val": -15})
            
        selected_card = random.choice(cards)
        return selected_card
    return None

# --- 6. AI MODEL BAĞLANTISI ---
def get_ai_response(prompt_history):
    if "GOOGLE_API_KEYS" not in st.secrets:
        st.error("API Key Bulunamadı!")
        return None
    
    api_keys = st.secrets["GOOGLE_API_KEYS"]
    key = random.choice(list(api_keys))
    genai.configure(api_key=key)
    
    # Model Önceliği
    models = ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash']
    model = None
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            model.generate_content("T", request_options={"timeout": 2})
            break
        except: continue
        
    if not model: return None

    config = {
        "temperature": 0.8,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json"
    }
    
    try:
        response = model.generate_content(prompt_history, generation_config=config)
        return json.loads(clean_json(response.text))
    except Exception as e:
        st.error(f"AI Hatası: {e}")
        return None

# --- 7. OYUN BAŞLATMA VE STATE ---
if "game_started" not in st.session_state: st.session_state.game_started = False
if "history" not in st.session_state: st.session_state.history = []
if "stats" not in st.session_state: 
    # Varsayılan değerler (Karakter yaratılınca güncellenecek)
    st.session_state.stats = {
        "money": 100000, 
        "team": 50, 
        "motivation": 50,
        "debt": 0,          # Kredi Borcu
        "monthly_pay": 0    # Aylık Sabit Gider
    }
if "player" not in st.session_state: st.session_state.player = {}
if "month" not in st.session_state: st.session_state.month = 1
if "game_over" not in st.session_state: st.session_state.game_over = False
if "selected_mode" not in st.session_state: st.session_state.selected_mode = "Gerçekçi"
if "last_chance_card" not in st.session_state: st.session_state.last_chance_card = None

# --- 8. SENARYO MOTORU ---
def run_turn(user_input):
    mode = st.session_state.selected_mode
    player = st.session_state.player
    stats = st.session_state.stats
    
    # Şans Kartı Kontrolü
    chance_card = trigger_chance_card()
    chance_text = ""
    if chance_card:
        st.session_state.last_chance_card = chance_card
        # Etkiyi uygula
        if chance_card['effect'] == 'money': stats['money'] += chance_card['val']
        elif chance_card['effect'] == 'team': stats['team'] += chance_card['val']
        elif chance_card['effect'] == 'motivation': stats['motivation'] += chance_card['val']
        
        # Sınırları koru
        stats['team'] = max(0, min(100, stats['team']))
        stats['motivation'] = max(0, min(100, stats['motivation']))
        
        chance_text = f"\n\n🃏 **ŞANS KARTI ÇEKTİN:** {chance_card['title']}\n_{chance_card['desc']}_"

    # Karakter Özellikleri Metni
    char_desc = f"""
    OYUNCU PROFİLİ:
    - İsim: {player.get('name')} ({player.get('gender')})
    - Yetenekler (0-10): Yazılım: {player['stats']['coding']}, Pazarlama: {player['stats']['marketing']}, 
      Network/Çevre: {player['stats']['network']}, Disiplin: {player['stats']['discipline']}, 
      Karizma/Tip: {player['stats']['charisma']}.
    - Özel Yetenek: {player.get('special_trait')}
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
    1. Oyuncunun hamlesini yeteneklerine göre değerlendir (Örn: Network yüksekse bürokratik krizi kolay çözsün).
    2. Finansal hesaplamayı yap (Giderleri düş, geliri ekle).
    3. Eğer Kasa < 0 veya Ekip/Motivasyon < 0 ise OYUNU BİTİR.
    4. Değilse yeni kriz/fırsat sun.
    
    ÇIKTI (JSON):
    {{
        "text": "Hikaye... {chance_text if chance_text else ''} \n\n🔥 DURUM: ... \n\nNe yapacaksın?\n\n**A) ...**\n...\n\n**B) ...**\n...",
        "month": {st.session_state.month + 1},
        "stats": {{
            "money": (yeni kasa),
            "team": (0-100),
            "motivation": (0-100),
            "debt": (kalan borç),
            "monthly_pay": (yeni aylık gider)
        }},
        "game_over": false,
        "game_over_reason": ""
    }}
    """
    
    chat_history = [{"role": "user", "parts": [system_prompt]}]
    for msg in st.session_state.history: chat_history.append(msg)
    chat_history.append({"role": "user", "parts": [user_input]})

    return get_ai_response(chat_history)

# --- 9. ARAYÜZ ---
apply_custom_css(st.session_state.selected_mode)

# === BÖLÜM 1: KARAKTER YARATMA EKRANI (LOBBY) ===
if not st.session_state.game_started:
    st.markdown('<div class="hero-title">Startup Survivor RPG</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#888;'>Kendi karakterini yarat, şirketi kur ve hayatta kal.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🎭 Kimlik")
        p_name = st.text_input("Girişimci Adı", "İsimsiz Kahraman")
        p_gender = st.selectbox("Cinsiyet", ["Erkek", "Kadın", "Belirtmek İstemiyorum"])
        p_mode = st.selectbox("Oyun Modu", ["Gerçekçi", "Türkiye Simülasyonu", "Zor", "Extreme", "Spartan"])
        st.session_state.selected_mode = p_mode
        
        st.markdown("### 🏦 Başlangıç Sermayesi")
        start_money = st.number_input("Kasa (TL)", min_value=1000, value=100000, step=10000)
        start_loan = st.number_input("Çekilen Kredi (TL)", min_value=0, value=0, step=10000)
        
    with col2:
        st.markdown("### 🧠 Yetenek Ağacı (0-10)")
        c1, c2 = st.columns(2)
        with c1:
            s_coding = st.slider("💻 Yazılım / Teknik", 0, 10, 5)
            s_marketing = st.slider("📢 Pazarlama / Satış", 0, 10, 5)
            s_network = st.slider("🤝 Network / Çevre (Dayı Faktörü)", 0, 10, 5)
        with c2:
            s_discipline = st.slider("⏱️ Disiplin / Yönetim", 0, 10, 5)
            s_charisma = st.slider("✨ Karizma (Tip & Ses)", 0, 10, 5, help="Yüksek karizma yatırımcıyı ikna eder, düşük karizma ciddiye alınmaz.")
        
        st.markdown("### ✨ Özel Yetenek (Trait)")
        special_trait = st.text_input("Örn: 'Uykusuz Kodlar', 'Eski Bankacı', 'Zengin Aile Çocuğu'...", "Azimli")
        
        if st.button("🚀 ŞİRKETİ KUR VE BAŞLA", use_container_width=True):
            # Karakteri Kaydet
            st.session_state.player = {
                "name": p_name, "gender": p_gender, "special_trait": special_trait,
                "stats": {
                    "coding": s_coding, "marketing": s_marketing, "network": s_network,
                    "discipline": s_discipline, "charisma": s_charisma
                }
            }
            # Finansı Kaydet
            st.session_state.stats = {
                "money": start_money + start_loan,
                "team": 50, "motivation": 50,
                "debt": start_loan,
                "monthly_pay": (start_loan * 0.05) + 10000 # Basit faiz + Kira vb.
            }
            
            # İlk Hikayeyi Başlat
            st.session_state.game_started = True
            
            intro_prompt = f"Oyun başlıyor. Girişimim: {special_trait} özelliğine sahip bir {p_gender}. Fikir: Henüz belli değil, ilk senaryoda sor."
            with st.spinner("Dünya oluşturuluyor..."):
                resp = run_turn(intro_prompt)
                if resp:
                    st.session_state.history.append({"role": "model", "parts": [json.dumps(resp)]})
                    st.session_state.stats = resp["stats"]
                    st.session_state.month = resp["month"]
                    st.rerun()

# === BÖLÜM 2: OYUN EKRANI ===
elif not st.session_state.game_over:
    
    # --- SIDEBAR (DASHBOARD) ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.player['name']}")
        st.progress(min(st.session_state.month / 12.0, 1.0), text=f"🗓️ Ay: {st.session_state.month}/12")
        
        st.divider()
        
        # Finansal Tablo
        net_change = 0 # Delta hesaplama eklenebilir
        st.metric("💵 Kasa", format_currency(st.session_state.stats['money']))
        st.caption(f"🔻 Aylık Gider: -{format_currency(st.session_state.stats['monthly_pay'])}")
        
        if st.session_state.stats['debt'] > 0:
            st.warning(f"🏦 Borç: {format_currency(st.session_state.stats['debt'])}")
        
        st.divider()
        
        # Diğer Statlar
        st.write(f"👥 Ekip: %{st.session_state.stats['team']}")
        st.progress(st.session_state.stats['team'] / 100)
        
        st.write(f"🔥 Motivasyon: %{st.session_state.stats['motivation']}")
        st.progress(st.session_state.stats['motivation'] / 100)

        # Şans Kartı Gösterimi (Varsa)
        if st.session_state.last_chance_card:
            st.info(f"🃏 Son Olay: {st.session_state.last_chance_card['title']}")

    # --- CHAT ALANI ---
    for msg in st.session_state.history:
        if msg["role"] == "model":
            try: content = json.loads(msg["parts"][0])["text"]
            except: content = msg["parts"][0]
            with st.chat_message("ai"): st.write(content)
        else:
            if "Sen 'Startup Survivor'" not in msg["parts"][0]:
                with st.chat_message("user"): st.write(msg["parts"][0])
                
    # --- OYUN SONU KONTROLÜ (12 AY) ---
    if st.session_state.month > 12:
        st.balloons()
        st.success("🎉 TEBRİKLER! ŞİRKETİ BAŞARIYLA YÖNETTİNİZ.")
        
        # Yatırımcı Karnesi
        st.markdown("### 📜 Yatırımcı Çıkış Raporu")
        score = "A+" if st.session_state.stats['money'] > 1000000 else "B"
        st.code(f"""
        KURUCU: {st.session_state.player['name']}
        FİNANSAL SKOR: {score}
        EKİP BAĞLILIĞI: %{st.session_state.stats['team']}
        SONUÇ: Başarılı Exit.
        """)
        
        if st.button("Yeni Kariyer"):
            st.session_state.clear()
            st.rerun()
            
    else:
        user_move = st.chat_input("Kararın nedir?")
        if user_move:
            with st.chat_message("user"): st.write(user_move)
            st.session_state.history.append({"role": "user", "parts": [user_move]})
            
            with st.spinner("Sonuçlar hesaplanıyor..."):
                response = run_turn(user_move)
                if response:
                    st.session_state.history.append({"role": "model", "parts": [json.dumps(response)]})
                    st.session_state.stats = response["stats"]
                    st.session_state.month = response["month"]
                    
                    if response.get("game_over"):
                        st.session_state.game_over = True
                        st.session_state.game_over_reason = response.get("game_over_reason")
                    st.rerun()

# === BÖLÜM 3: GAME OVER ===
else:
    st.error(f"💀 OYUN BİTTİ: {st.session_state.game_over_reason}")
    
    # Extreme Mod ise Komik Açıklama
    if st.session_state.selected_mode == "Extreme":
        reasons = [
            "Uzaylılar teknolojinizi çalıp Mars'ta patentlediler.",
            "Yanlışlıkla zaman makinesini icat ettiniz ve dinozorlar tarafından yendiniz.",
            "Elon Musk şirketi satın almak için tweet attı ama sonra vazgeçip Dogecoin ile ödeme teklif etti."
        ]
        st.warning(f"👽 Extreme Rapor: {random.choice(reasons)}")
    else:
        # Ciddi Analiz
        st.info("💡 İpucu: Bir sonraki sefer nakit akışına (Cash Flow) daha çok dikkat et.")

    if st.button("Tekrar Dene"):
        st.session_state.clear()
        st.rerun()