import serial
import time

# Sanal port çiftinin bir ucunu seçin.
# Ana uygulamanız diğer uca bağlanacak.
PORT_ADI = 'COM6'
BAUD_RATE = 115200 

print(f"Sanal Cihaz baslatiliyor. {PORT_ADI} portu dinleniyor...")
print("Cikmak icin Ctrl+C'ye basin.")

try:
    # Seri portu aç
    ser = serial.Serial(PORT_ADI, BAUD_RATE, timeout=1)

    while True:
        # Eğer portta okunacak veri varsa
        if ser.in_waiting > 0:
            # Gelen veriyi satır olarak oku ('\n' karakterine kadar)
            gelen_veri = ser.readline()
            
            # Gelen byte'ları metne çevir ve boşlukları temizle
            komut = gelen_veri.decode('utf-8').strip()
            
            if komut: # Eğer boş bir satır gelmediyse
                print(f"Alinan komut: '{komut}'")
                
                # Gelen komuta göre yanıt hazırla
                if komut == "LED_ON":
                    yanit = b"led yandi\n"
                elif komut == "LED_OFF":
                    yanit = b"led sondu\n"
                elif komut == "STATUS":
                    yanit = b"STATUS: OK, Cihaz Calisiyor\n"
                else:
                    yanit = f"Bilinmeyen komut: {komut}\n".encode('utf-8')
                
                # Yanıtı porta geri yaz
                ser.write(yanit)
                print(f"Gonderilen yanit: {yanit.strip()}")
        
        # CPU'yu yormamak için kısa bir bekleme
        time.sleep(0.1)

except serial.SerialException as e:
    print(f"Hata: Port acilamadi veya kullanilamiyor. {e}")
except KeyboardInterrupt:
    print("\nProgram kapatiliyor.")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()