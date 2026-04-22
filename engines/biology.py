# engines/biology.py

import math
from turf_advisor.config import TEMP_BASE_GDD, OPTIMAL_GROWTH_TEMP, NORMAL_STRESS_PLAYER, FRICTION_ANGLE_MAX

class BiologyEngine:
    def __init__(self, static_profile):
        """
        static_profile: Dane o gęstości, Om i głębokości korzeni.
        """
        self.profile = static_profile

    def calculate_gdd(self, t_max, t_min, base_temp=None):
        """
        Model Skumulowanych Stopniodni (Model II.1).
        Pomaga wyznaczyć termin kolejnego nawożenia lub zabiegów mechanicznych.
        """
        t_base = base_temp if base_temp is not None else TEMP_BASE_GDD
        t_avg = (t_max + t_min) / 2
        gdd = t_avg - t_base
        return round(max(0.0, gdd), 2)

    def growth_potential_pace(self, t_avg):
        """
        Model Potencjału Wzrostu (GP).
        Określa zapotrzebowanie na energię i składniki.
        """
        # Model Gaussa dla traw sezonu chłodnego (C3)
        variance = 5.5  # Szerokość krzywej (standard dla muraw)
        gp = math.exp(-0.5 * ((t_avg - OPTIMAL_GROWTH_TEMP) / variance) ** 2)
        return round(gp, 4)

    def shear_strength_model(self, current_vmc, root_density_index=1.0):
        """
        Model Odporności na Ścinanie (Parametr Coulomba-Mohra - Model II.8).
        Przewiduje stabilność murawy pod korkiem zawodnika.
        """
        # Kohezja (c) zależy głównie od gęstości korzeni i w mniejszym stopniu od materii organicznej
        # Model zakłada, że korzenie "zbroją" piasek.
        base_cohesion = 12.0  # kPa dla czystego piasku z minimalną ilością korzeni
        root_reinforcement = 25.0 * root_density_index 
        om_effect = self.profile.get('om_pct', 2.0) * 1.5
        
        cohesion = base_cohesion + root_reinforcement + om_effect

        # Kąt tarcia wewnętrznego (phi) piasku maleje wraz z wilgotnością (vmc)
        # Piasek jest najbardziej stabilny przy umiarkowanej wilgotności
        # Przy bardzo wysokim VMC występuje ciśnienie porowe redukujące stabilność
        friction_angle = FRICTION_ANGLE_MAX
        if current_vmc > 0.25:
            friction_angle -= (current_vmc - 0.25) * 40  # Gwałtowny spadek przy zalaniu

        # Uproszczone naprężenie normalne (sigma) od zawodnika
        sigma = NORMAL_STRESS_PLAYER

        shear_strength = cohesion + sigma * math.tan(math.radians(friction_angle))

        # Interpretacja wyników
        if shear_strength > 70:
            status = "EXCELLENT"
        elif shear_strength > 50:
            status = "GOOD"
        elif shear_strength > 35:
            status = "SOFT"
        else:
            status = "UNSTABLE"
            
        return {'kpa': round(shear_strength, 2), 'status': status}

    def calculate_n_mineralization(self, t_avg, current_vmc):
        """
        Model Mineralizacji Azotu (Model II.9).
        Oblicza dobowe uwalnianie N z materii organicznej na podstawie stosunku C:N.
        """
        cn_ratio = self.profile.get('cn_ratio', 12)
        om_pct = self.profile.get('om_pct', 2.5)
        
        # Współczynnik temperaturowy (aktywność mikrobiologiczna rośnie z temp.)
        f_temp = max(0, (t_avg - 5) / 25) if t_avg > 5 else 0
        
        # Współczynnik wilgotności (optimum dla mikrobów to ok 0.18-0.22 VMC)
        f_moist = max(0, 1 - abs(current_vmc - 0.20) / 0.25)
        
        # Potencjał mineralizacji: ok 2 kg N / ha / rok na każdy 1% OM w temp. optymalnej
        annual_pot = om_pct * 2.0
        daily_rate = (annual_pot / 365) * f_temp * f_moist
        
        # Korekta o stosunek C:N
        if cn_ratio > 25: daily_rate *= 0.5   # Immobilizacja (mikroby zabierają N)
        elif cn_ratio < 15: daily_rate *= 1.2 # Szybkie uwalnianie
            
        return round(daily_rate, 4)

    def clipping_volume_prediction(self, last_n_app_date, current_gdd_sum):
        """
        Przewiduje objętość pokosu (ClipVol).
        Pomaga opiekunowi zaplanować koszenie przy rzadkich wizytach.
        """
        # Wzrost przyspiesza po GDD > 150 od aplikacji N
        growth_factor = 1.0
        if current_gdd_sum > 150:
            growth_factor = 1.5

        return "High" if growth_factor > 1.2 else "Normal"

    def oxygen_diffusion_rate(self, vmc):
        """
        Modelowanie Wymiany Gazowej (Model II.7).
        Ocenia, czy korzenie mają wystarczająco tlenu.
        """
        # Obliczanie porowatości całkowitej
        porosity = 1 - (self.profile.get('bulk_density', 1.55) / 2.65)
        air_filled_porosity = porosity - vmc

        # Jeśli AFP < 10%, wzrost korzeni zostaje zahamowany
        if air_filled_porosity < 0.10:
            return "CRITICAL: Oxygen deficiency"
        return "Optimal"
