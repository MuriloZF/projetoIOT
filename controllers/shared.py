import threading
import time
import uuid
import paho.mqtt.client as mqtt

# --- MQTT Configuration ---
MQTT_BROKER_HOST = "broker.emqx.io"
MQTT_BROKER_PORT = 1883
MQTT_CLIENT_ID = f"flask_iot_{uuid.uuid4().hex[:8]}"

# --- Default Topics ---
TOPIC_TEMPERATURE_DEFAULT = "iot/sensor/temperatura"
TOPIC_HUMIDITY_DEFAULT = "iot/sensor/umidade"
TOPIC_VENTILATOR_CMD_DEFAULT = "iot/actuator/Ventilador/command"
TOPIC_VENTILATOR_STATUS_DEFAULT = "iot/actuator/Ventilador/status"
TOPIC_WATER_VALVE_CMD_DEFAULT = "iot/actuator/Mangueira_de_agua/command"
TOPIC_WATER_VALVE_STATUS_DEFAULT = "iot/actuator/Mangueira_de_agua/status"
TOPIC_HEATER_CMD_DEFAULT = "iot/actuator/Aquecedor/command"
TOPIC_HEATER_STATUS_DEFAULT = "iot/actuator/Aquecedor/status"

# --- Shared Resources ---
data_lock = threading.Lock()
command_history = []

# --- Dispositivos (Sensores e Atuadores) ---
devices = {
    "sensors": {
        "temperature_default": {
            "id": "sensor_temp_default",
            "name": "Sensor de Temperatura (Default)",
            "topic": TOPIC_TEMPERATURE_DEFAULT,
            "value": "N/A",
            "timestamp": "-",
            "data_type": "°C",
            "is_default": True
        },
        "humidity_default": {
            "id": "sensor_hum_default",
            "name": "Sensor de Umidade (Default)",
            "topic": TOPIC_HUMIDITY_DEFAULT,
            "value": "N/A",
            "timestamp": "-",
            "data_type": "%",
            "is_default": True
        }
    },
    "actuators": {
        "ventilator_default": {
            "id": "actuator_vent_default",
            "name": "Ventilador (Default)",
            "command_topic": TOPIC_VENTILATOR_CMD_DEFAULT,
            "status_topic": TOPIC_VENTILATOR_STATUS_DEFAULT,
            "state": "Desligado",
            "is_default": True
        },
        "water_valve_default": {
            "id": "actuator_valve_default",
            "name": "Mangueira de água (Default)",
            "command_topic": TOPIC_WATER_VALVE_CMD_DEFAULT,
            "status_topic": TOPIC_WATER_VALVE_STATUS_DEFAULT,
            "state": "Desligado",
            "is_default": True
        },
        "heater_default": {
            "id": "actuator_heater_default",
            "name": "Aquecedor (Default)",
            "command_topic": TOPIC_HEATER_CMD_DEFAULT,
            "status_topic": TOPIC_HEATER_STATUS_DEFAULT,
            "state": "Desligado",
            "is_default": True
        }
    }
}

# --- MQTT Client ---
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_CLIENT_ID)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"✅ Conectado ao broker MQTT: {MQTT_BROKER_HOST}")
        with data_lock:
            for sensor in devices["sensors"].values():
                if sensor.get("topic"):
                    client.subscribe(sensor["topic"])
                    print(f"🔔 Subscrito em {sensor['topic']}")

            for actuator in devices["actuators"].values():
                if actuator.get("status_topic"):
                    client.subscribe(actuator["status_topic"])
                    print(f"🔔 Subscrito em {actuator['status_topic']}")
    else:
        print(f"❌ Falha na conexão com código {rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode("utf-8").strip().upper()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    with data_lock:
        for sensor in devices["sensors"].values():
            if sensor["topic"] == topic:
                sensor["value"] = payload
                sensor["timestamp"] = timestamp
                print(f"📊 Sensor {sensor['name']} atualizado: {payload}")
                return
        
        for actuator in devices["actuators"].values():
            if actuator["status_topic"] == topic:
                actuator["state"] = "Ligado" if payload == "ON" else "Desligado" if payload == "OFF" else payload
                print(f"⚙️ Atuador {actuator['name']} atualizado: {actuator['state']}")
                return

        print(f"⚠️ Tópico não tratado: {topic} / Payload: {payload}")

def mqtt_thread_worker():
    print("🚀 Starting MQTT thread...")
    while True:
        try:
            mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            mqtt_client.loop_forever()
        except Exception as e:
            print(f"⚠️ MQTT error: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
            
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
