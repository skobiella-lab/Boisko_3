# vision/spectral_core.py

import numpy as np

class SpectralAnalysis:
    def __init__(self):
        pass

    def calculate_ndvi(self, red_band, nir_band):
        """
        Oblicza NDVI (Normalized Difference Vegetation Index).
        red_band, nir_band: macierze numpy (numpy arrays) z danymi z kamery.
        """
        # Formuła: (NIR - RED) / (NIR + RED)
        # Dodajemy małą wartość, aby uniknąć dzielenia przez zero
        ndvi = (nir_band.astype(float) - red_band.astype(float)) / \
               (nir_band + red_band + 1e-10)

        avg_ndvi = np.mean(ndvi)

        # Interpretacja dla murawy sportowej
        if avg_ndvi > 0.8:
            comment = "Bardzo wysoka aktywność fotosyntezy"
        elif avg_ndvi > 0.6:
            comment = "Stan optymalny"
        else:
            comment = "Wykryto stres (biotyczny lub abiotyczny)"

        return {'ndvi_avg': round(avg_ndvi, 3), 'comment': comment}

    def calculate_ndre(self, red_edge_band, nir_band):
        """
        Oblicza NDRE (Normalized Difference Red Edge).
        Lepszy dla bardzo gęstej darni, gdzie NDVI się "nasyca".
        """
        ndre = (nir_band.astype(float) - red_edge_band.astype(float)) / \
               (nir_band + red_edge_band + 1e-10)
        return round(np.mean(ndre), 3)
