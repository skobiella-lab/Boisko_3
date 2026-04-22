# app.py

import os
import sys

# Inteligentne ustawienie ścieżki głównej (Root Path)
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(current_dir, 'turf_advisor')):
    # Jeśli app.py jest w roocie, dodaj bieżący folder
    sys.path.insert(0, current_dir)
else:
    # Jeśli app.py jest wewnątrz turf_advisor, dodaj folder nadrzędny
    sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '..')))

import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image

from turf_advisor.database.db_manager import DatabaseManager
from turf_advisor.engines.nutrition import NutritionEngine
from turf_advisor.engines.hydrology import HydrologyEngine
from turf_advisor.engines.biology import BiologyEngine
from turf_advisor.probabilistic.risk_models import RiskEngine
from turf_advisor.probabilistic.monte_carlo import MonteCarloEngine
from turf_advisor.config import ENABLE_PROBABILISTIC, WEATHER_API_KEY
from turf_advisor.integrations.meteo_api import MeteoEngine
from turf_advisor.utils import geocode_address

def display_weather_charts(df):
    """Pomocnik do renderowania spójnych wykresów pogodowych."""
    if df is None or df.empty:
        st.warning("Brak danych pogodowych do wyświetlenia na wykresach.")
        return

    available_columns = df.columns.tolist()
    c1, c2 = st.columns(2)
    with c1:
        y_axis = [col for col in ['temp_avg', 'et_calculated'] if col in available_columns]
        if 'date' in available_columns and y_axis:
            st.line_chart(df, x='date', y=y_axis)
        else:
            st.info("Brak danych o temperaturze lub ET.")
    with c2:
        if 'date' in available_columns and 'precip_mm' in available_columns:
            st.bar_chart(df, x='date', y='precip_mm')
        else:
            st.info("Brak danych o opadach.")

# Inicjalizacja bazy i silników
db = DatabaseManager()
risk_engine = RiskEngine()

def get_cached_soil_data(field_id):
    """Pobiera dane glebowe z cache."""
    return db.get_latest_soil_analysis(field_id)

# Debug: Wyłączam cache tymczasowo dla pogody
def get_cached_weather_history(days=30):
    """Pobiera historię pogody bez cache (debug)."""
    data = db.get_weather_history(days=days)
    print(f'>>> DEBUG: get_cached_weather_history({days}) zwrócił {len(data) if data else 0} rekordów')
    return data

def get_weather_forecast():
    """Pobiera prognozę pogody bez cache (debug)."""
    data = db.get_weather_forecast()
    print(f'>>> DEBUG: get_weather_forecast() zwrócił {len(data) if data else 0} rekordów')
    return data

st.set_page_config(page_title="Turf Advisor Pro", layout="wide")

st.title("🌱 Turf Advisor: System Wspomagania Decyzji")

# --- SIDEBAR: Konfiguracja i Szybki Rekord ---
st.sidebar.header("Zarządzanie Boiskiem")
field_id = st.sidebar.selectbox("Wybierz boisko", [1], format_func=lambda x: f"Boisko Główne (ID: {x})")

st.sidebar.subheader("📍 Lokalizacja Boiska")

# Inicjalizacja współrzędnych w session_state jeśli nie istnieją
if 'lat' not in st.session_state:
    st.session_state.lat = 52.23
if 'lon' not in st.session_state:
    st.session_state.lon = 21.01
if 'city' not in st.session_state:
    st.session_state.city = "Moje Boisko"

# Pole adresu do geokodowania
address_input = st.sidebar.text_input(
    "Wprowadź adres lub miejscowość",
    placeholder="np. Warszawa, Aleje Jerozolimskie 10"
)

if st.sidebar.button("🔍 Znajdź współrzędne"):
    if address_input.strip():
        with st.sidebar.spinner("Szukam lokalizacji..."):
            location = geocode_address(address_input.strip())
            if location:
                st.session_state.lat = location['lat']
                st.session_state.lon = location['lon']
                st.session_state.city = location['display_name'][:50]  # Ogranicz długość
                st.sidebar.success(f"Znaleziono: {location['display_name'][:50]}...")
                st.rerun()
            else:
                st.sidebar.error("Nie znaleziono lokalizacji. Spróbuj inny adres.")
    else:
        st.sidebar.warning("Wprowadź adres!")

# Wyświetlanie i edycja współrzędnych
city = st.sidebar.text_input("Nazwa lokalizacji", value=st.session_state.city)
lat = st.sidebar.number_input("Szerokość (Lat)", value=st.session_state.lat, format="%.6f")
lon = st.sidebar.number_input("Długość (Lon)", value=st.session_state.lon, format="%.6f")

# Aktualizuj session_state jeśli użytkownik zmienił wartości ręcznie
st.session_state.city = city
st.session_state.lat = lat
st.session_state.lon = lon

# app.py -> w sekcji Sidebar

st.sidebar.divider()
st.sidebar.subheader("🔑 Klucz API Pogody")
# System najpierw szuka klucza w config, jeśli nie ma - prosi o wpisanie
api_key_input = st.sidebar.text_input("Klucz Visual Crossing", value=WEATHER_API_KEY, type="password")

# Suwak do wyboru liczby dni historii pogody
weather_days = st.sidebar.slider(
    "Dni historii pogody",
    min_value=7,
    max_value=30,
    value=7,
    step=1,
    help="Wybierz liczbę dni wstecz dla wyświetlania danych pogodowych"
)

# Suwak do wyboru liczby dni prognozy pogody
forecast_days = st.sidebar.slider(
    "Dni prognozy pogody",
    min_value=1,
    max_value=14,
    value=7,
    step=1,
    help="Wybierz liczbę dni do przodu dla prognozy pogody"
)

if st.sidebar.button("Pobierz dane i przelicz modele"):
    if api_key_input:
        meteo = MeteoEngine(lat, lon, api_key=api_key_input)
        if meteo.update_weather_data(forecast_days=forecast_days):
            st.sidebar.success("Dane pobrane pomyślnie!")
            st.rerun()
        else:
            st.sidebar.error("Błąd API. Sprawdź klucz lub koordynaty.")
    else:
        st.sidebar.warning("Wpisz klucz API!")

