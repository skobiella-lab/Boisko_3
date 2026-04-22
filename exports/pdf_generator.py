# exports/pdf_generator.py

from fpdf import FPDF
from datetime import datetime

class ReportGenerator:
    def __init__(self, field_name):
        self.field_name = field_name
        self.pdf = FPDF()
        self.pdf.add_page()
        # W realnej aplikacji należy załadować czcionkę obsługującą polskie znaki (UTF-8)
        self.pdf.set_font("Arial", size=12)

    def generate_weekly_report(self, hard_data, deterministic_advice, risk_alerts):
        """
        Główna metoda tworząca profesjonalny raport.
        hard_data: Wyniki fizyczne (Mehlich-3, VMC)
        deterministic_advice: Zalecenia z modeli (ilość wody, nawozu)
        risk_alerts: Wnioski z modeli probabilistycznych i wizji
        """
        # 1. NAGŁÓWEK
        self.pdf.set_font("Arial", 'B', 16)
        self.pdf.cell(200, 10, txt=f"RAPORT TYGODNIOWY: {self.field_name}", ln=True, align='C')
        self.pdf.set_font("Arial", size=10)
        self.pdf.cell(200, 10, txt=f"Data wygenerowania: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
        self.pdf.ln(10)

        # 2. WSKAZÓWKI OPISOWE (Komentarz Agrotechniczny)
        self.pdf.set_font("Arial", 'B', 12)
        self.pdf.cell(200, 10, txt="1. KOMENTARZ I WSKAZOWKI DLA OPIEKUNA", ln=True)
        self.pdf.set_font("Arial", size=11)

        # Tekst generowany przez silnik opisowy
        comment = (
            f"W nadchodzacym tygodniu warunki meteo wymuszaja korekte nawadniania. "
            f"Model fizyczny przewiduje deficyt wody w czwartek. "
            f"Zasoby potasu (K) wg Mehlich-3 sa na poziomie {hard_data['k_val']} mg/kg. "
            f"Zalecane rzadkie, ale glebokie podlewanie (25-30 mm)."
        )
        self.pdf.multi_cell(0, 10, txt=comment)
        self.pdf.ln(5)

        # 3. HARMONOGRAM ZABIEGÓW
        self.pdf.set_font("Arial", 'B', 12)
        self.pdf.cell(200, 10, txt="2. HARMONOGRAM TYGODNIOWY (PROJEKT)", ln=True)
        self.pdf.set_font("Arial", size=10)

        # Tabela harmonogramu
        self.pdf.cell(40, 10, "Dzien", 1)
        self.pdf.cell(80, 10, "Zabieg", 1)
        self.pdf.cell(60, 10, "Zrodlo / Model", 1)
        self.pdf.ln()

        schedule = [
            ("Poniedzialek", "Koszenie 28mm", "Model GDD"),
            ("Czwartek", "Podlewanie 30mm", "Model Richardsa"),
            ("Sobota", "Koszenie 28mm", "Fizyka Wzrostu")
        ]

        for day, action, source in schedule:
            self.pdf.cell(40, 10, day, 1)
            self.pdf.cell(80, 10, action, 1)
            self.pdf.cell(60, 10, source, 1)
            self.pdf.ln()

        self.pdf.ln(5)

        # 4. DANE FIZYCZNE I PODSUMOWANIE (Mehlich-3)
        self.pdf.set_font("Arial", 'B', 12)
        self.pdf.cell(200, 10, txt="3. PODSUMOWANIE STANU ZASOBOW", ln=True)
        self.pdf.set_font("Arial", size=10)

        for p, val in hard_data['nutrients'].items():
            self.pdf.cell(0, 7, txt=f"- {p}: {val} mg/kg (MLSN Target: {hard_data['targets'][p]})", ln=True)

        # Zapis do pliku
        filename = f"reports/Raport_{datetime.now().strftime('%Y%m%d')}.pdf"
        self.pdf.output(filename)
        return filename
