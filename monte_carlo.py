# probabilistic/monte_carlo.py
import numpy as np

class MonteCarloEngine:
    def __init__(self, current_n, profile):
        self.current_n = current_n
        self.profile = profile

    def simulate_nitrogen_leaching(self, forecast_precip, iterations=1000):
        """Symulacja Monte Carlo: Ryzyko Wypłukania Azotu."""
        # Generujemy rozkład opadów (niepewność prognozy)
        precip_samples = np.random.normal(forecast_precip, forecast_precip * 0.3, iterations)
        leaching_losses = []

        for p in precip_samples:
            # Prosty model: powyżej 15mm opadu zaczyna się wypłukiwanie na piasku
            loss = max(0, (p - 15) * 0.05 * self.current_n)
            leaching_losses.append(loss)

        avg_loss = np.mean(leaching_losses)
        ci = np.percentile(leaching_losses, [5, 95])
        return {'avg_loss_kg': round(avg_loss, 2), 'confidence_interval': ci, 'risk_level': "HIGH" if avg_loss > 5 else "LOW"}