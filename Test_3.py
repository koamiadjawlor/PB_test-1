from machine import Pin, PWM, I2C, UART
import time
import ustruct

# Configuration PWM
pwm_out = PWM(Pin(16))
pwm_out.freq(1000)

# Configuration UART
uart = UART(0, baudrate=115200, tx=Pin(4), rx=Pin(5))

# Configuration I2C pour ADS1015
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
ADS1015_ADDR = 0x48

def read_h8_voltage():
    """Lit la tension sur H8 (canal AIN2)"""
    config = 0xE283  # AIN2, ± 4.096V
    i2c.writeto_mem(ADS1015_ADDR, 0x01, config.to_bytes(2, 'big'))
    time.sleep_ms(10)
    
    data = i2c.readfrom_mem(ADS1015_ADDR, 0x00, 2)
    raw = int.from_bytes(data, 'big') >> 4
    if raw > 2047:
        raw -= 4096
    
    return raw * 4.096 / 2048

def set_pwm_duty(duty_cycle):
    """Définit le rapport cyclique PWM (0-100%)"""
    duty = int(duty_cycle * 65535 / 100)
    pwm_out.duty_u16(duty)
    # Envoi de la valeur théorique par UART
    uart.write(f"{duty_cycle:.1f}\n")

def calculate_real_duty(voltage):
    """Calcule le rapport cyclique réel à partir de la tension"""
    return (voltage / 3.3) * 100

def read_uart_duty():
    """Lit et parse la valeur du duty cycle depuis l'UART de manière sécurisée"""
    if uart.any():
        try:
            data = uart.readline()
            if data:
                received_str = data.decode().strip()
                return float(received_str)
        except (ValueError, UnicodeError):
            print("Erreur de lecture UART")
    return None

def main():
    duty_cycle = 0
    direction = 1
    
    while True:
        # Mode émetteur : génération PWM
        set_pwm_duty(duty_cycle)
        
        # Mode récepteur : lecture et comparaison
        received_duty = read_uart_duty()
        if received_duty is not None:
            measured_voltage = read_h8_voltage()
            real_duty = calculate_real_duty(measured_voltage)
            error = real_duty - received_duty
            
            print(f"Pico1 - Théorique: {received_duty:.1f}%, Mesuré: {real_duty:.1f}%, Erreur: {error:.2f}%")
        
        # Variation du duty cycle pour les tests
        duty_cycle += direction
        if duty_cycle >= 100 or duty_cycle <= 0:
            direction *= -1
        
        time.sleep(0.1)

if __name__ == "__main__":
    main()