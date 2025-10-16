from machine import Pin, PWM, I2C, UART
import time
import ustruct

# Configuration PWM
pwm_out = PWM(Pin(15))  # GP15 pour sortie PWM
pwm_out.freq(1000)      # Fréquence 1kHz

# Configuration UART
uart = UART(1, baudrate=115200, tx=Pin(8), rx=Pin(9))

# Configuration I2C pour ADS1015 (lecture H8)
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
    # Tension max = 3.3V pour 100% de duty cycle
    return (voltage / 3.3) * 100

def main():
    duty_cycle = 0
    direction = 1
    
    while True:
        # Mode émetteur : génération PWM
        set_pwm_duty(duty_cycle)
        
        # Mode récepteur : lecture et comparaison
        if uart.any():
            received_duty = float(uart.readline().decode().strip())#type:ignore
            measured_voltage = read_h8_voltage()
            real_duty = calculate_real_duty(measured_voltage)
            error = real_duty - received_duty
            
            print(f"Pico1 - Théorique: {received_duty:.1f}%, Mesuré: {real_duty:.1f}%, Erreur: {error:.1f}%")
        
        # Variation du duty cycle pour les tests
        duty_cycle += direction
        if duty_cycle >= 100 or duty_cycle <= 0:
            direction *= -1
        
        time.sleep(0.1)

if __name__ == "__main__":
    main()