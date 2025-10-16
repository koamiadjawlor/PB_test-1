from machine import Pin, PWM, I2C, UART
import time

# Configuration PWM
pwm_out = PWM(Pin(16))
pwm_out.freq(1000)

# Configuration UART
uart = UART(0, baudrate=115200, tx=Pin(4), rx=Pin(5))

# Configuration I2C
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=100000)
ADS1015_ADDR = 0x48

# Variables de synchronisation
sequence = 0
last_received_sequence = -1

def read_ads1015_ain2():
    """Lecture de AIN2"""
    try:
        config = 0xE283
        i2c.writeto_mem(ADS1015_ADDR, 0x01, config.to_bytes(2, 'big'))
        time.sleep_ms(20)
        data = i2c.readfrom_mem(ADS1015_ADDR, 0x00, 2)
        raw = int.from_bytes(data, 'big') >> 4
        if raw > 2047:
            raw -= 4096
        return raw * 4.096 / 2048
    except:
        return 0

def send_measurement(duty_cycle, voltage, real_duty):
    """Envoi d'une mesure avec séquence"""
    global sequence
    message = f"S{sequence:03d}D{duty_cycle:03d}V{voltage:.2f}R{real_duty:.1f}E\n"
    uart.write(message)
    sequence += 1

def receive_measurement():
    """Réception et parsing d'une mesure"""
    global last_received_sequence
    
    if uart.any():
        try:
            data = uart.readline()
            if data and data.startswith(b'S'):
                # Format: S001D050V1.65R50.0E
                text = data.decode().strip()
                
                # Extraction des parties
                seq = int(text[1:4])  # Séquence
                if seq <= last_received_sequence:
                    return None  # Message déjà traité
                
                last_received_sequence = seq
                received_duty = int(text[5:8])  # Duty théorique
                voltage_str = text[9:text.index('R')]  # Tension
                real_duty_str = text[text.index('R')+1:text.index('E')]  # Duty réel
                
                return {
                    'sequence': seq,
                    'theoretical': received_duty,
                    'voltage': float(voltage_str),
                    'real_duty': float(real_duty_str)
                }
        except Exception as e:
            print(f"Erreur parsing: {e}")
    return None

def main():
    print("Pico1 - Mode synchronisé démarré")
    
    duty_cycle = 0
    direction = 1
    last_display_time = time.time()
    
    while True:
        current_time = time.time()
        
        # 1. Génération PWM
        pwm_out.duty_u16(int(duty_cycle * 65535 / 100))
        time.sleep_ms(50)  # Stabilisation filtre RC
        
        # 2. Mesure locale
        voltage = read_ads1015_ain2()
        real_duty = (voltage / 3.3) * 100
        
        # 3. Envoi de la mesure
        send_measurement(duty_cycle, voltage, real_duty)
        
        # 4. Réception et affichage
        received = receive_measurement()
        if received:
            error = received['real_duty'] - received['theoretical']
            print(f"RECU - Seq:{received['sequence']:03d} | "
                  f"Théo:{received['theoretical']:3d}% | "
                  f"Mes:{received['real_duty']:5.1f}% | "
                  f"Tens:{received['voltage']:4.2f}V | "
                  f"Erreur:{error:+.1f}%")
        
        # Affichage périodique de l'émission
        if current_time - last_display_time > 2:
            print(f"EMIS - Duty:{duty_cycle:3d}% | Tens:{voltage:4.2f}V | Réel:{real_duty:5.1f}%")
            last_display_time = current_time
        
        # Variation du duty cycle
        duty_cycle += direction
        if duty_cycle >= 100 or duty_cycle <= 0:
            direction *= -1
        
        time.sleep(0.3)  #Cycle plus lent pour stabilité

if __name__ == "__main__":
    main()