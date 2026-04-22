# database/db_manager.py
import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Ustawia ścieżkę bezwzględną względem folderu turf_advisor
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, 'data', 'turf_system.db')
        else:
            self.db_path = db_path
        # Upewnij się, że katalog data istnieje
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        """Tworzy połączenie z bazą danych i ustawia Row jako słownik."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Inicjalizuje bazę danych na podstawie pliku schema.sql"""
        # Jeśli plik bazy nie istnieje, zostanie utworzony przy pierwszym połączeniu
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema = f.read()
            with self.get_connection() as conn:
                conn.executescript(schema)

    def save_soil_analysis(self, data_dict):
        """Zapisuje kompletny wynik Mehlich-3 i Metody Ogrodniczej (18 parametrów)"""
        query = """
            INSERT INTO soil_analysis (
                profile_id, date_sampled, ph_h2o, ph_hcl, ec_ds_m,
                m3_p, m3_k, m3_mg, m3_ca, m3_s, m3_na, m3_fe, m3_mn, 
                m3_b, m3_cu, m3_zn, m3_al,
                hort_p, hort_k, hort_mg, hort_n_no3, hort_n_nh4, hort_cl
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            # Pobieranie wartości ze słownika z wartościami domyślnymi (0.0), aby uniknąć błędów
            values = (
                data_dict.get('profile_id', 1),
                data_dict.get('date_sampled', datetime.now().date().strftime('%Y-%m-%d')),
                data_dict.get('ph_h2o', 6.5),
                data_dict.get('ph_hcl', 0.0),
                data_dict.get('ec_ds_m', 0.0),
                data_dict.get('m3_p', 0.0),
                data_dict.get('m3_k', 0.0),
                data_dict.get('m3_mg', 0.0),
                data_dict.get('m3_ca', 0.0),
                data_dict.get('m3_s', 0.0),
                data_dict.get('m3_na', 0.0),
                data_dict.get('m3_fe', 0.0),
                data_dict.get('m3_mn', 0.0),
                data_dict.get('m3_b', 0.0),
                data_dict.get('m3_cu', 0.0),
                data_dict.get('m3_zn', 0.0),
                data_dict.get('m3_al', 0.0),
                data_dict.get('hort_p', 0.0),
                data_dict.get('hort_k', 0.0),
                data_dict.get('hort_mg', 0.0),
                data_dict.get('hort_n_no3', 0.0),
                data_dict.get('hort_n_nh4', 0.0),
                data_dict.get('hort_cl', 0.0)
            )
            with self.get_connection() as conn:
                conn.execute(query, values)
                conn.commit()
                print(">>> SUKCES: Dane glebowe zapisane pomyślnie.")
                return True
        except Exception as e:
            print(f">>> BŁĄD ZAPISU DO BAZY: {e}")
            return False

    def get_latest_soil_analysis(self, profile_id):
        """Pobiera absolutnie ostatni rekord analizy dla danego boiska."""
        query = "SELECT * FROM soil_analysis WHERE profile_id = ? ORDER BY id DESC LIMIT 1"
        try:
            with self.get_connection() as conn:
                row = conn.execute(query, (profile_id,)).fetchone()
                if row:
                    return dict(row) # Zamiana na słownik, aby NutritionEngine mógł czytać klucze
                return None
        except Exception as e:
            print(f">>> BŁĄD ODCZYTU Z BAZY: {e}")
            return None

    def add_maintenance_record(self, profile_id, action_type, amount, product_id=None):
        """Zapisuje zabieg pielęgnacyjny w dzienniku."""
        query = """
            INSERT INTO maintenance_log (profile_id, action_type, amount, product_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            with self.get_connection() as conn:
                conn.execute(query, (profile_id, action_type, amount, product_id, datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            print(f">>> BŁĄD ZAPISU ZABIEGU: {e}")
            return False

    def get_maintenance_records(self, profile_id):
        """Pobiera historię wszystkich zabiegów dla danego boiska."""
        query = "SELECT * FROM maintenance_log WHERE profile_id = ? ORDER BY timestamp DESC"
        try:
            with self.get_connection() as conn:
                rows = conn.execute(query, (profile_id,)).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f">>> BŁĄD ODCZYTU DZIENNIKA: {e}")
            return []

    def get_weather_history(self, days=7):
        """Pobiera historię pogody do wykresów i modeli (tylko rzeczywiste dane)."""
        query = "SELECT * FROM weather_history WHERE is_forecast = 0 ORDER BY date DESC LIMIT ?"
        try:
            with self.get_connection() as conn:
                rows = conn.execute(query, (days,)).fetchall()
                # Zwracamy listę słowników dla czytelności w Pandas
                return [dict(row) for row in rows]
        except Exception as e:
            print(f">>> BŁĄD ODCZYTU POGODY: {e}")
            return []

    def get_weather_forecast(self):
        """Pobiera prognozę pogody (tylko dane prognozy)."""
        from datetime import datetime
        today = datetime.now().date()
        query = "SELECT * FROM weather_history WHERE date >= ? AND is_forecast = 1 ORDER BY date ASC"
        try:
            with self.get_connection() as conn:
                rows = conn.execute(query, (today,)).fetchall()
                # Zwracamy listę słowników dla czytelności w Pandas
                return [dict(row) for row in rows]
        except Exception as e:
            print(f">>> BŁĄD ODCZYTU PROGNOZY: {e}")
            return []
