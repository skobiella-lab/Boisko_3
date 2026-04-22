# vision/color_analysis.py

import cv2
import numpy as np

class ColorAnalysis:
    def __init__(self):
        pass

    def calculate_dgci(self, image_path):
        """
        Oblicza Dark Green Color Index (DGCI).
        Wartość 0-1 (im wyższa, tym ciemniejsza, zdrowsza trawa).
        """
        img = cv2.imread(image_path)
        if img is None:
            return None

        # Konwersja do przestrzeni HLS (Hue, Lightness, Saturation)
        hls = cv2.cvtColor(img, cv2.COLOR_BGR2HLS)

        # Wyciągamy średnie wartości dla całego zdjęcia
        avg_h = np.mean(hls[:, :, 0])  # Odcień
        avg_l = np.mean(hls[:, :, 1])  # Jasność
        avg_s = np.mean(hls[:, :, 2])  # Nasycenie

        # Standaryzacja wartości (według literatury naukowej DGCI)
        # Przekształcamy parametry na skalę 0-1
        h_scaled = avg_h / 180.0
        l_scaled = avg_l / 255.0
        s_scaled = avg_s / 255.0

        dgci = (h_scaled + (1 - l_scaled) + s_scaled) / 3

        status = "Optymalny Azot" if dgci > 0.55 else "Możliwy deficyt N/Fe"
        return {'dgci': round(dgci, 3), 'status': status}

    def detect_bare_patches(self, image_path):
        """
        Wykrywa ubytki (puste place) na murawie.
        """
        img = cv2.imread(image_path)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Zakres koloru zielonego
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])

        mask = cv2.inRange(hsv, lower_green, upper_green)
        green_ratio = np.sum(mask > 0) / mask.size

        return {'cover_pct': round(green_ratio * 100, 1)}
