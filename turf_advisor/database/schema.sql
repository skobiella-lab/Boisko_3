-- Tabela analiz glebowych (Mehlich-3 i Metoda Ogrodnicza)
CREATE TABLE IF NOT EXISTS soil_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER,
    date_sampled TEXT,
    ph_h2o REAL,
    ph_hcl REAL,
    ec_ds_m REAL,
    m3_p REAL, m3_k REAL, m3_mg REAL, m3_ca REAL, m3_s REAL,
    m3_na REAL, m3_fe REAL, m3_mn REAL, m3_b REAL, m3_cu REAL,
    m3_zn REAL, m3_al REAL,
    hort_p REAL, hort_k REAL, hort_mg REAL,
    hort_n_no3 REAL, hort_n_nh4 REAL, hort_cl REAL
);

-- Tabela logów zabiegów
CREATE TABLE IF NOT EXISTS maintenance_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER,
    action_type TEXT,
    amount REAL,
    product_id INTEGER,
    timestamp DATETIME
);

-- Tabela pogody (historia i prognoza)
CREATE TABLE IF NOT EXISTS weather_history (
    date TEXT PRIMARY KEY,
    temp_max REAL,
    temp_min REAL,
    temp_avg REAL,
    precip_mm REAL,
    humidity REAL,
    et_calculated REAL,
    is_forecast INTEGER DEFAULT 0
);

-- Przykładowy profil boiska
INSERT OR IGNORE INTO soil_analysis (id, profile_id, date_sampled, ph_h2o) 
VALUES (1, 1, '2023-01-01', 6.5);