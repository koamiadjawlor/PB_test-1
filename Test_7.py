from machine import Pin, PWM, I2C, UART
import time

# Configuration PWM
pwm_out = PWM(Pin(16))
pwm_out.freq(1000)  # Fréquence 1kHz

# Configuration UART
uart = UART(1, baudrate=115200, tx=Pin(8), rx=Pin(9))

# Configuration I2C pour ADS1015
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=100000)
ADS1015_ADDR = 0x48

def read_ads1015_ain2():
    """Lecture de la tension filtrée sur AIN2"""
    try:
        config = 0xE283  # AIN2, ±4.096V
        i2c.writeto_mem(ADS1015_ADDR, 0x01, config.to_bytes(2, 'big'))
        time.sleep_ms(50)
        data = i2c.readfrom_mem(ADS1015_ADDR, 0x00, 2)
        raw = int.from_bytes(data, 'big') >> 4
        if raw > 2047:
            raw -= 4096
        return raw * 4.096 / 2048
    except Exception as e:
        print(f"Erreur ADC: {e}")
        return 0

def set_pwm_duty(duty_cycle):
    """Définit le rapport cyclique PWM et envoie la valeur théorique"""
    duty = int(max(0, min(100, duty_cycle)) * 65535 / 100)
    pwm_out.duty_u16(duty)
    # Envoi de la valeur théorique à Pico 2
    uart.write(f"TH:{duty_cycle:.1f}\n")
    return duty_cycle

def calculate_real_duty(voltage):
    """Calcule le rapport cyclique réel à partir de la tension"""
    return max(0, min(100, (voltage / 3.3) * 100))

def read_uart_measurement():
    """Lit les mesures envoyées par Pico 2"""
    if uart.any():
        try:
            data = uart.readline().decode().strip() #type:ignore
            if data.startswith("ME:"):
                parts = data.split(":")
                received_duty = float(parts[1])
                measured_duty = float(parts[2])
                error = float(parts[3])
                return received_duty, measured_duty, error
        except Exception as e:
            print(f"Erreur lecture UART: {e}")
    return None, None, None

def main():
    print("=== Pico 1 - Générateur PWM Principal ===")
    print("Duty | Tension | Réel | Erreur Pico2")
    print("-" * 45)
    
    # Séquence de tests des rapports cycliques
    test_sequence = [0, 10, 25, 50, 75, 90, 100]
    current_index = 0
    last_change = time.time()
    
    while True:
        current_time = time.time()
        
        # Changement du duty cycle toutes les 3 secondes
        if current_time - last_change > 3:
            duty_cycle = test_sequence[current_index]
            
            # 1. Génération du signal PWM
            set_pwm_duty(duty_cycle)
            time.sleep(0.1)  # Stabilisation du filtre RC
            
            # 2. Mesure locale de la tension filtrée
            voltage = read_ads1015_ain2()
            real_duty_local = calculate_real_duty(voltage)
            
            # 3. Réception des mesures de Pico 2
            received_duty, measured_duty, error_pico2 = read_uart_measurement()
            
            # 4. Affichage des résultats
            if received_duty is not None:
                print(f"{duty_cycle:3.0f}% | {voltage:6.2f}V | {real_duty_local:4.1f}% | Erreur Pico2: {error_pico2:+.1f}%")
            else:
                print(f"{duty_cycle:3.0f}% | {voltage:6.2f}V | {real_duty_local:4.1f}% | En attente Pico2...")
            
            # Passage au duty cycle suivant
            current_index = (current_index + 1) % len(test_sequence)
            last_change = current_time
        
        time.sleep(0.1)

if __name__ == "__main__":
    main()