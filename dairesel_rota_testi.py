import serial
import struct
import time
import math

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
    packet += b'\x55\xAA'  # Header
    packet += b'\x01'      # Packet ID
    packet += bytes([len(payload)]) # Payload Length (48)
    packet += payload
    # CRC, ID + Len + Payload üzerinden hesaplanır
    crc = crc16(packet[2:])
    packet += crc.to_bytes(2, 'big')
    return packet

def send_circular_route_data(port_name='COM6', mode='packet'):
    """
    Belirlenen bir merkez etrafında dairesel bir rota verisi gönderir.
    """
    # Rota Ayarları
    # Merkez Nokta: Kadıköy Sahili civarı
    center_lat = 40.9925
    center_lon = 29.0225
    radius = 0.008  # Dairenin yarıçapı (derece cinsinden)
    
    # Sabit Hedef Noktası: Çamlıca Kulesi civarı
    t_lat, t_lon, t_alt = 41.0360, 29.0660, 587.0
    
    print(f"Opening port {port_name} to send CIRCULAR route data in '{mode}' mode...")
    
    try:
        with serial.Serial(port_name, 115200, timeout=1) as ser:
            # Daire üzerinde 5 derecelik adımlarla 72 nokta oluştur
            for angle in range(0, 361, 5):
                rad_angle = math.radians(angle)
                
                # Anlık 'Home' pozisyonunu sin/cos ile hesapla
                h_lat = center_lat + radius * math.sin(rad_angle)
                h_lon = center_lon + radius * math.cos(rad_angle)
                h_alt = 50 + 20 * math.sin(rad_angle) # İrtifa da dalgalansın
                
                print(f"Sending point {int(angle/5)+1}/73: Angle={angle}°, Lat={h_lat:.4f}, Lon={h_lon:.4f}")
                
                if mode == 'packet':
                    pkt = build_packet(h_lat, h_lon, h_alt, t_lat, t_lon, t_alt)
                else: # 'binary'
                    pkt = build_raw_binary(h_lat, h_lon, h_alt, t_lat, t_lon, t_alt)
                
                ser.write(pkt)
                time.sleep(0.2) # Animasyonun akıcı olması için bekleme süresini kısalttık
                
        print("Circular route simulation complete.")
    except serial.SerialException as e:
        print(f"Error opening or writing to serial port {port_name}: {e}")

if __name__ == "__main__":
    # Test edilecek modu buradan değiştirin: 'packet' veya 'binary'
    test_mode = 'binary'
    
    # Kendi sanal seri portunuzun adını buraya yazın
    port = 'COM6'

    send_circular_route_data(port_name=port, mode=test_mode)