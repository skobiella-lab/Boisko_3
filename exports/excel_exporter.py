# exports/excel_exporter.py

import pandas as pd

def export_raw_data_to_excel(weather_df, soil_df, maintenance_df):
    """
    Eksportuje pelna historie fizyczna do pliku Excel.
    weather_df: historia temperatur, opadow, ET
    soil_df: historia wynikow Mehlich-3
    maintenance_df: dziennik wszystkich zabiegow
    """
    with pd.ExcelWriter('reports/Turf_System_Raw_Data.xlsx') as writer:
        weather_df.to_excel(writer, sheet_name='Pogoda_i_ET')
        soil_df.to_excel(writer, sheet_name='Analizy_Glebowe')
        maintenance_df.to_excel(writer, sheet_name='Historia_Zabiegow')
