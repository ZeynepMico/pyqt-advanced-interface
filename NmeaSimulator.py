from PyQt5.QtCore import QObject, QTimer

class NmeaSimulator(QObject):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

        self.simulation_route = [
            (39.9334, 32.8597), # Ankara, Anıtkabir
            (39.2131, 33.1787), # Şereflikoçhisar (Tuz Gölü yakını)
            (38.3686, 34.0370), # Aksaray
            (37.8713, 32.4942), # Konya, Mevlana Müzesi
            (38.2269, 34.5367), # Ihlara Vadisi girişi
            (38.6274, 34.7132), # Nevşehir (Kapadokya)
            (38.7230, 35.4849), # Kayseri
            (39.7478, 37.0179), # Sivas, şehir merkezi
            (39.8465, 33.5153)  # Kırıkkale (Ankara'ya dönüş yolu)
        ]
        self.sim_route_index = 0

        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(self.simulate_gps_data)

    def start(self, interval_ms=1000):
        """Simülasyonu başlatır."""
        self.simulation_timer.start(interval_ms)
        self.main_window.append_to_log("NMEA simulation started.", color="green")

    def stop(self):
        """Simülasyonu durdurur."""
        self.simulation_timer.stop()
        self.main_window.append_to_log("NMEA simulation stopped.", color="orange")

    def simulate_gps_data(self):
        """Tanımlı rota üzerinden sahte bir NMEA cümlesi oluşturur ve ana pencereye gönderir."""
        if not self.simulation_route:
            return
            
        lat, lon = self.simulation_route[self.sim_route_index]

        # NMEA FORMATLAMA KODU 
        # Enlem için
        lat_deg = int(lat)
        lat_min = (lat - lat_deg) * 60
        lat_nmea = f"{lat_deg:02d}{lat_min:07.4f}" # DDMM.MMMM formatı
        lat_dir = 'N' if lat >= 0 else 'S'
        
        # Boylam için
        lon_deg = int(lon)
        lon_min = (lon - lon_deg) * 60
        lon_nmea = f"{lon_deg:03d}{lon_min:07.4f}" # DDDMM.MMMM formatı
        lon_dir = 'E' if lon >= 0 else 'W'
        
        # Sahte bir $GPRMC cümlesi oluştur
        fake_nmea_sentence = f"$GPRMC,123519,A,{lat_nmea},{lat_dir},{lon_nmea},{lon_dir},0.0,0.0,290725,,"
        
        self.main_window.append_to_log(f"SIMULATOR: {fake_nmea_sentence}", color="black")
        
        self.main_window.parse_nmea_sentence(fake_nmea_sentence)
        
        self.sim_route_index = (self.sim_route_index + 1) % len(self.simulation_route)