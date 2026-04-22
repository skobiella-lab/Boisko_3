# probabilistic/monte_carlo.py

import numpy as np
from turf_advisor.config import ENABLE_PROBABILISTIC

class MonteCarloEngine:
    def __init__(self, current_n_status, soil_profile):
        if current_n_status is None:
            raise ValueError("current_n_status cannot be None")
        self.initial_n = current_n_status
        self.profile = soil_profile

    def simulate_nitrogen_leaching(self, forecast_precip, iterations=1000):
        """
        Symuluje ryzyko utraty azotu przy niepewności opadów.
        forecast_precip: prognozowany opad w mm.
        """
        if not ENABLE_PROBABILISTIC:
            return "Moduł probabilistyczny wyłączony."

        leaching_results = []

        for _ in range(iterations):
            # Wprowadzamy szum do prognozy opadu (+/- 30%)
            simulated_rain = np.random.normal(forecast_precip, forecast_precip * 0.3)
            simulated_rain = max(0, simulated_rain)

            # Modelujemy drenaż: piasek przepuszcza wodę nieliniowo
            # Jeśli opad > 15mm na Twoim profilu, strata N gwałtownie rośnie
            if simulated_rain > 15:
                loss_pct = np.random.uniform(0.15, 0.40) # Strata 15-40% azotu
            else:
                loss_pct = np.random.uniform(0.01, 0.05)

            leaching_results.append(self.initial_n * loss_pct)

        # Obliczamy prawdopodobieństwo utraty więcej niż 20% azotu
        critical_loss = [res for res in leaching_results if res > (self.initial_n * 0.2)]
        prob_low_efficiency = len(critical_loss) / iterations

        return {
            'avg_loss_kg': round(np.mean(leaching_results), 2),
            'risk_level': "HIGH" if prob_low_efficiency > 0.3 else "LOW",
            'confidence_interval': np.percentile(leaching_results, [5, 95])
        }
