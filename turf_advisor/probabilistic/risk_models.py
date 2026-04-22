# probabilistic/risk_models.py

import math
from turf_advisor.config import ENABLE_PROBABILISTIC

class RiskEngine:
    def __init__(self):
        pass

    def smith_kerns_dollar_spot(self, temp_avg_list, humidity_avg_list):
        """
        Model Ryzyka Chorobowego (Model III.6).
        Oblicza prawdopodobieństwo wystąpienia Dolarowej Plamistości (0.0 - 1.0).
        """
        if not temp_avg_list or not humidity_avg_list:
            return 0.0
            
        # Średnia z ostatnich 5 dni
        t_avg = sum(temp_avg_list) / len(temp_avg_list)
        rh_avg = sum(humidity_avg_list) / len(humidity_avg_list)

        # Równanie logistyczne Smith-Kerns
        logit = -11.403 + (0.284 * t_avg) + (0.066 * rh_avg)
        probability = math.exp(logit) / (1 + math.exp(logit))

        return round(probability, 3)

    def bayesian_stress_diagnosis(self, evidence):
        """
        Sieć Bayesa (Model III.4) - Uproszczona logika wnioskowania.
        evidence: {'yellowing': True, 'low_temp': False, 'high_ph': True}
        """
        if not ENABLE_PROBABILISTIC:
            return "Wymagany tryb Advanced."

        # P(Przyczyna | Objaw)
        # Jeśli liście żółkną i pH > 7.0 -> Wysokie prawdop. braku Fe/Mn (Model II.17)
        risks = []
        if evidence.get('yellowing') and evidence.get('high_ph'):
            risks.append({'issue': 'Microelement Lockout', 'prob': 0.85})

        if evidence.get('yellowing') and evidence.get('low_nitrogen'):
            risks.append({'issue': 'Nitrogen Deficiency', 'prob': 0.70})

        return sorted(risks, key=lambda x: x['prob'], reverse=True)

    def markov_turf_degradation(self, match_count, current_state=0):
        """
        Modelowanie Markowa (Model III.2).
        Przewiduje stan murawy po serii meczów.
        States: 0-Perfect, 1-Wear, 2-Damaged
        """
        # Macierz przejść zależna od intensywności (match_count)
        # Przy intensywnym użytkowaniu szansa na degradację rośnie o 20%
        transition_prob = 0.1 * match_count

        if current_state == 0 and transition_prob > 0.5:
            return 1 # Przejście do stanu 'Lekkie zużycie'
        return current_state
