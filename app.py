from flask import Flask,flash, render_template, Blueprint, request, jsonify, redirect, url_for, session

from controllers.shared import mqtt_client, devices, command_history, data_lock, MQTT_BROKER_HOST, MQTT_BROKER_PORT, mqtt_thread_worker

import time
import threading
# Import the user blueprint and user/admin dictionaries from user.py
from controllers.user import user_bp
from controllers.sensor import sensor_main
from controllers.actuator import actuator_main


app = Flask(__name__)
app.secret_key = "supersecretkey_for_iot_project"

# Register the user blueprint
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(sensor_main, url_prefix="/sensor")
app.register_blueprint(actuator_main, url_prefix="/actuator")


threading.Thread(target=mqtt_thread_worker, daemon=True).start()

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
        
@app.route("/api/actuator/command", methods=["POST"])
def actuator_command():
    if "user_id" not in session or session.get("privilegio") != 1:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    data = request.get_json()
    actuator_id = data.get("actuator_id")
    command = data.get("command", "").lower()

    if not actuator_id or command not in ["ligar", "desligar"]:
        return jsonify({"status": "error", "message": "Invalid request"}), 400

    with data_lock:
        target_actuator = None
        for act_key, act_info in devices["actuators"].items():
            if act_info["id"] == actuator_id:
                target_actuator = act_info
                break

        if target_actuator and target_actuator.get("command_topic"):
            mqtt_payload = "ON" if command == "ligar" else "OFF"
            mqtt_client.publish(target_actuator["command_topic"], mqtt_payload)

            new_state = "Ligado" if command == "ligar" else "Desligado"
            target_actuator["state"] = new_state

            log_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "user": session.get("user_id", "Unknown"),
                "actuator_name": target_actuator.get("name", actuator_id),
                "command": new_state,
                "topic": target_actuator["command_topic"],
                "payload": mqtt_payload
            }
            command_history.append(log_entry)
            if len(command_history) > 50:
                command_history.pop(0)

            print(f"✅ Comando '{command}' enviado para {target_actuator['name']}")
            return jsonify({
                "status": "success",
                "message": f"Comando '{command}' enviado",
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