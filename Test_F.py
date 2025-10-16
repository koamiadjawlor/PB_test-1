# Test simple sur Pico 2
from machine import UART, Pin
import time

uart = UART(1, baudrate=115200, tx=Pin(8), rx=Pin(9))

print("Test UART - En attente de données...")

while True:
    if uart.any():
        data = uart.read(uart.any())
        print(f"Données reçues: {data}")
        print(f"Taille: {len(data)} bytes")
    
    time.sleep(1)