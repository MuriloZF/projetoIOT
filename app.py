from flask import Flask,flash, render_template, Blueprint, request, jsonify, redirect, url_for, session
import paho.mqtt.client as mqtt
import threading
import time
import json
import uuid
from actuator import Blueprint as actuator_bp
# Import the user blueprint and user/admin dictionaries from user.py
from user import user_bp, users_dict, admins_dict

app = Flask(__name__)
app.secret_key = "supersecretkey_for_iot_project"

# Register the user blueprint
app.register_blueprint(user_bp, url_prefix="/user")

# --- MQTT Configuration ---
MQTT_BROKER_HOST = "broker.emqx.io"
MQTT_BROKER_PORT = 1883
MQTT_CLIENT_ID = f"flask_iot_{uuid.uuid4().hex[:8]}"

# --- MQTT Topics (Initial/Default) ---
TOPIC_TEMPERATURE_DEFAULT = "iot/sensor/temperatura"
TOPIC_HUMIDITY_DEFAULT = "iot/sensor/umidade"
TOPIC_VENTILATOR_CMD_DEFAULT = "iot/actuator/Ventilador/command"
TOPIC_VENTILATOR_STATUS_DEFAULT = "iot/actuator/Ventilador/status"
TOPIC_WATER_VALVE_CMD_DEFAULT = "iot/actuator/Mangueira_de_agua/command"
TOPIC_WATER_VALVE_STATUS_DEFAULT = "iot/actuator/Mangueira_de_agua/status"
TOPIC_HEATER_CMD_DEFAULT = "iot/actuator/Aquecedor/command"
TOPIC_HEATER_STATUS_DEFAULT = "iot/actuator/Aquecedor/status"

# --- Device Initialization & Command History ---
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

command_history = []
data_lock = threading.Lock()

# --- MQTT Client Setup ---
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_CLIENT_ID)




