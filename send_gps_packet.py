import serial
import struct
import time

# CRC16 fonksiyonu
def crc16(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc

def build_raw_binary(h_lat, h_lon, h_alt, t_lat, t_lon, t_alt):
    payload = struct.pack("<6d", h_lat, h_lon, h_alt, t_lat, t_lon, t_alt)
    return payload

def build_packet(h_lat, h_lon, h_alt, t_lat, t_lon, t_alt):
    payload = build_raw_binary(h_lat, h_lon, h_alt, t_lat, t_lon, t_alt)
    packet = bytearray()
    packet += b'\x55\xAA'
    packet += b'\x01'
    packet += bytes([len(payload)])
    packet += payload
    crc = crc16(packet[2:])
    packet += crc.to_bytes(2, 'big')
    return packet

def send_route_data(port_name='COM6', mode='packet'):
    """
    Tanımlanmış bir rota üzerindeki noktaları sırayla gönderir.
    """
    # İstanbul -> İzmit -> Bolu -> Ankara rotası
    turkey_route = [
        (41.044, 29.035),  # İstanbul - 15 Temmuz Şehitler Köprüsü
        (40.765, 29.940),  # İzmit
        (40.739, 31.609),  # Bolu
        (39.925, 32.836)   # Ankara - Anıtkabir
    ]
    
    # Hedef konumu sabit tutalım
    t_lat, t_lon, t_alt = 40.8845452, 29.0783668, 1600.0
    
    print(f"Opening port {port_name} to send ROUTE data in '{mode}' mode...")
    
    try:
        with serial.Serial(port_name, 115200, timeout=1) as ser:
            # Rota üzerindeki her nokta için bir paket gönder
            for i, (h_lat, h_lon) in enumerate(turkey_route):
                h_alt = 100.0 + (i * 50) # İrtifa da artsın
                
                print(f"Sending waypoint {i+1}/{len(turkey_route)}: Lat={h_lat}, Lon={h_lon}")
                
                if mode == 'packet':
                    pkt = build_packet(h_lat, h_lon, h_alt, t_lat, t_lon, t_alt)
                else: # 'binary'
                    pkt = build_raw_binary(h_lat, h_lon, h_alt, t_lat, t_lon, t_alt)
                
                ser.write(pkt)
                time.sleep(2) # Noktalar arası geçişi görmek için bekleme süresini artırdık
                
        print("Route simulation complete.")
    except serial.SerialException as e:
        print(f"Error opening or writing to serial port {port_name}: {e}")

if __name__ == "__main__":
    # Test edilecek modu buradan değiştirin: 'packet' veya 'binary'
    test_mode = 'packet'
    
    port = 'COM6'

    send_route_data(port_name=port, mode=test_mode)