# turf_advisor/app.py (sekcja Sidebar)
st.sidebar.divider()
st.sidebar.subheader("🔄 Opcja Alternatywna (Bez API Key)")

# app.py (fragment w sidebarze)
# app.py (fragment)
if st.sidebar.button("Pobierz z Open-Meteo"):
    # Upewnij się, że używasz nazw zmiennych z Twoich pól input (lat, lon)
    meteo = MeteoEngine(lat, lon)
    if meteo.update_weather_data(forecast_days=forecast_days):
        st.sidebar.success("Pogoda zaktualizowana!")
        st.rerun()
    else:
        st.sidebar.error("Błąd połączenia z Open-Meteo.")

if st.sidebar.button("Pobierz historię z Open-Meteo"):
    meteo = MeteoEngine(lat, lon)
    if meteo.update_historical_weather(days_back=30):
        st.sidebar.success("Historia pogodowa pobrana!")
        st.rerun()
    else:
        st.sidebar.error("Błąd pobierania historii.")

if st.sidebar.button("TEST BAZY (Wymuś dane)"):
    conn = db.get_connection()
    conn.execute("INSERT OR REPLACE INTO weather_history (date, temp_max, temp_min, temp_avg, precip_mm, humidity, et_calculated, is_forecast) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (datetime.now().strftime('%Y-%m-%d'), 22.0, 15.0, 18.5, 2.0, 70.0, 3.5, 0))
    conn.commit()
    st.sidebar.success("Testowy wpis dodany! Odśwież stronę.")


st.sidebar.subheader("⚡ Szybki Rekord Zabiegu")
action = st.sidebar.selectbox("Typ zabiegu", ["KOSZENIE", "PODLEWANIE", "NAWOZENIE"])

product_name = None
if action == "NAWOZENIE":
    if 'fertilizer_db' in st.session_state:
        fert_list = st.session_state.fertilizer_db['Nazwa'].tolist()
        product_name = st.sidebar.selectbox("Wybierz nawóz", fert_list)
    else:
        product_name = st.sidebar.text_input("Nazwa nawozu")
    amount = st.sidebar.number_input("Dawka (kg/ha)", min_value=0.0, value=25.0, step=5.0)
else:
    amount = st.sidebar.number_input("Ilość (mm lub inne)", min_value=0.0)

if st.sidebar.button("Zapisz zabieg"):
    db.add_maintenance_record(field_id, action, amount, product_id=product_name)
    st.sidebar.success("Zabieg zarejestrowany!")

# --- INICJALIZACJA DANYCH ---
latest_soil = None
static_profile = {
    'bulk_density': 1.55,
    'om_pct': 2.5,
    'cn_ratio': 12,
    'root_depth_mm': 150,
    'sand_pct': 90.0,
    'silt_pct': 5.0,
    'clay_pct': 5.0
}

try:
    latest_soil = db.get_latest_soil_analysis(field_id)
except Exception as e:
    st.error(f"Błąd połączenia z bazą: {e}")

# --- GŁÓWNY PANEL ZAKŁADEK ---
tab_dashboard, tab_weather, tab_soil, tab_ferts, tab_journal, tab_vision, tab_risk = st.tabs([
    "🏠 Dashboard Operacyjny",
    "🌦️ Pogoda i Prognoza",
    "🧪 Laboratorium (Mehlich-3)",
    "🌿 Baza Nawozów",
    "📋 Dziennik Zabiegów",
    "👁️ Analiza Wizyjna",
    "🎲 Modele Ryzyka"
])

# --- ZAKŁADKA 1: DASHBOARD ---
# app.py -> wewnątrz with tab_dashboard:

with tab_dashboard:
    st.info("ℹ️ **Uwaga:** Modele fizyczne w tym panelu (stabilność, napowietrzenie) zakładają warunki izolowane (np. zadaszenie). Wpływ pogody i opadów jest uwzględniany w dedykowanych zakładkach Ryzyka i Pogody.")
    st.subheader(f"📍 Lokalizacja Boiska: {city}")

    # 1. POBIERANIE ŚWIEŻYCH DANYCH Z BAZY
    # Pobieramy dane tutaj, aby system reagował na zmiany w zakładce Laboratorium
    current_soil = get_cached_soil_data(field_id)

    if current_soil:
        # --- INICJALIZACJA SILNIKÓW (Wszystkie wewnątrz bloku if) ---
        nut_engine = NutritionEngine(current_soil, static_profile)
        hydro_engine = HydrologyEngine(static_profile, None)
        bio_eng = BiologyEngine(static_profile) # Definicja bio_eng dla col3

        # Obliczanie bilansów
        balance = nut_engine.get_full_balance()
        vmc_sim = 0.18  # Aktualna wilgotność (symulacja)

        # --- GÓRNE WSKAŹNIKI (KPI) ---
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("##### 📊 Zasobność (Mehlich-3)")
            st.caption("🔬 **Model:** Mehlich-3 - Analiza chemiczna gleby")
            # Wyświetlamy kluczowe pierwiastki z Twoich notatek
            for nut in ['P', 'K', 'Mg']:
                val = balance[nut]['current']
                diff = balance[nut]['diff_mg_kg']
                st.metric(
                    label=f"Potencjał {nut}",
                    value=f"{val} mg/kg",
                    delta=f"{diff} vs MLSN",
                    delta_color="normal" if diff >= 0 else "inverse"
                )
            # Poziom pH
            ph = current_soil.get('ph_h2o', 6.5) or 6.5
            # Interpretacja pH dla trawy
            if ph < 5.5:
                ph_status = "Zbyt kwaśna"
                ph_color = "🔴"
            elif ph < 6.0:
                ph_status = "Kwaśna"
                ph_color = "🟠"
            elif ph <= 7.0:
                ph_status = "Optymalna"
                ph_color = "🟢"
            else:
                ph_status = "Zasadowa"
                ph_color = "🟡"
            st.metric(
                label="Poziom pH (H2O)",
                value=f"{ph}",
                delta=f"{ph_color} {ph_status}",
                delta_color="off"
            )

            with st.expander("🧪 Mikroelementy", expanded=False):
                micros_data = nut_engine.get_micros_status()
                for name, info in micros_data.items():
                    icon = "✅" if info['status'] == "OK" else "⚠️"
                    st.write(f"{icon} **{name}**: {info['value']} mg/kg")

        with col2:
            st.markdown("##### 💧 Status Hydrologiczny")
            st.caption("🌊 **Model:** Fizyka Richardsa - Transport wody w glebie")
            air_status = hydro_engine.air_filled_porosity(vmc_sim)
            st.metric("Wilgotność VMC", f"{vmc_sim*100}%", "Optymalna")
            st.write(f"**Napowietrzenie:** {air_status['air_pct']}% ({air_status['status']})")
            st.write(f"**Profil:** {static_profile['sand_pct']}% piasku (USGA)")

        with col3:
            st.markdown("##### 📈 Ryzyko i Predykcja")
            st.caption("🦠 **Model:** GDD + Modele Ryzyka - Biologia i epidemiologia")

            # Dynamiczne obliczenia na podstawie dzisiejszej pogody
            weather_now = get_cached_weather_history(days=1)
            t_avg_today = 18.0
            if weather_now:
                day = weather_now[0]
                t_avg_today = day.get('temp_avg', 18.0)
                gdd_today = bio_eng.calculate_gdd(day.get('temp_max', 22), day.get('temp_min', 14))
                st.write(f"**GDD (dzisiaj):** {gdd_today}")
                
                # Model Potencjału Wzrostu (GP)
                gp = bio_eng.growth_potential_pace(t_avg_today)
                st.write(f"**Potencjał wzrostu (GP):** {round(gp*100, 1)}%")

            # Obliczanie stabilności przez zdefiniowany wyżej bio_eng
            shear = bio_eng.shear_strength_model(vmc_sim)
            # Polskie nazwy statusów stabilności
            status_pl = {
                'EXCELLENT': '🟢 DOSKONAŁA',
                'SOFT': '🟡 MIĘKKA',
                'UNSTABLE': '🔴 NIESTABILNA'
            }
            status_desc = status_pl.get(shear['status'], shear['status'])
            st.write(f"**Stabilność:** {status_desc} ({shear['kpa']} kPa)")

            # Model Smith-Kerns (przykładowe dane historyczne)
            risk_prob = risk_engine.smith_kerns_dollar_spot([18, 20, 19], [85, 90, 88])
            st.progress(risk_prob)
            # Polska nazwa: "Plamistość dolara" 
            st.write(f"**Ryzyko Plamistości dolara:** {int(risk_prob*100)}%")

            n_min = bio_eng.calculate_n_mineralization(t_avg_today, vmc_sim)
            st.write(f"**Mineralizacja N:** {n_min} kg/ha/dobę")
            st.caption("📚 *Plamistość dolara* – choroba grzybowa trawy (okrągłe plamki)")

        with col4:
            st.markdown("##### 🧪 Status Azotowy")
            st.caption("🌱 **Model:** Metoda Ogrodnicza - Dostępność bieżąca")
            # Obliczanie dostępnego azotu (NO3 + NH4)
            n_no3 = current_soil.get('hort_n_no3', 0) or 0
            n_nh4 = current_soil.get('hort_n_nh4', 0) or 0
            total_n = n_no3 + n_nh4
            # Cel dla trawy: 10-20 mg/dm³ (około 15-30 mg/kg przy gęstości 1.5)
            target_n = 15.0  # mg/dm³
            diff_n = total_n - target_n
            st.metric(
                label="Azot dostępny (NO3+NH4)",
                value=f"{total_n} mg/dm³",
                delta=f"{diff_n:.1f} vs cel (15 mg/dm³)",
                delta_color="normal" if diff_n >= 0 else "inverse"
            )
            # Potencjał organiczny
            organic_n = nut_engine.get_organic_nitrogen_potential()
            if isinstance(organic_n, str):
                st.write(f"**Potencjał organiczny:** {organic_n}")
            else:
                st.write(f"**Mineralizacja org.:** {organic_n} kg N/ha/rok")
            
            # Integracja silnika uwalniania azotu (Model 14) - Poprawiono formę z 'nh2' na 'urea'
            n_release_urea = nut_engine.nitrogen_release_model(0, t_avg_today, form='nh2')
            n_release_nh4 = nut_engine.nitrogen_release_model(0, t_avg_today, form='nh4')
            st.write(f"**Dostępność N-Mocznik:** {round(n_release_urea*100, 1)}%/d")
            st.caption(f"Temp. gleby rzutuje na uwalnianie form NH4: {round(n_release_nh4*100,1)}%/d")

        # --- SEKCOJA WSKAZÓWEK I HARMONOGRAMU ---
        st.divider()
        st.subheader("📅 Harmonogram Zabiegów i Wskazówki")

        # Podsumowanie modeli używanych w systemie
        with st.expander("🔍 **Modele decyzyjne w systemie**", expanded=False):
            st.markdown("""
            **🌱 Turf Advisor** wykorzystuje następujące modele matematyczne:

            - **🔬 Mehlich-3**: Chemiczna ekstrakcja składników odżywczych z gleby
            - **🌊 Fizyka Richardsa**: Model transportu wody i wilgotności w glebie  
            - **🌡️ GDD (Grade Day Degrees)**: Akumulacja ciepła dla decyzji o koszeniu
            - **🦠 Modele epidemiologiczne**: Przewidywanie ryzyka chorób (Smith-Kerns)
            - **🌦️ Penman-Monteith**: Obliczenia ewapotranspiracji (ET0)
            - **📊 Van Genuchten**: Krzywe retencji wody w glebie
            """)

        # Generowanie opisowych wskazówek na podstawie bilansu Mehlich-3
        tips = []
        if balance['K']['status'] == 'DEFICIT':
            tips.append(f"⚠️ **Potas (K):** Poziom {balance['K']['current']} mg/kg jest zbyt niski. Zaplanuj nawożenie.")
        if balance['Mg']['status'] == 'DEFICIT':
            tips.append(f"⚠️ **Magnez (Mg):** Deficyt ({balance['Mg']['current']} mg/kg).")
        
        # Analiza mikroelementów
        micros_status = nut_engine.get_micros_status()
        for name, info in micros_status.items():
            if info['status'] == 'DEFICIT':
                tips.append(f"⚠️ **{name}:** Deficyt ({info['value']} mg/kg). Cel: {info['target']} mg/kg.")
        
        # Dodanie warningów dla azotu
        n_no3 = current_soil.get('hort_n_no3', 0) or 0
        n_nh4 = current_soil.get('hort_n_nh4', 0) or 0
        total_n = n_no3 + n_nh4
        if total_n < 10:
            tips.append(f"⚠️ **Azot (N):** Poziom {total_n} mg/dm³ jest niski. Wymagane nawożenie azotem!")
        elif total_n < 15:
            tips.append(f"⚠️ **Azot (N):** Poziom {total_n} mg/dm³ jest poniżej celu. Rozważ nawożenie.")

        if tips:
            for tip in tips:
                st.warning(tip)
        else:
            st.success("✅ Parametry glebowe są zgodne z normami MLSN.")

        # --- SŁOWNIK MLSN I OPISY PARAMETRÓW ---
        st.divider()
        col_mlsn1, col_mlsn2 = st.columns(2)
        
        with col_mlsn1:
            st.markdown("##### 📖 Co to jest MLSN?")
            st.markdown("""
            **MLSN** = *Minimum Levels for Sustainable Nutrition*
            
            To **minimalne poziomy składników** potrzebne do:
            - ✅ Utrzymania zdrowia i wzrostu murawy
            - ✅ Zapewnienia trwałości systemu
            - ✅ Unikania deficytów i nadmierów
            
            Wartości MLSN różnią się dla każdego pierwiastka i są oparte na badaniach agronomicznych.
            """)
        
        with col_mlsn2:
            st.markdown("##### 🎯 Cele MLSN dla tego boiska:")
            mlsn_targets = {
                "Fosfor (P)": "21 mg/kg",
                "Potas (K)": "37 mg/kg",
                "Magnez (Mg)": "47 mg/kg",
                "Wapń (Ca)": "331 mg/kg",
                "Siarka (S)": "7 mg/kg"
            }
            for nut, target in mlsn_targets.items():
                st.write(f"• **{nut}**: {target}")
        
        # Opisy parametrów zostały przeniesione do zakładki Laboratorium.
        
        # Tabela harmonogramu z oznaczeniami modeli
        st.markdown("##### 📋 Harmonogram zabiegów z modelami decyzyjnymi")
        schedule_data = {
            "Dzień": ["Poniedziałek", "Czwartek", "Sobota"],
            "Zabieg": ["Koszenie (28mm)", "Podlewanie (30mm)", "Nawożenie K+Mg+N"],
            "Model decyzyjny": ["GDD (Stopnie dnia)", "Fizyka Richardsa (Transport wody)", "Mehlich-3 + Metoda Ogrodnicza"],
            "Status": ["✅ OK", "💧 Niedostateczna", f"{'⚠️ Deficyt' if total_n < 15 else '✅ OK'}"],
            "Parametry wejściowe": ["Temperatura powietrza", "Wilgotność gleby, opady", "Zasobność K, Mg, N w glebie"]
        }
        st.table(pd.DataFrame(schedule_data))

    else:
        # Komunikat, gdy baza jest pusta
        st.warning("⚠️ Brak danych glebowych. Przejdź do zakładki 'Laboratorium', wprowadź wyniki i kliknij Zapisz.")
    
    st.download_button("📩 Eksportuj Raport", "Dane...", file_name="Raport_Turf.pdf")


# --- ZAKŁADKA: POGODA ---
with tab_weather:
    st.subheader(f"🌦️ System Monitoringu Pogodowego")
    
    cw1, cw2, cw3 = st.columns([0.4, 0.4, 0.2])
    # Pobieramy dane zgodnie z wyborem użytkownika na suwaku w sidebarze
    weather_history = get_cached_weather_history(days=weather_days)
    
    with cw1:
        st.info(f"📍 **Lokalizacja:** {city} | Szer: {lat}, Dł: {lon}")
    with cw2:
        if weather_history:
            df_h = pd.DataFrame(weather_history)
            # Bilans wodny wyliczamy zawsze dla ostatnich 7 dni dla spójności wskaźnika
            df_recent = df_h.head(7)
            rain_sum = df_recent['precip_mm'].sum() if 'precip_mm' in df_recent.columns else 0
            et_sum = df_recent['et_calculated'].sum() if 'et_calculated' in df_recent.columns else 0
            balance_w = rain_sum - et_sum
            
            st.metric("7-dniowy Bilans Wodny", f"{balance_w:.1f} mm", 
                      delta="Nadmiar" if balance_w > 0 else "Deficyt",
                      delta_color="normal" if balance_w > 0 else "inverse")
        else:
            st.info("Brak danych do bilansu.")
            
    with cw3:
        if st.button("🔄 Odśwież Dane", key="tab_weather_global_refresh"):
            st.cache_data.clear()
            st.rerun()

    if weather_history:
        st.markdown(f"#### 📅 Historia (Ostatnie {weather_days} dni)")
        display_weather_charts(pd.DataFrame(weather_history))
    else:
        st.warning("Brak danych historycznych. Skorzystaj z panelu bocznego, aby pobrać historię.")

    st.divider()

    # Prognoza
    st.markdown(f"#### 🔮 Prognoza (Następne {forecast_days} dni)")
    weather_forecast = get_weather_forecast()
    if weather_forecast:
        today = datetime.now().date()
        future_f = [d for d in weather_forecast if datetime.strptime(d['date'], '%Y-%m-%d').date() >= today][:forecast_days]
        if future_f:
            df_f = pd.DataFrame(future_f)
            display_weather_charts(df_f)
            
            with st.expander("📋 Szczegółowe zestawienie prognozy", expanded=True):
                f_view = df_f[['date', 'temp_min', 'temp_max', 'temp_avg', 'precip_mm']].copy()
                f_view['date'] = pd.to_datetime(f_view['date']).dt.strftime('%d.%m.%Y')
                f_view.columns = ['Data', 'Min (°C)', 'Max (°C)', 'Średnia (°C)', 'Opad (mm)']
                st.dataframe(f_view, use_container_width=True)
        else: st.info("Brak aktualnej prognozy w bazie.")
    else: st.info("Brak danych prognozy.")

# --- ZAKŁADKA 2: LABORATORIUM ---
with tab_soil:
    st.subheader("🧪 Formularz Wyników Badań Glebowych")
    st.markdown("Wprowadź dane z raportu laboratoryjnego (Mehlich-3 oraz Metoda Ogrodnicza).")

    with st.form("soil_input_form"):
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("**Podstawowe i pH**")
            ph_h2o = st.number_input("pH (w H2O)", value=6.5, step=0.1)
            ph_hcl = st.number_input("pH (w KCl/HCl)", value=5.8, step=0.1)
            ec = st.number_input("Zasolenie EC (dS/m)", value=0.1, format="%.3f")
            
            st.markdown("**Metoda Ogrodnicza (mg/dm³)**")
            h_no3 = st.number_input("N-NO3", value=10.0)
            h_nh4 = st.number_input("N-NH4", value=2.0)
            h_p = st.number_input("P (Hort)", value=40.0)
            h_k = st.number_input("K (Hort)", value=120.0)

        with c2:
            st.markdown("**Mehlich-3 - Makro (mg/kg)**")
            m3_p = st.number_input("P (M3)", value=30.0)
            m3_k = st.number_input("K (M3)", value=50.0)
            m3_mg = st.number_input("Mg (M3)", value=60.0)
            m3_ca = st.number_input("Ca (M3)", value=400.0)
            m3_s = st.number_input("S (M3)", value=10.0)

        with c3:
            st.markdown("**Mehlich-3 - Mikro (mg/kg)**")
            m3_fe = st.number_input("Fe (M3)", value=100.0)
            m3_mn = st.number_input("Mn (M3)", value=25.0)
            m3_cu = st.number_input("Cu (M3)", value=1.5)
            m3_zn = st.number_input("Zn (M3)", value=3.0)
            m3_al = st.number_input("Al (M3)", value=20.0)

        submit_soil = st.form_submit_button("💾 Zapisz wyniki w bazie")
        
        if submit_soil:
            soil_data = {
                'profile_id': field_id,
                'ph_h2o': ph_h2o, 'ph_hcl': ph_hcl, 'ec_ds_m': ec,
                'm3_p': m3_p, 'm3_k': m3_k, 'm3_mg': m3_mg, 'm3_ca': m3_ca, 'm3_s': m3_s,
                'm3_fe': m3_fe, 'm3_mn': m3_mn, 'm3_cu': m3_cu, 'm3_zn': m3_zn, 'm3_al': m3_al,
                'hort_n_no3': h_no3, 'hort_n_nh4': h_nh4, 'hort_p': h_p, 'hort_k': h_k
            }
            if db.save_soil_analysis(soil_data):
                st.success("✅ Dane zapisane! Przejdź do Dashboardu, aby zobaczyć analizę.")
                st.rerun()
    
    st.divider()
    st.markdown("### 📊 Bilans Kationów (Wysycenie Kompleksu Sorpcyjnego)")
    st.caption("Model Bilansu Kationów (K, Mg, Ca) w procentach wysycenia kompleksu sorpcyjnego.")

    if current_soil:
        nut_engine = NutritionEngine(current_soil, static_profile)
        cation_balance = nut_engine.calculate_cation_balance_saturation()

        col_cb1, col_cb2, col_cb3, col_cb4 = st.columns(4)
        with col_cb1:
            st.metric("CEC (meq/100g)", f"{cation_balance['Total_CEC_meq_100g']}")
        with col_cb2:
            st.metric("K (%)", f"{cation_balance['K_saturation_pct']}%")
            if not (3 <= cation_balance['K_saturation_pct'] <= 5):
                st.warning("K poza optymalnym zakresem (3-5%)")
        with col_cb3:
            st.metric("Mg (%)", f"{cation_balance['Mg_saturation_pct']}%")
            if not (10 <= cation_balance['Mg_saturation_pct'] <= 15):
                st.warning("Mg poza optymalnym zakresem (10-15%)")
        with col_cb4:
            st.metric("Ca (%)", f"{cation_balance['Ca_saturation_pct']}%")
            if not (65 <= cation_balance['Ca_saturation_pct'] <= 75):
                st.warning("Ca poza optymalnym zakresem (65-75%)")
        
        st.markdown("""
        **Interpretacja:**
        - **K (Potas):** Optymalnie 3-5% wysycenia.
        - **Mg (Magnez):** Optymalnie 10-15% wysycenia.
        - **Ca (Wapń):** Optymalnie 65-75% wysycenia.
        """)
    else:
        st.info("Wprowadź dane glebowe, aby obliczyć bilans kationów.")

# --- NOWA ZAKŁADKA: BAZA NAWOZÓW ---
with tab_ferts:
    st.subheader("🌿 Zarządzanie Bazą Nawozów")
    st.markdown("Edytuj składy popularnych nawozów lub dodaj własne produkty.")
    
    if 'fertilizer_db' not in st.session_state:
        default_ferts = [
            {"Nazwa": "ICL Sportsmaster Base", "N (%)": 12.0, "P (%)": 24.0, "K (%)": 0.0, "Mg (%)": 2.0, "Typ": "Startowy"},
            {"Nazwa": "ICL Sportsmaster High K", "N (%)": 15.0, "P (%)": 0.0, "K (%)": 25.0, "Mg (%)": 2.0, "Typ": "Antystresowy"},
            {"Nazwa": "ICL Sierraform GT Spring Start", "N (%)": 16.0, "P (%)": 0.0, "K (%)": 16.0, "Mg (%)": 0.0, "Typ": "Premium Micro"},
            {"Nazwa": "Compo Floranid Twin Permanent", "N (%)": 16.0, "P (%)": 7.0, "K (%)": 15.0, "Mg (%)": 2.0, "Typ": "Uniwersalny"},
            {"Nazwa": "YaraMila Complex", "N (%)": 12.0, "P (%)": 11.0, "K (%)": 18.0, "Mg (%)": 3.0, "Typ": "Bezchlorkowy"},
            {"Nazwa": "Agromaster 19-5-20", "N (%)": 19.0, "P (%)": 5.0, "K (%)": 20.0, "Mg (%)": 4.0, "Typ": "CRF (Otoczkowany)"},
            {"Nazwa": "Everris Sierrablen Plus", "N (%)": 24.0, "P (%)": 5.0, "K (%)": 8.0, "Mg (%)": 2.0, "Typ": "Długodziałający"},
            {"Nazwa": "ICL ProTurf High K", "N (%)": 12.0, "P (%)": 5.0, "K (%)": 20.0, "Mg (%)": 2.0, "Typ": "Wieloskładnikowy"},
            {"Nazwa": "YaraVera AMIDAS", "N (%)": 40.0, "P (%)": 0.0, "K (%)": 0.0, "Mg (%)": 0.0, "Typ": "Azotowy"},
            {"Nazwa": "Chelat Żelaza (Solufeed)", "N (%)": 0.0, "P (%)": 0.0, "K (%)": 0.0, "Mg (%)": 0.0, "Typ": "Interwencyjny Fe"},
            {"Nazwa": "Siarczan Magnezu", "N (%)": 0.0, "P (%)": 0.0, "K (%)": 0.0, "Mg (%)": 16.0, "Typ": "Rozpuszczalny"}
        ]
        st.session_state.fertilizer_db = pd.DataFrame(default_ferts)
    
    edited_ferts = st.data_editor(st.session_state.fertilizer_db, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Zapisz Bazę Nawozów"):
        st.session_state.fertilizer_db = edited_ferts
        st.success("Baza została zaktualizowana.")

# --- NOWA ZAKŁADKA: DZIENNIK ZABIEGÓW ---
with tab_journal:
    st.subheader("📋 Dziennik Zabiegów")
    records = db.get_maintenance_records(field_id)
    if records:
        df_journal = pd.DataFrame(records)
        edited_journal = st.data_editor(df_journal, num_rows="dynamic", use_container_width=True)
        if st.button("🔄 Aktualizuj Historię"):
            # Tutaj można dodać logikę synchronizacji z DB
            st.success("Dziennik zaktualizowany.")
    else:
        st.info("Brak wpisów w dzienniku.")

# --- ZAKŁADKA: WIZJA ---
with tab_vision:
    st.subheader("👁️ Diagnostyka Wizyjna i Spektralna")

    with st.expander("🔍 **Modele decyzyjne w analizie wizyjnej**", expanded=False):
        st.markdown("""
        **Moduł wizyjny** wykorzystuje zaawansowane przetwarzanie obrazu do nieinwazyjnej oceny stanu murawy:

        - **📸 Model DGCI (Dark Green Color Index)**: Konwertuje wartości RGB na przestrzeń HSB (Hue, Saturation, Brightness). 
          Pozwala na obiektywną ocenę koloru i pośrednią estymację zawartości azotu w liściach, eliminując błąd subiektywnej oceny ludzkiej.
        
        - **🛰️ Model NDVI (Normalized Difference Vegetation Index)**: Analizuje stosunek odbicia światła w paśmie czerwonym i bliskiej podczerwieni. 
          Wykrywa stres biotyczny i abiotyczny na 3-5 dni przed pojawieniem się objawów widocznych w świetle dziennym.
        """)

    v_col1, v_col2 = st.columns([0.6, 0.4])
    
    with v_col1:
        st.markdown("#### 📸 Analiza RGB")
        analysis_mode = st.radio("Tryb analizy", ["Pojedyncze zdjęcie", "Porównanie (Przed / Po)"], horizontal=True)

        if analysis_mode == "Pojedyncze zdjęcie":
            uploaded_file = st.file_uploader("Wgraj zdjęcie", type=['png', 'jpg', 'jpeg'], key="single_img")
            if uploaded_file:
                img = Image.open(uploaded_file)
                st.image(img, caption="Podgląd", use_container_width=True)
                # Symulacja wyniku (w rzeczywistości wywołanie color_analysis.py)
                dgci_score = 0.75
                st.metric("Indeks DGCI", f"{dgci_score}", "Prawidłowy")
                st.progress(0.75)
        else:
            c_before, c_after = st.columns(2)
            dgci_before, dgci_after = None, None
            
            with c_before:
                st.caption("📷 Zdjęcie PRZED")
                file_before = st.file_uploader("Wgraj obraz", type=['png', 'jpg', 'jpeg'], key="img_before")
                if file_before:
                    st.image(Image.open(file_before), use_container_width=True)
                    dgci_before = 0.65  # Symulacja wyniku z silnika wizyjnego
            
            with c_after:
                st.caption("📸 Zdjęcie PO")
                file_after = st.file_uploader("Wgraj obraz", type=['png', 'jpg', 'jpeg'], key="img_after")
                if file_after:
                    st.image(Image.open(file_after), use_container_width=True)
                    dgci_after = 0.82  # Symulacja wyniku z silnika wizyjnego
            
            if dgci_before and dgci_after:
                st.divider()
                diff = dgci_after - dgci_before
                res_col1, res_col2, res_col3 = st.columns(3)
                res_col1.metric("DGCI Przed", f"{dgci_before}")
                res_col2.metric("DGCI Po", f"{dgci_after}")
                res_col3.metric("Zmiana (Delta)", f"{diff:+.2f}", delta=f"{diff*100:+.1f}%")
                
                if diff > 0.05:
                    st.success(f"🚀 Wykryto poprawę kondycji o {round(diff*100, 1)}%. Zabieg przyniósł oczekiwane rezultaty.")
                elif diff < -0.05:
                    st.error(f"⚠️ Wykryto spadek indeksu DGCI o {round(abs(diff*100), 1)}%. Sprawdź czynniki stresogenne.")
            
    with v_col2:
        st.markdown("#### 🛰️ NDVI i Spektrometria")
        st.button("Pobierz dane Sentinel-2")
        st.button("Połącz z kamerą Sentera")
        with st.expander("Legenda NDVI"):
            st.markdown("""
            **NDVI (Znormalizowany Wskaźnik Wegetacji):**
            - **0.7 - 0.9 (Ciemnozielony)**: Maksymalny wigor, gęsta darń.
            - **0.4 - 0.6 (Żółty/Jasnozielony)**: Początek stresu abiotycznego lub braki N.
            - **< 0.3 (Czerwony)**: Uszkodzenia mechaniczne lub chorobowe.
            
            *Wskazówka: NDVI pozwala wykryć stres roślin na 3-5 dni przed tym, jak stanie się on widoczny w świetle widzialnym (RGB).*
            """)

# --- ZAKŁADKA 4: RYZYKO ---
with tab_risk:
    st.subheader("🎲 Modele Ryzyka i Nawożenie")

    st.info("ℹ️ **Zintegrowany System Decyzyjny:** Ten panel łączy predykcje pogodowe z biologią patogenów i fizyką gleby.")

    with st.expander("🔍 **Modele decyzyjne i korelacje**", expanded=False):
        st.markdown("""
        **Logika doboru nawożenia:**
        1. **Smith-Kerns (Choroby):** Jeśli ryzyko infekcji przekracza 40%, silnik rekomendacji automatycznie ogranicza dawkę azotu (N) szybkodziałającego, sugerując przejście na potas (K) dla wzmocnienia ścian komórkowych.
        2. **Monte Carlo (Wypłukiwanie):** Analizuje strukturę gleby (USGA) i prognozowane ulewy. Jeśli ryzyko strat N jest wysokie, system preferuje nawozy otoczkowane (CRF).
        3. **MLSN (Deficyty):** Silnik `NutritionEngine` oblicza 'lukę' w kg/ha, którą musimy wypełnić mieszanką z magazynu.
        4. **GP (Growth Potential):** Sprawdza, czy temperatura pozwala na pobranie składników. Jeśli GP < 20%, nawożenie doglebowe jest wstrzymywane.
        """)

    # --- RYZYKO CHOROBOWE ---
    st.markdown("### 🦠 Ryzyko Plamistości Dolara (Smith-Kerns)")
    risk_col1, risk_col2 = st.columns(2)
    
    with risk_col1:
        weather_history = get_cached_weather_history(days=5)
        if weather_history:
            df_hist = pd.DataFrame(weather_history)
            temps = df_hist['temp_avg'].tolist()
            humids = df_hist['humidity'].tolist()
            risk_prob = risk_engine.smith_kerns_dollar_spot(temps, humids)
            
            if risk_prob < 0.3:
                status = "🟢 NISKIE"
            elif risk_prob < 0.6:
                status = "🟡 ŚREDNIE"
            else:
                status = "🔴 WYSOKIE"
            
            st.metric("Ryzyko Plamistości", f"{int(risk_prob*100)}%", status)
            
            if risk_prob > 0.5:
                st.warning("⚠️ Ryzyko wysokie! Rozważ fungicyd.")
            elif risk_prob > 0.3:
                st.info("💡 Ryzyko średnie. Monitoruj.")
            else:
                st.success("✅ Ryzyko niskie.")
        else:
            st.warning("Brak danych pogodowych.")
    
    with risk_col2:
        st.markdown("**Trend (ostatnie 5 dni)**")
        if weather_history and len(weather_history) >= 2:
            df_hist = pd.DataFrame(weather_history)
            trend_data = []
            for i, row in df_hist.iterrows():
                risk = risk_engine.smith_kerns_dollar_spot([row['temp_avg']], [row['humidity']])
                trend_data.append({'Data': row['date'], 'Ryzyko': risk*100})
            st.line_chart(pd.DataFrame(trend_data).set_index('Data'))
    
    st.divider()
    
    # --- MONTE CARLO ---
    st.markdown("### 🔬 Symulacja Utraty Azotu (Monte Carlo)")
    if ENABLE_PROBABILISTIC and current_soil:
        n_no3 = current_soil.get('hort_n_no3', 0) or 0
        n_nh4 = current_soil.get('hort_n_nh4', 0) or 0
        total_n = n_no3 + n_nh4
        
        if total_n > 0:
            forecast_data = db.get_weather_forecast()
            if forecast_data:
                df_forecast = pd.DataFrame(forecast_data[:7])
                avg_precip = df_forecast['precip_mm'].mean()
                
                col_mc1, col_mc2 = st.columns(2)
                with col_mc1:
                    forecast_input = st.slider("Prognoza opadów (mm)", 0.0, 50.0, avg_precip, 1.0)
                with col_mc2:
                    iterations = st.slider("Symulacje", 100, 5000, 1000, 100)
                
                mc_engine = MonteCarloEngine(total_n, static_profile)
                sim_result = mc_engine.simulate_nitrogen_leaching(forecast_input, iterations)
                
                col_res1, col_res2, col_res3 = st.columns(3)
                with col_res1:
                    st.metric("Średnia utrata N", f"{sim_result['avg_loss_kg']} kg/ha")
                with col_res2:
                    st.metric("CI 5%", f"{sim_result['confidence_interval'][0]:.2f} kg/ha")
                with col_res3:
                    st.metric("CI 95%", f"{sim_result['confidence_interval'][1]:.2f} kg/ha")
                
                if sim_result['risk_level'] == "HIGH":
                    st.error("🔴 Ryzyko WYSOKIE: Rozważ ochronę.")
                else:
                    st.success("🟢 Ryzyko NISKIE: Straty w normie.")
            else:
                st.warning("Brak prognozy. Pobierz z Open-Meteo.")
        else:
            st.warning("Azot = 0. Wprowadź w Laboratorium.")
    else:
        st.info("💡 Włącz ENABLE_PROBABILISTIC w config.py")
    
    st.divider()
    
    # --- AUTOMATYCZNY KONFIGURATOR NAWOŻENIA ---
    st.markdown("### 🌾 Automatyczny Konfigurator Nawożenia (Silnik MLSN)")
    st.caption("System automatycznie analizuje deficyty i dobiera najlepszy produkt z Twojego magazynu.")

    with st.expander("🔍 **Model decyzyjny nawożenia mineralnego**", expanded=False):
        st.markdown("""
        **Algorytm Optymalizacji Magazynowej (MLSN-Optimizer):**
        - Porównuje bieżące wyniki Mehlich-3 z progami MLSN (Minimum Levels for Sustainable Nutrition).
        - Priorytetyzuje kationy (K, Mg, Ca) w oparciu o procent wysycenia kompleksu sorpcyjnego (BCSR).
        - Automatycznie dobiera produkt z magazynu, który najlepiej niweluje największy deficyt przy bezpiecznym ładunku azotu.
        """)

    if current_soil:
        # Pobranie danych o bilansie kationów do logiki optymalizacji
        nut_engine = NutritionEngine(current_soil, static_profile)
        cation_balance = nut_engine.calculate_cation_balance_saturation()
        cec = cation_balance['Total_CEC_meq_100g']

        col_nav1, col_nav2 = st.columns(2)
        
        with col_nav1:
            st.markdown("**🔍 Wykryte Luki Składników:**")
            deficit_table = []
            total_deficit = 0
            needs_dict = {}
            
            for nut in ['P', 'K', 'Mg', 'Ca', 'S']:
                if nut in balance:
                    current = balance[nut]['current']
                    target = balance[nut]['target']
                    need = balance[nut]['need_kg_ha']
                    status = balance[nut]['status']
                    
                    if status == 'DEFICIT':
                        needs_dict[nut] = need
                        total_deficit += need

                    deficit_table.append({
                        'Pierwiastek': nut,
                        'Bieżący': f"{current} mg/kg",
                        'Cel': f"{target} mg/kg",
                        'Status': '🔴 BRAK' if status == 'DEFICIT' else '🟢 OK',
                        'Potrzeba': f"{need} kg/ha"
                    })
            
            # Wyświetlenie statusu wysycenia w konfiguratorze
            st.markdown("**⚖️ Status Wysycenia Kompleksu (BCSR):**")
            c_cols = st.columns(3)
            with c_cols[0]:
                st.write(f"K: {cation_balance['K_saturation_pct']}%")
                if cation_balance['K_saturation_pct'] < 3: st.caption("🔴 Za niskie")
            with c_cols[1]:
                st.write(f"Mg: {cation_balance['Mg_saturation_pct']}%")
                if cation_balance['Mg_saturation_pct'] < 10: st.caption("🔴 Za niskie")
            with c_cols[2]:
                st.write(f"Ca: {cation_balance['Ca_saturation_pct']}%")
                if cation_balance['Ca_saturation_pct'] < 65: st.caption("🔴 Za niskie")
            
            if deficit_table:
                st.dataframe(pd.DataFrame(deficit_table), use_container_width=True)
            else:
                st.success("Brak krytycznych deficytów makroelementów.")
        
        with col_nav2:
            st.markdown("**📦 Dostępne Środki (Magazyn):**")
            
            inventory = st.multiselect(
                "Wybierz produkty do kalkulacji:",
                st.session_state.fertilizer_db['Nazwa'].tolist(),
                default=[st.session_state.fertilizer_db['Nazwa'].iloc[0]] if not st.session_state.fertilizer_db.empty else None
            )

        # Wynik konfiguratora
        if total_deficit > 0 and inventory:
            st.markdown("---")
            st.markdown("#### 🧮 Rekomendacja Optymalizacji")
            
            available_ferts = st.session_state.fertilizer_db[st.session_state.fertilizer_db['Nazwa'].isin(inventory)]
            
            # Inteligentny wybór priorytetu:
            # Jeśli wysycenie kationami (BCSR) jest krytycznie niskie, traktuj to jako priorytet przed MLSN
            priority_nut = None
            if cation_balance['K_saturation_pct'] < 2.5: priority_nut = 'K'
            elif cation_balance['Mg_saturation_pct'] < 8.0: priority_nut = 'Mg'
            elif cation_balance['Ca_saturation_pct'] < 60.0: priority_nut = 'Ca'

            # Wybór głównego składnika do korekty
            if needs_dict:
                main_nutrient = priority_nut if (priority_nut and priority_nut in needs_dict) else max(needs_dict, key=needs_dict.get)
                best_fert = available_ferts.sort_values(by=f"{main_nutrient} (%)", ascending=False).iloc[0]
                
                target_need = needs_dict[main_nutrient]
                if best_fert[f"{main_nutrient} (%)"] > 0:
                    dose = target_need / (best_fert[f"{main_nutrient} (%)"] / 100)
                    n_load = dose * (best_fert['N (%)'] / 100)
                    
                    res_c1, res_c2 = st.columns(2)
                    with res_c1:
                        st.success(f"**Zalecany nawóz:** {best_fert['Nazwa']}")
                        st.metric("Dawka na hektar", f"{round(dose, 1)} kg/ha")
                    
                    with res_c2:
                        st.write(f"**Pokrycie deficytu {main_nutrient}:** 100%")
                        st.write(f"**Ładunek Azotu (N):** {round(n_load, 1)} kg/ha")
                        
                        if priority_nut:
                            st.info(f"💡 Rekomendacja zorientowana na szybką korektę wysycenia {priority_nut} w kompleksie sorpcyjnym.")
                    
                    if n_load > 30:
                        st.warning(f"⚠️ **Ostrzeżenie:** Wysoka dawka azotu. Przy obecnym ryzyku chorób (Smith-Kerns) zalecana aplikacja dzielona.")
                else:
                    st.error(f"Brak produktu w wybranym magazynie zawierającego: {main_nutrient}")
        elif total_deficit == 0:
            st.success("✅ Wszystkie parametry MLSN są w normie. Nie wymagane jest dodatkowe nawożenie mineralne.")

    else:
        st.warning("⚠️ Brak danych glebowych. Przejdź do Laboratorium.")
