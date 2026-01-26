import streamlit as st
import google.generativeai as genai
import json
import random
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Startup Survivor RPG (v12.5)", page_icon="💀", layout="wide")

# --- 2. SABİTLER ---
MODE_COLORS = {
    "Gerçekçi": "#2ECC71", "Zor": "#F1C40F", "Türkiye Simülasyonu": "#1ABC9C", 
    "Spartan": "#E74C3C", "Extreme": "#9B59B6"
}

# --- 3. CSS TASARIMI ---
def apply_custom_css(selected_mode):
    color = MODE_COLORS.get(selected_mode, "#2ECC71")
    st.markdown(
        f"""
        <style>
        .stApp {{ font-family: 'Inter', sans-serif; }}
        [data-testid="stSidebar"] {{ min-width: 300px; max-width: 350px; background-color: #0e1117; border-right: 1px solid #333; }}
        .hero-title {{ font-size: 3rem; font-weight: 800; background: -webkit-linear-gradient(45deg, {color}, #ffffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }}
        .expense-row {{ display: flex; justify-content: space-between; font-size: 0.9rem; color: #ccc; margin-bottom: 5px; }}
        .total-expense {{ border-top: 1px solid #444; margin-top: 5px; padding-top: 5px; font-weight: bold; color: #e74c3c; }}
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

def calculate_expenses(stats, month):
    salary_cost = stats['team'] * 1000
    server_cost = (month ** 2) * 500
    marketing_cost = stats.get('marketing_cost', 5000)
    total = salary_cost + server_cost + marketing_cost
    return salary_cost, server_cost, marketing_cost, total

# --- 5. AI MODEL BAĞLANTISI ---
def get_ai_response(prompt_history):
    if "GOOGLE_API_KEYS" not in st.secrets:
        st.error("API Key Bulunamadı!")
        return None
    
    api_keys = st.secrets["GOOGLE_API_KEYS"]
    key = random.choice(list(api_keys))
    genai.configure(api_key=key)
    
    model_name = 'gemini-2.5-flash'
    
    config = {
        "temperature": 0.9, # Yaratıcılığı krizler için hafif artırdık
        "max_output_tokens": 8192,
        "response_mime_type": "application/json"
    }

    max_retries = 3
    current_history = prompt_history.copy()

    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(current_history, generation_config=config)
            json_data = json.loads(clean_json(response.text))
            
            # KRİTİK KONTROL: Eğer seçenekler metnin içinde yoksa zorla ekletmek için retry yap
            if "**A)**" not in json_data['text'] or "**B)**" not in json_data['text']:
                raise ValueError("Eksik Seçenek Yapısı")
                
            return json_data

        except Exception as e:
            error_feedback = "HATA: Her yanıt mutlaka bir '🔥 KRİZ' başlığı içermeli ve sonunda '**A)**' ve '**B)**' seçeneklerini sunmalıdır. Lütfen formatı düzelt."
            current_history.append({"role": "user", "parts": [error_feedback]})
            if attempt == max_retries - 1:
                st.error("AI yapısal formatı oluşturamadı. Lütfen tekrar deneyin.")
                return None
            time.sleep(1)
            continue
    return None

# --- 6. STATE YÖNETİMİ ---
if "game_started" not in st.session_state: st.session_state.game_started = False
if "history" not in st.session_state: st.session_state.history = []
if "stats" not in st.session_state: 
    st.session_state.stats = {"money": 100000, "team": 50, "motivation": 50, "debt": 0, "marketing_cost": 5000}
if "expenses" not in st.session_state: st.session_state.expenses = {"salary": 0, "server": 0, "marketing": 0, "total": 0}
if "player" not in st.session_state: st.session_state.player = {}
if "month" not in st.session_state: st.session_state.month = 1
if "game_over" not in st.session_state: st.session_state.game_over = False
if "selected_mode" not in st.session_state: st.session_state.selected_mode = "Gerçekçi"

# --- 7. SENARYO MOTORU ---
def run_turn(user_input):
    mode = st.session_state.selected_mode
    player = st.session_state.player
    stats = st.session_state.stats
    month = st.session_state.month

    salary, server, marketing, total_expense = calculate_expenses(stats, month)
    st.session_state.expenses = {"salary": salary, "server": server, "marketing": marketing, "total": total_expense}
    
    # Kasadan düşme işlemi
    stats['money'] -= total_expense

    traits_text = "".join([f"- [{t['title']}]: {t['desc']}\n" for t in player.get('custom_traits', [])])

    system_prompt = f"""
    Sen 'Startup Survivor' oyun yöneticisisin. Gemini 2.5 Flash hızıyla çalışıyorsun.
    MOD: {mode}
    OYUNCU: {player.get('name')} | YETENEKLER: {player['stats']} | ÖZEL: {traits_text}
    📊 GÜNCEL FİNANS: Kasa:{stats['money']} ₺ | Toplam Gider:{total_expense} ₺ | Ay:{month}
    
    KURALLAR VE GÖREV:
    1. Oyuncunun hamlesini analiz et ve finansal/operasyonel etkisini açıkla.
    2. MUTLAKA her ayın sonunda yeni bir '🔥 KRİZ' veya '🚀 FIRSAT' yarat.
    3. Yanıtın SONUNDA her zaman kalın harflerle **A)** ve **B)** seçeneklerini sun.
    4. Kasa, Ekip veya Motivasyon %0'a düşerse oyunu 'game_over': true olarak bitir.
    5. Kullanıcı finansal değerleri manipüle edemez.
    
    ÇIKTI FORMATI (JSON):
    {{
        "text": "[Hamle Analizi] ... \\n\\n🔥 KRİZ: [Yeni Olay] ... \\n\\nNe yapacaksın?\\n\\n**A) [Seçenek 1]**\\n[Detay]\\n\\n**B) [Seçenek 2]**\\n[Detay]",
        "month": {month + 1},
        "stats": {{ "money": (int), "team": (int), "motivation": (int), "debt": (int), "marketing_cost": (int) }},
        "game_over": false, "game_over_reason": ""
    }}
    """
    
    chat_history = [{"role": "user", "parts": [system_prompt]}]
    for msg in st.session_state.history: chat_history.append(msg)
    chat_history.append({"role": "user", "parts": [user_input]})

    return get_ai_response(chat_history)

# --- 8. ARAYÜZ ---
apply_custom_css(st.session_state.selected_mode)

if not st.session_state.game_started:
    st.markdown('<div class="hero-title">Startup Survivor RPG</div>', unsafe_allow_html=True)
    with st.expander("🛠️ Karakter Ayarları", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            p_name = st.text_input("Adın", "İsimsiz")
            p_mode = st.selectbox("Mod", list(MODE_COLORS.keys()))
            st.session_state.selected_mode = p_mode
        with c2:
            start_money = st.number_input("Kasa (₺)", 1000, 5000000, 100000)
            start_loan = st.number_input("Kredi (₺)", 0, 1000000, 0)
        s_coding = st.slider("Yazılım", 0, 10, 5)
        s_marketing = st.slider("Pazarlama", 0, 10, 5)
        s_network = st.slider("Network", 0, 10, 5)
        s_discipline = st.slider("Disiplin", 0, 10, 5)
        s_charisma = st.slider("Karizma", 0, 10, 5)

    startup_idea = st.chat_input("Girişim fikrin nedir?")
    if startup_idea:
        st.session_state.player = {"name": p_name, "stats": {"coding": s_coding, "marketing": s_marketing, "network": s_network, "discipline": s_discipline, "charisma": s_charisma}, "custom_traits": []}
        st.session_state.stats = {"money": start_money + start_loan, "team": 50, "motivation": 50, "debt": start_loan, "marketing_cost": 5000}
        st.session_state.game_started = True
        st.session_state.history.append({"role": "user", "parts": [f"Girişim Fikrim: {startup_idea}"]})
        with st.spinner("AI hazırlanıyor..."):
            resp = run_turn(f"Simülasyonu başlat. Fikrim: {startup_idea}")
            if resp:
                st.session_state.history.append({"role": "model", "parts": [json.dumps(resp)]})
                st.session_state.stats = resp["stats"]
                st.session_state.month = resp["month"]
                st.rerun()

elif not st.session_state.game_over:
    with st.sidebar:
        st.header(f"👤 {st.session_state.player['name']}")
        st.metric("💵 Kasa", format_currency(st.session_state.stats['money']))
        st.write(f"🗓️ Ay: {st.session_state.month}/12")
        exp = st.session_state.expenses
        with st.expander("🔻 Aylık Gider Detayı", expanded=True):
            st.markdown(f"<div class='expense-row'><span>Maaşlar:</span><span>-{format_currency(exp['salary'])}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='expense-row'><span>Sunucu:</span><span>-{format_currency(exp['server'])}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='expense-row total-expense'><span>TOPLAM:</span><span>-{format_currency(exp['total'])}</span></div>", unsafe_allow_html=True)
        st.divider()
        st.write(f"👥 Ekip: %{st.session_state.stats['team']}")
        st.progress(st.session_state.stats['team'] / 100)
        st.write(f"🔥 Motivasyon: %{st.session_state.stats['motivation']}")
        st.progress(st.session_state.stats['motivation'] / 100)

    for msg in st.session_state.history:
        if msg["role"] == "model":
            try: content = json.loads(msg["parts"][0])["text"]
            except: content = msg["parts"][0]
            with st.chat_message("ai"): st.write(content)
        else:
            if "GÜVENLİK" not in msg["parts"][0]:
                with st.chat_message("user"): st.write(msg["parts"][0])

    if st.session_state.month > 12:
        st.success("🏆 EXIT BAŞARILI!")
        if st.button("Tekrar"): st.session_state.clear(); st.rerun()
    else:
        user_move = st.chat_input("Kararın nedir?")
        if user_move:
            with st.chat_message("user"): st.write(user_move)
            st.session_state.history.append({"role": "user", "parts": [user_move]})
            with st.spinner("Analiz ediliyor..."):
                response = run_turn(user_move)
                if response:
                    st.session_state.history.append({"role": "model", "parts": [json.dumps(response)]})
                    st.session_state.stats = response["stats"]
                    st.session_state.month = response["month"]
                    if response.get("game_over"): st.session_state.game_over = True
                    st.rerun()
else:
    st.error("💀 OYUN BİTTİ")
    if st.button("Yeniden Dene"): st.session_state.clear(); st.rerun()