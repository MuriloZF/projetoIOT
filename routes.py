from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from shared import devices, data_lock, command_history
import time

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@main_bp.route("/home")
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

@main_bp.route("/dashboard")
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

@main_bp.route("/api/device_data")
def get_device_data():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    with data_lock:
        return jsonify({
            "sensors": devices["sensors"],
            "actuators": devices["actuators"],
            "command_history": command_history[-10:]
        })

@main_bp.route("/api/actuator/raw_command", methods=["POST"])
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

# Error handlers

@main_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html"), 404

@main_bp.app_errorhandler(500)
def internal_server_error(e):
    return render_template("errors/500.html"), 500

@main_bp.app_errorhandler(401)
def unauthorized_error(e):
    return render_template("errors/401.html"), 401

@main_bp.app_errorhandler(403)
def forbidden_error(e):
    return render_template("errors/403.html"), 403
