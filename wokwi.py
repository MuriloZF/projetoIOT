# MicroPython code for ESP32 in Wokwi
# This code connects to WiFi, an MQTT broker, publishes sensor data (temperature and humidity),
# and subscribes to topics to control actuators (Ventilador, Mangueira de água) based on commands from the dashboard.

from machine import Pin, PWM
import dht
import time
import network
from umqtt.simple import MQTTClient
import ubinascii
import json # For potential future use with JSON payloads

# --- Configuration ---
# WiFi Credentials (Wokwi uses Wokwi-GUEST with no password)
SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""

# MQTT Broker Configuration (matches dashboard.html defaults)
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883 # Default MQTT port
# CLIENT_ID = "esp32_wokwi_" + ubinascii.hexlify(network.WLAN(network.STA_IF).config("mac")[:3]).decode()
# Wokwi doesn't easily provide MAC for client ID, using a fixed one or a simpler random one
CLIENT_ID = "esp32_wokwi_client_iot_project"

# MQTT Topics (must match dashboard.html and backend logic)
TOPIC_SENSOR_TEMP = b"iot/sensor/temperatura"
TOPIC_SENSOR_HUMIDITY = b"iot/sensor/umidade"

TOPIC_ACTUATOR_VENTILADOR_CMD = b"iot/actuator/Ventilador/command"
TOPIC_ACTUATOR_MANGUEIRA_CMD = b"iot/actuator/Mangueira_de_agua/command" # Note: 'Mangueira_de_agua' to match dashboard's JS topic generation

# --- Hardware Pins ---
# Actuators
ventilador_pin = Pin(27, Pin.OUT)  # Ventilador (LED in Wokwi)
mangueira_servo_pin = Pin(12)     # Mangueira (Servo Motor)
servo = PWM(mangueira_servo_pin, freq=50)

# Sensors
dht_sensor_pin = Pin(21)
dht_sensor = dht.DHT11(dht_sensor_pin)

# --- Global Variables ---
mqtt_client = None
last_sensor_publish_time = 0
SENSOR_PUBLISH_INTERVAL = 5  # seconds

# --- Servo Control Functions (Mangueira) ---
def abrir_mangueira():
    servo.duty(115)  # Adjust duty cycle for fully open (e.g., 115-120 for 180 degrees)
    print("Mangueira Aberta (Ligada)")

def fechar_mangueira():
    servo.duty(30)   # Adjust duty cycle for fully closed (e.g., 20-30 for 0 degrees)
    print("Mangueira Fechada (Desligada)")

# --- MQTT Callback Function ---
def mqtt_subscription_callback(topic, msg):
    print(f"Received message: Topic='{topic.decode()}', Message='{msg.decode()}'")
    command = msg.decode().lower()
    topic_str = topic.decode()

    if topic_str == TOPIC_ACTUATOR_VENTILADOR_CMD.decode():
        if command == "ligar":
            ventilador_pin.on()
            print("Ventilador Ligado")
        elif command == "desligar":
            ventilador_pin.off()
            print("Ventilador Desligado")
        else:
            print(f"Comando desconhecido para Ventilador: {command}")

    elif topic_str == TOPIC_ACTUATOR_MANGUEIRA_CMD.decode():
        if command == "ligar":
            abrir_mangueira()
        elif command == "desligar":
            fechar_mangueira()
        else:
            print(f"Comando desconhecido para Mangueira: {command}")
    else:
        print(f"Tópico não tratado: {topic_str}")

# --- WiFi Connection ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Conectando à rede WiFi {SSID}...")
        wlan.connect(SSID, WIFI_PASSWORD)
        timeout = 10
        while not wlan.isconnected() and timeout > 0:
            print(".", end="")
            time.sleep(1)
            timeout -= 1
    if wlan.isconnected():
        print(f"\nConectado ao WiFi! Endereço IP: {wlan.ifconfig()[0]}")
        return True
    else:
        print("\nFalha ao conectar ao WiFi.")
        return False

