# Ce code repose principalement sur celui intitulé “Exemple de code pour récupérer la valeur du port H8”, fourni par le professeur. 
# L’IA Deepseek et Copilot ont servi à compléter certaines parties clées ainsi qu’à apporter des corrections sur la base des exigneces du projet. 
# La communication serie dans le lab 4 nous a aussi été utile pour comprendre comment cabler et échanger des données entre les deux Pico.
# Les erreurs et modifications ont été traitées grâce à GitHub Copilot Chat sur VS Code. 
# Enfin, Copilot a aussi été utilisé pour mieux comprendre les différentes fonctions et commentaires présents dans le code. »


from machine import Pin, PWM, I2C, UART
import time

# Configuration PWM (pour le mode bidirectionnel)
pwm_out = PWM(Pin(16)) # pwm output sur la pin 16
pwm_out.freq(1000) # Fréquence 1kHz

# Configuration UART
uart = UART(1, baudrate=115200, tx=Pin(8), rx=Pin(9)) #UART canal 1, vitesse de transmission 115200 bauds

# Configuration I2C pour ADS1015
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=100000) #I2C canal 1
ADS1015_ADDR = 0x48

def read_ads1015_ain2():
    """Lecture de la tension filtrée sur AIN2"""
    try:
        config = 0xE283  # AIN2, ±4.096V #Configuration de l'ADS1015 pour lire le canal AIN2
        i2c.writeto_mem(ADS1015_ADDR, 0x01, config.to_bytes(2, 'big')) #Congiguration de l'ADS1015 pour lire le canal AIN2
        time.sleep_ms(50) #Attente de la conversion
        data = i2c.readfrom_mem(ADS1015_ADDR, 0x00, 2) #Lecture des données converties
        raw = int.from_bytes(data, 'big') >> 4 #Conversion des données brutes
        if raw > 2047:
            raw -= 4096
        return raw * 4.096 / 2048
    except Exception as e:
        print(f"Erreur ADC: {e}")
        return 0

def calculate_real_duty(voltage):
    """Calcule le rapport cyclique réel à partir de la tension"""
    return max(0, min(100, (voltage / 3.3) * 100))# Calcul du duty cycle réel en pourcentage

def send_measurement(theoretical_duty, measured_duty, error):
    """Envoie les mesures à Pico 1"""
    message = f"ME:{theoretical_duty:.1f}:{measured_duty:.1f}:{error:.1f}\n"# Formatage du message
    uart.write(message)

def read_uart_theoretical():
    """Lit la valeur théorique envoyée par Pico 1"""
    if uart.any(): # Vérifie si des données sont disponibles sur l'UART
        try:
            data = uart.readline().decode().strip() #type:ignore # Lecture et décodage de la ligne reçue
            if data.startswith("TH:"):# Vérifie le format des données reçues
                return float(data[3:])# Récupère la valeur théorique envoyée
        except:
            pass
    return None

def set_pwm_duty(duty_cycle):
    """Définit le rapport cyclique PWM pour le mode bidirectionnel"""
    duty = int(max(0, min(100, duty_cycle)) * 65535 / 100)  # Conversion du pourcentage en valeur 16 bits
    pwm_out.duty_u16(duty)  # Définition du duty cycle PWM
    return duty_cycle

def main():
    print("=== Pico 2 - Mesure et Validation ===")
    print("Attente des donnees de Pico 1...")
    
    # Séquence pour le mode bidirectionnel
    bidir_sequence = [100, 80, 60, 40, 20, 0] 
    bidir_index = 0
    last_bidir_change = time.time()

    # Boucle principale
    
    while True:
        # 1. Réception de la valeur théorique de Pico 1
        theoretical_duty = read_uart_theoretical()
        
        if theoretical_duty is not None:
            # 2. Mesure de la tension filtrée
            voltage = read_ads1015_ain2()
            
            # 3. Calcul du rapport cyclique réel
            measured_duty = calculate_real_duty(voltage)
            
            # 4. Calcul de l'erreur
            error = measured_duty - theoretical_duty
            
            # 5. Envoi des résultats à Pico 1
            send_measurement(theoretical_duty, measured_duty, error)
            
            # 6. Affichage local
            print(f"Theorique: {theoretical_duty:5.1f}% | Mesure: {measured_duty:5.1f}% | Erreur: {error:+.1f}% | Tension: {voltage:.2f}V")
        
        # Mode bidirectionnel : Pico 2 génère aussi un PWM
        current_time = time.time()
        if current_time - last_bidir_change > 4:  # Toutes les 4 secondes
            bidir_duty = bidir_sequence[bidir_index] # Duty cycle pour Pico 2
            set_pwm_duty(bidir_duty) # Application du duty cycle
            bidir_voltage = read_ads1015_ain2() # Mesure de la tension filtrée
            bidir_real = calculate_real_duty(bidir_voltage) # Calcul du duty cycle réel
            print(f"Pico2 Emission - Duty: {bidir_duty}% -> Tension: {bidir_voltage:.2f}V ({bidir_real:.1f}%)") # Affichage local
            
            bidir_index = (bidir_index + 1) % len(bidir_sequence)
            last_bidir_change = current_time
        
        time.sleep(0.3)

if __name__ == "__main__":
    main()