# engines/biology.py
import math
from turf_advisor.config import TEMP_BASE_GDD, OPTIMAL_GROWTH_TEMP

class BiologyEngine:
    def __init__(self, profile):
        self.profile = profile

    def calculate_gdd(self, t_max, t_min):
        """Model Skumulowanych Stopniodni (GDD)."""
        daily_avg = (t_max + t_min) / 2
        gdd = max(0, daily_avg - TEMP_BASE_GDD)
        return round(gdd, 1)

    def growth_potential_pace(self, t_avg):
        """Model Potencjału Wzrostu (GP) na podstawie temperatury."""
        # Krzywa dzwonowa (Gaussian) dla trawy typu C3
        sigma = 5.5 
        gp = math.exp(-0.5 * pow((t_avg - OPTIMAL_GROWTH_TEMP) / sigma, 2))
        return round(gp, 3)

    def shear_strength_model(self, vmc):
        """Model Odporności na Ścinanie (Parametr Coulomba-Mohra)."""
        # Uproszczony model: wilgotność obniża stabilność mechaniczną
        # vmc w zakresie 0.10 - 0.40
        base_shear = 45.0  # kPa dla suchego piasku
        if vmc > 0.25:
            kpa = base_shear * (1 - (vmc - 0.25) * 2)
            status = 'SOFT' if vmc < 0.35 else 'UNSTABLE'
        else:
            kpa = base_shear + (vmc * 20)
            status = 'EXCELLENT'
        return {'kpa': round(kpa, 1), 'status': status}

    def calculate_n_mineralization(self, t_avg, vmc):
        """Model Mineralizacji Azotu (Stosunek C:N i temperatura)."""
        if t_avg < 5: return 0.0
        om = float(self.profile.get('om_pct', 2.0))
        cn = float(self.profile.get('cn_ratio', 12))
        
        # Tempo zależne od aktywności mikrobiologicznej (temp i wilgoć)
        rate = (t_avg / 20) * (vmc / 0.25) * (15 / cn)
        return round(om * rate * 0.15, 2) # kg N/ha/dobę