def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"✅ Connected to MQTT Broker: {MQTT_BROKER_HOST}")
        with data_lock:
            # Subscribe to all sensor topics
            for sensor_info in devices["sensors"].values():
                if sensor_info.get("topic"):
                    client.subscribe(sensor_info["topic"])
                    print(f"🔔 Subscribed to sensor topic: {sensor_info['topic']} for {sensor_info['name']}")
            
            # Subscribe to all actuator status topics
            for actuator_info in devices["actuators"].values():
                if actuator_info.get("status_topic"):
                    client.subscribe(actuator_info["status_topic"])
                    print(f"🔔 Subscribed to actuator status topic: {actuator_info['status_topic']} for {actuator_info['name']}")
    else:
        print(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode("utf-8").strip().upper()  # Normalize to uppercase
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    updated = False
    
    with data_lock:
        # Check if this is a sensor update
        for sensor_info in devices["sensors"].values():
            if sensor_info.get("topic") == topic:
                sensor_info["value"] = payload
                sensor_info["timestamp"] = timestamp
                print(f"📊 Sensor update for {sensor_info['name']}: {payload}{sensor_info.get('data_type','')}")
                updated = True
                break
        
        if updated:
            return

        # Check if this is an actuator status update
        for actuator_info in devices["actuators"].values():
            if actuator_info.get("status_topic") == topic:
                # Interpret both raw (ON/OFF) and translated (Ligado/Desligado) states
                if payload == "ON":
                    actuator_info["state"] = "Ligado"
                elif payload == "OFF":
                    actuator_info["state"] = "Desligado"
                else:
                    actuator_info["state"] = payload.capitalize()
                
                print(f"⚙️ Actuator status update for {actuator_info['name']}: {actuator_info['state']}")
                updated = True
                break
        
        if not updated:
            print(f"⚠️ Received message for unhandled topic: {topic} with payload: {payload}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def mqtt_thread_worker():
    print("🚀 Starting MQTT thread...")
    while True:
        try:
            mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            mqtt_client.loop_forever()
        except Exception as e:
            print(f"⚠️ MQTT error: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)

threading.Thread(target=mqtt_thread_worker, daemon=True).start()

sensor_bp_main = Blueprint("sensor_main", __name__, template_folder="templates", url_prefix="/sensor")

@sensor_bp_main.route("/register", methods=["GET", "POST"])
def register_sensor_page():
    if session.get("privilegio") != 1:
        return redirect(url_for("user.login_page"))
    
    if request.method == "POST":
        sensor_name = request.form.get("name")
        sensor_topic = request.form.get("topic")
        sensor_type = request.form.get("type", "")
        
        if not all([sensor_name, sensor_topic]):
            flash("Nome e tópico do sensor são obrigatórios", "error")
            return redirect(url_for("sensor_main.register_sensor_page"))
        
        with data_lock:
            # Check if topic already exists
            if any(s["topic"] == sensor_topic for s in devices["sensors"].values()):
                flash("Já existe um sensor com este tópico MQTT", "error")
                return redirect(url_for("sensor_main.register_sensor_page"))
            
            sensor_id = f"sensor_{uuid.uuid4().hex[:6]}"
            devices["sensors"][sensor_id] = {
                "id": sensor_id,
                "name": sensor_name,
                "topic": sensor_topic,
                "value": "N/A",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "data_type": sensor_type,
                "is_default": False
            }
            
            # Subscribe to MQTT topic
            mqtt_client.subscribe(sensor_topic)
            print(f"🔔 Subscribed to new sensor topic: {sensor_topic}")
            
            flash(f"Sensor '{sensor_name}' registrado com sucesso!", "success")
            return redirect(url_for("sensor_main.manage_sensors_page"))
    
    return render_template("register_sensor.html")

@sensor_bp_main.route("/manage")
def manage_sensors_page():
    if session.get("privilegio") != 1:
        return redirect(url_for("user.login_page"))
    
    with data_lock:
        sensors_list = list(devices["sensors"].values())
        # Sort by timestamp (newest first)
        sensors_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return render_template("manage_sensor.html", devices=sensors_list)

@sensor_bp_main.route("/delete/<sensor_id>", methods=["POST"])
def delete_sensor(sensor_id):
    if session.get("privilegio") != 1:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    with data_lock:
        if sensor_id in devices["sensors"] and not devices["sensors"][sensor_id].get("is_default", False):
            topic_to_unsubscribe = devices["sensors"][sensor_id].get("topic")
            if topic_to_unsubscribe:
                mqtt_client.unsubscribe(topic_to_unsubscribe)
                print(f"🔕 Unsubscribed from sensor topic: {topic_to_unsubscribe}")
            del devices["sensors"][sensor_id]
            print(f"🗑️ Deleted sensor: {sensor_id}")
        else:
            print(f"⚠️ Attempted to delete non-existent or default sensor: {sensor_id}")
    return redirect(url_for("sensor_main.manage_sensors_page"))
@sensor_bp_main.route("/edit/<sensor_id>", methods=["GET", "POST"])
def edit_sensor(sensor_id):
    if session.get("privilegio") != 1:
        flash("Acesso não autorizado", "error")
        return redirect(url_for("user.login_page"))
    
    with data_lock:
        sensor = devices["sensors"].get(sensor_id)
        if not sensor:
            flash("Sensor não encontrado!", "error")
            return redirect(url_for("sensor_main.manage_sensors_page"))
        
        if request.method == "POST":
            sensor_name = request.form.get("sensor_name", "").strip()
            data_type = request.form.get("data_type", "").strip()
            
            if not sensor_name:
                flash("Nome do sensor é obrigatório!", "error")
                return render_template("edit_sensor.html", sensor=sensor)
            
            # Update sensor data
            sensor["name"] = sensor_name
            sensor["data_type"] = data_type
            sensor["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            flash("Sensor atualizado com sucesso!", "success")
            return redirect(url_for("sensor_main.manage_sensors_page"))
    
    return render_template("edit_sensor.html", sensor=sensor)

app.register_blueprint(sensor_bp_main)

# --- Actuator Management Blueprint ---
actuator_bp_main = Blueprint("actuator_main", __name__, template_folder="templates", url_prefix="/actuator")

@actuator_bp_main.route("/register", methods=["GET", "POST"])
def register_actuator_page():
    if session.get("privilegio") != 1:
        flash("Acesso não autorizado", "error")
        return redirect(url_for("user.login_page"))
    
    if request.method == "POST":
        actuator_name = request.form.get("name", "").strip()
        cmd_topic = request.form.get("command_topic", "").strip()
        status_topic = request.form.get("status_topic", "").strip()
        
        if not actuator_name or not cmd_topic:
            flash("Nome e tópico de comando são obrigatórios", "error")
            return render_template("register_actuator.html")
        
        with data_lock:
            # Check if command topic already exists
            if any(a["command_topic"] == cmd_topic for a in devices["actuators"].values()):
                flash("Já existe um atuador com este tópico de comando", "error")
                return render_template("register_actuator.html")
            
            actuator_id = f"actuator_{uuid.uuid4().hex[:6]}"
            devices["actuators"][actuator_id] = {
                "id": actuator_id,
                "name": actuator_name,
                "command_topic": cmd_topic,
                "status_topic": status_topic,
                "state": "Desligado",
                "is_default": False,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Subscribe to status topic if provided
            if status_topic:
                mqtt_client.subscribe(status_topic)
                print(f"🔔 Subscribed to actuator status topic: {status_topic}")
            
            flash(f"Atuador '{actuator_name}' registrado com sucesso!", "success")
            return redirect(url_for("actuator_main.manage_actuators_page"))
    
    return render_template("register_actuator.html")

@actuator_bp_main.route("/manage")
def manage_actuators_page():
    if session.get("privilegio") != 1:
        flash("Acesso não autorizado", "error")
        return redirect(url_for("user.login_page"))
    
    with data_lock:
        actuators_list = sorted(
            devices["actuators"].values(),
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
    
    return render_template("manage_actuator.html", devices=actuators_list)

@actuator_bp_main.route("/edit/<actuator_id>", methods=["GET", "POST"])
def edit_actuator_page(actuator_id):
    if session.get("privilegio") != 1:
        flash("Acesso não autorizado", "error")
        return redirect(url_for("user.login_page"))
    
    with data_lock:
        actuator = devices["actuators"].get(actuator_id)
        if not actuator:
            flash("Atuador não encontrado", "error")
            return redirect(url_for("actuator_main.manage_actuators_page"))
        
        if request.method == "POST":
            actuator_name = request.form.get("name", "").strip()
            cmd_topic = request.form.get("command_topic", "").strip()
            status_topic = request.form.get("status_topic", "").strip()
            
            if not actuator_name or not cmd_topic:
                flash("Nome e tópico de comando são obrigatórios", "error")
                return render_template("edit_actuator.html", actuator=actuator)
            
            # Unsubscribe from old status topic if it changed
            if actuator["status_topic"] and actuator["status_topic"] != status_topic:
                mqtt_client.unsubscribe(actuator["status_topic"])
                print(f"🔕 Unsubscribed from old status topic: {actuator['status_topic']}")
            
            # Update actuator data
            actuator["name"] = actuator_name
            actuator["command_topic"] = cmd_topic
            actuator["status_topic"] = status_topic
            actuator["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Subscribe to new status topic if provided
            if status_topic:
                mqtt_client.subscribe(status_topic)
                print(f"🔔 Subscribed to new status topic: {status_topic}")
            
            flash("Atuador atualizado com sucesso!", "success")
            return redirect(url_for("actuator_main.manage_actuators_page"))
    
    return render_template("edit_actuator.html", actuator=actuator)

@actuator_bp_main.route("/toggle/<actuator_id>", methods=["POST"])
def toggle_actuator(actuator_id):
    if session.get("privilegio") != 1:
        return jsonify({"status": "error", "message": "Não autorizado"}), 403
    
    with data_lock:
        actuator = devices["actuators"].get(actuator_id)
        if not actuator:
            return jsonify({"status": "error", "message": "Atuador não encontrado"}), 404
        
        new_state = "Ligado" if actuator["state"] == "Desligado" else "Desligado"
        actuator["state"] = new_state
        
        # Send MQTT command (using ON/OFF for compatibility)
        mqtt_state = "ON" if new_state == "Ligado" else "OFF"
        mqtt_client.publish(actuator["command_topic"], mqtt_state)
        
        # Update timestamp
        actuator["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify({
            "status": "success",
            "new_state": new_state,
            "actuator_id": actuator_id
        })

@actuator_bp_main.route("/delete/<actuator_id>", methods=["POST"])
def delete_actuator(actuator_id):
    if session.get("privilegio") != 1:
        flash("Acesso não autorizado", "error")
        return redirect(url_for("user.login_page"))
    
    with data_lock:
        actuator = devices["actuators"].get(actuator_id)
        if not actuator:
            flash("Atuador não encontrado", "error")
            return redirect(url_for("actuator_main.manage_actuators_page"))
        
        if actuator.get("is_default", False):
            flash("Não é possível remover atuadores padrão", "error")
            return redirect(url_for("actuator_main.manage_actuators_page"))
        
        # Unsubscribe from status topic if exists
        if actuator["status_topic"]:
            mqtt_client.unsubscribe(actuator["status_topic"])
            print(f"🔕 Unsubscribed from status topic: {actuator['status_topic']}")
        
        # Remove actuator
        actuator_name = actuator["name"]
        del devices["actuators"][actuator_id]
        
        flash(f"Atuador '{actuator_name}' removido com sucesso", "success")
        print(f"🗑️ Deleted actuator: {actuator_id}")
    
    return redirect(url_for("actuator_main.manage_actuators_page"))

app.register_blueprint(actuator_bp_main)

# --- Main Routes (Dashboard, etc.) ---
@app.route("/")
@app.route("/home")
def home_page_dashboard():
    if "user_id" not in session:
        return redirect(url_for("user.login_page"))
    with data_lock:
        temp_sensor = devices["sensors"].get("temperature_default", {})
        hum_sensor = devices["sensors"].get("humidity_default", {})
        water_valve_actuator = devices["actuators"].get("water_valve_default", {})
        ventilator_actuator = devices["actuators"].get("ventilator_default", {})
        heater_actuator = devices["actuators"].get("heater_default", {})
        all_actuators = list(devices["actuators"].values())
        all_sensors = list(devices["sensors"].values())
    
    privilegio = session.get("privilegio", 0)
    
    return render_template("home.html",
                         privilegio=privilegio,
                         temperatura=temp_sensor.get("value", "N/A"),
                         timestamp_temp=temp_sensor.get("timestamp", "-"),
                         umidade=hum_sensor.get("value", "N/A"),
                         timestamp_umidade=hum_sensor.get("timestamp", "-"),
                         mangueira_status=water_valve_actuator.get("state", "Desconhecido"),
                         ventilador_status=ventilator_actuator.get("state", "Desconhecido"),
                         aquecedor_status=heater_actuator.get("state", "Desconhecido"),
                         all_actuators=all_actuators,
                         all_sensors=all_sensors,
                         command_history=command_history[-10:])

@app.route("/dashboard")
def detailed_dashboard_page():
    if "user_id" not in session:
        return redirect(url_for("user.login_page"))
    with data_lock:
        all_actuators = list(devices["actuators"].values())
        all_sensors = list(devices["sensors"].values())
    privilegio = session.get("privilegio", 0)
    return render_template("dashboard.html",
                         privilegio=privilegio,
                         all_actuators=all_actuators,
                         all_sensors=all_sensors,
                         temperatura=devices["sensors"].get("temperature_default", {}).get("value", "N/A"),
                         umidade=devices["sensors"].get("humidity_default", {}).get("value", "N/A"),
                         command_history=command_history[-10:])

# --- API Endpoints ---
@app.route("/api/device_data")
def get_device_data():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    with data_lock:
        return jsonify({
            "sensors": devices["sensors"],
            "actuators": devices["actuators"],
            "command_history": command_history[-10:]
        })

@app.route("/api/actuator/raw_command", methods=["POST"])
def actuator_raw_command():
    if "user_id" not in session or session.get("privilegio") != 1:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    data = request.get_json()
    actuator_id = data.get("actuator_id")
    raw_command = data.get("raw_command", "").upper()
    
    if not actuator_id or raw_command not in ["ON", "OFF"]:
        return jsonify({"status": "error", "message": "Invalid request"}), 400
    
    with data_lock:
        target_actuator = None
        for act_key, act_info in devices["actuators"].items():
            if act_info["id"] == actuator_id:
                target_actuator = act_info
                break
        
        if target_actuator and target_actuator.get("command_topic"):
            # Publish raw command
            mqtt_client.publish(target_actuator["command_topic"], raw_command)
            
            # Update state optimistically
            new_state = "Ligado" if raw_command == "ON" else "Desligado"
            target_actuator["state"] = new_state
            
            # Log command history
            log_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "user": session.get("user_id", "Unknown"),
                "actuator_name": target_actuator.get("name", actuator_id),
                "command": new_state,
                "topic": target_actuator["command_topic"],
                "payload": raw_command
            }
            command_history.append(log_entry)
            if len(command_history) > 50:
                command_history.pop(0)
                
            print(f"✅ Raw command {raw_command} sent to {target_actuator['name']}")
            return jsonify({
                "status": "success", 
                "message": f"Raw command {raw_command} sent",
                "new_state": new_state
            })
        else:
            return jsonify({"status": "error", "message": "Actuator not found"}), 404

# --- Error Handlers ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("errors/500.html"), 500

@app.errorhandler(401)
def unauthorized_error(e):
    return render_template("errors/401.html"), 401

@app.errorhandler(403)
def forbidden_error(e):
    return render_template("errors/403.html"), 403

if __name__ == "__main__":
    print("🌐 Starting IoT Dashboard...")
    app.run(host="0.0.0.0", port=5000, debug=True)