# --- MQTT Connection ---
def connect_mqtt():
    global mqtt_client
    try:
        mqtt_client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT)
        mqtt_client.set_callback(mqtt_subscription_callback)
        mqtt_client.connect()
        print(f"Conectado ao MQTT Broker: {MQTT_BROKER}")
        # Subscribe to actuator command topics
        mqtt_client.subscribe(TOPIC_ACTUATOR_VENTILADOR_CMD)
        print(f"Subscrito a: {TOPIC_ACTUATOR_VENTILADOR_CMD.decode()}")
        mqtt_client.subscribe(TOPIC_ACTUATOR_MANGUEIRA_CMD)
        print(f"Subscrito a: {TOPIC_ACTUATOR_MANGUEIRA_CMD.decode()}")
        return True
    except OSError as e:
        print(f"Erro ao conectar ao MQTT Broker: {e}")
        return False
    except Exception as e:
        print(f"Exceção genérica ao conectar ao MQTT: {e}")
        return False

# --- Main Loop ---
def main():
    global last_sensor_publish_time
    global mqtt_client

    # Initial setup
    ventilador_pin.off()
    fechar_mangueira() # Start with mangueira closed

    if not connect_wifi():
        print("Não foi possível conectar ao WiFi. Reiniciando em 10s...")
        time.sleep(10)
        machine.reset() # Or handle error differently

    if not connect_mqtt():
        print("Não foi possível conectar ao MQTT. Reiniciando em 10s...")
        time.sleep(10)
        machine.reset() # Or handle error differently

    print("Setup completo. Iniciando loop principal...")

    while True:
        try:
            current_time = time.time()

            # Check for incoming MQTT messages
            if mqtt_client:
                mqtt_client.check_msg()

            # Publish sensor data periodically
            if (current_time - last_sensor_publish_time) >= SENSOR_PUBLISH_INTERVAL:
                dht_sensor.measure()
                temp = dht_sensor.temperature()
                hum = dht_sensor.humidity()
                print(f"Temperatura: {temp}°C, Umidade: {hum}%")

                if mqtt_client:
                    try:
                        mqtt_client.publish(TOPIC_SENSOR_TEMP, str(temp).encode())
                        print(f"Publicado no tópico {TOPIC_SENSOR_TEMP.decode()}: {temp}°C")
                        mqtt_client.publish(TOPIC_SENSOR_HUMIDITY, str(hum).encode())
                        print(f"Publicado no tópico {TOPIC_SENSOR_HUMIDITY.decode()}: {hum}%")
                        last_sensor_publish_time = current_time
                    except Exception as e:
                        print(f"Erro ao publicar dados dos sensores: {e}")
                        # Attempt to reconnect if publishing fails
                        print("Tentando reconectar ao MQTT...")
                        if connect_mqtt():
                            print("Reconectado ao MQTT com sucesso.")
                        else:
                            print("Falha ao reconectar ao MQTT. Tentando novamente no próximo ciclo.")
                            time.sleep(5) # Wait before retrying connection in the main loop
                            continue # Skip to next iteration to retry connection
                else:
                    print("Cliente MQTT não conectado. Tentando reconectar...")
                    if connect_mqtt():
                         print("Reconectado ao MQTT com sucesso.")
                    else:
                        print("Falha ao reconectar ao MQTT. Tentando novamente no próximo ciclo.")
                        time.sleep(5)
                        continue

            time.sleep(1)  # Main loop delay

        except OSError as e:
            print(f"Erro de OSError no loop principal: {e}")
            print("Tentando reconectar WiFi e MQTT...")
            if connect_wifi():
                connect_mqtt()
            else:
                print("Falha ao reconectar WiFi. Reiniciando em 10s...")
                time.sleep(10)
                machine.reset()
            time.sleep(5) # wait before next loop iteration
        except Exception as e:
            print(f"Erro inesperado no loop principal: {e}")
            time.sleep(5)
            # Consider a soft reset or more robust error handling here
            # machine.reset()

if __name__ == "__main__":
    main()

