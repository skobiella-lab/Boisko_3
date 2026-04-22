# engines/hydrology.py

import math

class HydrologyEngine:
    def __init__(self, static_profile, weather_data):
        """
        static_profile: Dane granulometryczne (sand, silt, clay)
        weather_data: Dane pogodowe (temp, humidity, wind, solar)
        """
        self.profile = static_profile
        self.weather = weather_data
        # Stałe fizyczne dla piasku (Model Richardsa / Van Genuchten)
        self.alpha = 0.145  # Parametr dla piasku (1/cm)
        self.n_param = 2.68 # Parametr dla piasku
        self.theta_s = 0.43 # Nasycenie (porowatość)
        self.theta_r = 0.04 # Wilgotność resztkowa

    def calculate_et0_penman(self, t_avg, humidity, wind_speed, solar_rad):
        """
        Model Ewapotranspiracji Penman-Monteith (FAO-56).
        Oblicza ile mm wody ucieka z murawy na dobę.
        """
        # Uproszczony model Penman-Monteith
        delta = (4098 * (0.6108 * math.exp(17.27 * t_avg / (t_avg + 237.3)))) / ((t_avg + 237.3) ** 2)
        psycho = 0.067

        # Wpływ wiatru i słońca
        rn = solar_rad * 0.77  # Net radiation (uproszczone)
        et0 = (0.408 * delta * rn + psycho * (900 / (t_avg + 273)) * wind_speed * (1.5)) / (delta + psycho * (1 + 0.34 * wind_speed))

        # Kc dla murawy sportowej (współczynnik roślinny)
        kc = 0.85
        return et0 * kc

    def estimate_field_capacity(self):
        """
        Estymuje pojemność polową (Field Capacity) na podstawie składu granulometrycznego.
        Model 10: Retencja wody.
        """
        sand = self.profile.get('sand_pct', 90.0)
        # Uproszczona korelacja: im więcej piasku, tym niższa pojemność polowa
        # Dla 100% piasku ok 10%, dla 80% piasku ok 20%
        fc = 0.10 + (100 - sand) * 0.005
        return round(fc, 3)

    def water_retention_curve(self, h):
        """
        Model Van Genuchtena (Model 10 z Twoich notatek).
        h: potencjał matrycowy (cm)
        Zwraca objętościową zawartość wody (theta).
        """
        m = 1 - 1/self.n_param
        theta = self.theta_r + (self.theta_s - self.theta_r) / (math.pow(1 + math.pow(self.alpha * h, self.n_param), m))
        return theta

    def simulate_leaching(self, irrigation_mm, current_vmc):
        """
        Uproszczony Model Richardsa (Model 6).
        Oblicza ile wody z podlewania ucieknie poza strefę korzeniową (150mm).
        """
        field_capacity = self.estimate_field_capacity()
        available_space = (field_capacity - current_vmc) * self.profile['root_depth_mm']

        if irrigation_mm > available_space:
            leached = irrigation_mm - available_space
            return round(leached, 2)
        return 0.0

    def get_irrigation_strategy(self, current_vmc, forecast_et_sum_3days):
        """
        Logika planowania dla podlania 1-2 razy w tygodniu.
        """
        # Punkt więdnięcia dla piasku (PWP)
        wilting_point = 0.07
        # Bezpieczny zapas (Management Allowed Depletion)
        mad_threshold = 0.12

        current_water_storage = current_vmc * self.profile['root_depth_mm']
        min_water_storage = mad_threshold * self.profile['root_depth_mm']

        usable_water = max(0, current_water_storage - min_water_storage)

        if usable_water < forecast_et_sum_3days:
            # Sugerowana dawka "na zapas" uwzględniająca retencję
            needed_dose = forecast_et_sum_3days - usable_water
            # Ograniczenie do pojemności polowej (żeby nie wypłukać nawozu)
            max_effective_dose = (0.25 - current_vmc) * self.profile['root_depth_mm']

            return {
                'action': 'IRRIGATE',
                'dose_mm': round(min(needed_dose * 1.2, max_effective_dose), 1),
                'note': "Podlewanie zapobiegawcze przed suszą."
            }

        return {'action': 'WAIT', 'dose_mm': 0, 'note': "Wilgotność w normie."}

    def air_filled_porosity(self, current_vmc):
        """
        Model Wymiany Gazowej (Model 7).
        Oblicza wolną przestrzeń powietrzną w porach gleby.
        """
        total_porosity = 1 - (self.profile['bulk_density'] / 2.65)
        air_content = total_porosity - current_vmc

        # Krytyczna wartość dla korzeni to 10% tlenu w porach
        status = "OK" if air_content > 0.10 else "ANXIA_RISK"
        return {'air_pct': round(air_content * 100, 1), 'status': status}
