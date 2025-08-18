import serial
import time
import math

# Sanal port çiftinin bir ucunu seçin.
# Ana uygulamanız diğer uca bağlanacak.
PORT_ADI = 'COM6'
BAUD_RATE = 115200 

print(f"Grafik Test Veri Gonderici baslatiliyor. Port: {PORT_ADI}")
print("Veri gonderme basladi... Cikmak icin Ctrl+C'ye basin.")

try:
    # Seri portu aç
    with serial.Serial(PORT_ADI, BAUD_RATE, timeout=1) as ser:
        i = 0
        while True:
            # Test için 8 farklı ve ilgi çekici veri üretelim
            # Sinüs ve kosinüs dalgaları, lineer artış, rastgele gürültü vb.
            val1 = 50 + 50 * math.sin(math.radians(i * 2))     # Sinüs dalgası
            val2 = 50 + 50 * math.cos(math.radians(i * 2))     # Kosinüs dalgası
            val3 = i % 100                                     # 0-99 arası sayan sayaç
            val4 = 75                                          # Sabit değer
            val5 = 50 + 25 * math.sin(math.radians(i * 5))     # Daha hızlı bir sinüs dalgası
            val6 = 25 + 25 * math.cos(math.radians(i * 1))     # Daha yavaş bir kosinüs dalgası
            val7 = 100 - (i % 100)                             # Geriye sayan sayaç
            val8 = val1 + 10                                   # Birinci veriye bağımlı veri

            # Verileri virgülle ayrılmış bir metin haline getir
            # ".2f" ile virgülden sonra 2 basamak olacak şekilde formatlıyoruz
            veri_satiri = f"{val1:.2f},{val2:.2f},{val3:.2f},{val4:.2f},{val5:.2f},{val6:.2f},{val7:.2f},{val8:.2f}\n"
            
            # Satırı seri porta gönder
            ser.write(veri_satiri.encode('utf-8'))
            
            print(f"Gonderildi: {veri_satiri.strip()}", end='\r')
            
            i += 1
            # Veri gönderme sıklığı (saniyede 5 kez)
            time.sleep(0.2) 

except serial.SerialException as e:
    print(f"\nHata: Port acilamadi veya kullanilamiyor. {e}")
except KeyboardInterrupt:
    print("\nProgram kapatiliyor.")
