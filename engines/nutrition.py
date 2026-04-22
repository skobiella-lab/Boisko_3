# turf_advisor/engines/nutrition.py

import math
from turf_advisor.config import MLSN_TARGETS, DEFAULT_BULK_DENSITY

class NutritionEngine:
    def __init__(self, soil_analysis_data, static_profile):
        self.soil_data = soil_analysis_data
        self.profile = static_profile
        self.mlsn_targets = MLSN_TARGETS

    def get_full_balance(self):
        """
        Oblicza bilans składników odżywczych w oparciu o MLSN.
        Zwraca słownik z bieżącymi wartościami, celami, potrzebami i statusami.
        """
        balance = {}
        for nutrient, target in self.mlsn_targets.items():
            current_val = self.soil_data.get(f'm3_{nutrient.lower()}', 0.0) or 0.0
            need_kg_ha = 0.0
            status = 'OK'
            diff = current_val - target

            if current_val < target:
                status = 'DEFICIT'
                # Przybliżona konwersja mg/kg na kg/ha dla warstwy 15cm
                # Zakładamy gęstość objętościową 1.55 g/cm3 (1550 kg/m3)
                # 15 cm = 0.15 m
                # Masa gleby w 1 ha (10000 m2) do głębokości 0.15m = 10000 * 0.15 * 1550 = 2325000 kg
                # Czyli 1 mg/kg = 1 g/tonę = 2.325 kg/ha
                # Potrzeba = (target - current_val) * 2.325
                # Używamy bulk_density z profilu, jeśli dostępne, inaczej domyślne
                bulk_density = self.profile.get('bulk_density', DEFAULT_BULK_DENSITY)
                need_kg_ha = (target - current_val) * (bulk_density * 0.15 * 10000 / 1000) # kg/ha
                need_kg_ha = round(need_kg_ha, 2)

            balance[nutrient] = {
                'current': current_val,
                'target': target,
                'diff_mg_kg': round(diff, 1),
                'status': status,
                'need_kg_ha': need_kg_ha
            }
        return balance

    def get_organic_nitrogen_potential(self):
        """
        Szacuje potencjał mineralizacji azotu z materii organicznej.
        """
        om_pct = self.profile.get('om_pct', 2.5)
        # Uproszczone założenie: 1% OM uwalnia ok. 2 kg N/ha/rok
        # W rzeczywistości zależy od C:N, temperatury, wilgotności
        return round(om_pct * 2.0, 1)

    def nitrogen_release_model(self, n_amount_applied, soil_temp_c, form='urea'):
        """
        Model uwalniania azotu w zależności od temperatury i formy.
        Zwraca procent uwolnionego N dziennie.
        """
        if form == 'urea':
            # Ureaza działa optymalnie w 20-30C. Poniżej 10C bardzo wolno.
            # Uproszczony model: liniowy wzrost od 5C do 25C, potem plateau
            if soil_temp_c < 5:
                release_rate = 0.001 # Bardzo wolno
            elif soil_temp_c > 25:
                release_rate = 0.05 # Max 5% dziennie
            else:
                release_rate = 0.001 + (soil_temp_c - 5) * (0.05 - 0.001) / (25 - 5)
            return release_rate
        elif form == 'nh4':
            # Nitryfikacja (NH4 -> NO3) jest procesem mikrobiologicznym, temp-zależnym
            if soil_temp_c < 10:
                release_rate = 0.01 # Wolno
            elif soil_temp_c > 30:
                release_rate = 0.08 # Max 8% dziennie
            else:
                release_rate = 0.01 + (soil_temp_c - 10) * (0.08 - 0.01) / (30 - 10)
            return release_rate
        return 0.0

    def calculate_cec(self):
        """
        Oblicza przybliżoną Kationową Pojemność Wymienną (CEC) w meq/100g.
        Uproszczony model bazujący na materii organicznej i glinie.
        """
        om_pct = self.profile.get('om_pct', 2.5)
        clay_pct = self.profile.get('clay_pct', 5.0)

        # Typowe wartości CEC:
        # OM: ~200 meq/100g na 1% OM
        # Glina: ~50 meq/100g na 1% gliny
        # Uproszczony model: 2 meq/100g per %OM, 0.5 meq/100g per %Clay
        cec = (om_pct * 2.0) + (clay_pct * 0.5)
        return round(cec, 2)

    def calculate_cation_balance_saturation(self):
        """
        Model Bilansu Kationów (K, Mg, Ca) w procentach wysycenia kompleksu sorpcyjnego.
        Zwraca słownik z procentowym wysyceniem dla K, Mg, Ca oraz sumaryczne CEC.
        """
        k_mg_kg = self.soil_data.get('m3_k', 0.0) or 0.0
        mg_mg_kg = self.soil_data.get('m3_mg', 0.0) or 0.0
        ca_mg_kg = self.soil_data.get('m3_ca', 0.0) or 0.0

        # Konwersja mg/kg na meq/100g
        k_meq_100g = (k_mg_kg * 1) / (39.1 * 10)
        mg_meq_100g = (mg_mg_kg * 2) / (24.3 * 10)
        ca_meq_100g = (ca_mg_kg * 2) / (40.1 * 10)

        total_cec = self.calculate_cec()

        if total_cec == 0:
            return {'K_saturation_pct': 0.0, 'Mg_saturation_pct': 0.0, 'Ca_saturation_pct': 0.0, 'Total_CEC_meq_100g': 0.0, 'status': 'Brak danych do obliczenia CEC'}

        k_sat_pct = (k_meq_100g / total_cec) * 100
        mg_sat_pct = (mg_meq_100g / total_cec) * 100
        ca_sat_pct = (ca_meq_100g / total_cec) * 100

        return {
            'K_saturation_pct': round(k_sat_pct, 1),
            'Mg_saturation_pct': round(mg_sat_pct, 1),
            'Ca_saturation_pct': round(ca_sat_pct, 1),
            'Total_CEC_meq_100g': round(total_cec, 2)
        }

    def get_micros_status(self):
        """
        Analizuje status mikroelementów (Fe, Mn, Zn, Cu, B) na podstawie Mehlich-3.
        Zwraca interpretację dla każdego pierwiastka.
        """
        micros = {
            'fe': {'name': 'Żelazo', 'min': 50},
            'mn': {'name': 'Mangan', 'min': 20},
            'zn': {'name': 'Cynk', 'min': 2},
            'cu': {'name': 'Miedź', 'min': 1},
            'b': {'name': 'Bor', 'min': 0.5}
        }
        results = {}
        for key, limits in micros.items():
            val = self.soil_data.get(f'm3_{key}', 0.0) or 0.0
            results[limits['name']] = {
                'value': val,
                'status': 'OK' if val >= limits['min'] else 'DEFICIT',
                'target': limits['min']
            }
        return results

    def check_salinity_risk(self):
        """
        Ocena ryzyka zasolenia i toksyczności chlorków/sodu (Parametr 18 z Prompt.txt).
        """
        ec = self.soil_data.get('ec_ds_m', 0.0) or 0.0
        # Sód i Chlorki zazwyczaj z metody ogrodniczej (mg/dm3)
        na = self.soil_data.get('hort_na', 0.0) or 0.0
        
        risk = "LOW"
        if ec > 2.0 or na > 150:
            risk = "HIGH"
        elif ec > 1.0 or na > 70:
            risk = "MODERATE"
            
        return {
            'risk_level': risk,
            'ec_value': ec,
            'na_content': na,
            'recommendation': "Płukanie profilu wymagane" if risk == "HIGH" else "Monitorowanie"
        }