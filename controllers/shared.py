import threading
import time
import uuid
import datetime
import paho.mqtt.client as mqtt
from models.db import db
from models.iot.sensor_model import Sensor
from models.iot.actuator_model import Actuator
from flask import current_app

flask_app = None

def set_flask_app(app):
    global flask_app
    flask_app = app
    print("✅ Flask app configurada no módulo MQTT")


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
        if flask_app is None:
            print("⚠️ Aviso: Flask app não configurada!")
            return
            
        with flask_app.app_context():
            print("🔍 Buscando sensores no banco de dados...")
            for sensor in Sensor.get_sensors():
                if sensor.topic:
                    client.subscribe(sensor.topic)
                    print(f"🔔 Subscrito em {sensor.topic}")

            print("🔍 Buscando atuadores no banco de dados...")
            for actuator in Actuator.get_actuators():
                if actuator.topic_status:
                    client.subscribe(actuator.topic_status)
                    print(f"🔔 Subscrito em {actuator.topic_status}")
    else:
        print(f"❌ Falha na conexão com código {rc}")

def on_message(client, userdata, msg):
    if flask_app is None:
        print("⚠️ Ignorando mensagem - Flask app não configurada!")
        return
        
    topic = msg.topic
    payload = msg.payload.decode("utf-8").strip().upper()
    
    with flask_app.app_context():
        print(f"📨 Mensagem recebida: {topic} = {payload}")
        
        sensor = Sensor.query.filter_by(topic=topic).first()
        if sensor:
            try:
                sensor.value = float(payload)
                db.session.commit()
                print(f"📊 Sensor {sensor.name} atualizado: {payload}")
                return
            except ValueError:
                print(f"⚠️ Valor inválido para sensor: {payload}")
                pass
        

        actuator = Actuator.query.filter_by(topic_status=topic).first()
        if actuator:
            actuator.is_active = (payload == "ON")
            db.session.commit()
            print(f"⚙️ Atuador {actuator.name} atualizado: {'ON' if actuator.is_active else 'OFF'}")
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
