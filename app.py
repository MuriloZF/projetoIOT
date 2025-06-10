from flask import Flask,flash, render_template, Blueprint, request, jsonify, redirect, url_for, session
from controllers.shared import mqtt_client, devices, command_history, data_lock, MQTT_BROKER_HOST, MQTT_BROKER_PORT, mqtt_thread_worker, set_flask_app

import time
import threading
from controllers.user import user_bp
from controllers.sensor import sensor_main
from controllers.actuator import actuator_main
from models.user.user import User
from models.db import db
from models.iot.actuator_model import Actuator
from models.iot.sensor_model import Sensor
import cryptography
from functools import wraps


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://termcon:termcon@localhost:3306/term_control"

def standard_admin():
    adminStandard = User.query.filter_by(username="adminStandard", password="1234", role="admin").first()
    if not adminStandard:
        adminStandard = User(username="adminStandard", password="1234", role="admin")
        db.session.add(adminStandard)
        db.session.commit()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") == None:
            flash("Acesso não autorizado", "error")
            return redirect(url_for("user.login_page"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Acesso não autorizado", "error")
            return redirect(url_for("user.login_page"))
        return f(*args, **kwargs)
    return decorated_function

def controller_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin" or session.get("role") != "controller":
            flash("Acesso não autorizado", "error")
            return redirect(url_for("user.login_page"))
        return f(*args, **kwargs)
    return decorated_function
db.init_app(app)
app.secret_key = "supersecretkey_for_iot_project"

set_flask_app(app)

# Register the user blueprint
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(sensor_main, url_prefix="/sensor")
app.register_blueprint(actuator_main, url_prefix="/actuator")

with app.app_context():
    db.create_all()
    threading.Thread(target=mqtt_thread_worker, daemon=True).start()
    print("🚀 Thread MQTT iniciado com contexto de aplicação")

@app.before_request
def verificar_autenticacao():
    rotas_livres = [
        "user.login_page",
        "user.register_user_page",
        "user.login",
        "static"
    ]
    if request.endpoint not in rotas_livres and not session.get("user_id"):
        return redirect(url_for("user.login_page"))

# --- Main Routes (Dashboard, etc.) ---
@app.route("/")
@app.route("/home")
@login_required
def home_page_dashboard():
    with data_lock:
        temp_sensor = Sensor.get_single_sensor(1)
        hum_sensor = Sensor.get_single_sensor(3)
        water_valve_actuator = Actuator.get_single_actuator(3)
        ventilator_actuator = Actuator.get_single_actuator(2)
        heater_actuator = Actuator.get_single_actuator(4)
        all_actuators = Actuator.get_actuators()
        all_sensors = Sensor.get_sensors()

    role = session.get("role", "user")

    if role == "admin":
        base_template = "baseAdmin.html"
    
    elif role == "controller":
        base_template = "baseController.html"

    else:
        base_template = "baseUser.html"   

    umidade = hum_sensor.value if hum_sensor else "N/A"
    temperatura = temp_sensor.value if temp_sensor else "N/A"
    timestamp_temp = temp_sensor.created_at if temp_sensor else "-"
    timestamp_umidade = hum_sensor.created_at if hum_sensor else "-"

    mangueira_status = water_valve_actuator.is_active if water_valve_actuator else "Desconhecido"
    ventilador_status = ventilator_actuator.is_active if ventilator_actuator else "Desconhecido"
    aquecedor_status = heater_actuator.is_active if heater_actuator else "Desconhecido"

    return render_template("home.html",
                         role=role,
                         base_template=base_template,
                         temperatura=temperatura,
                         timestamp_temp=timestamp_temp,
                         umidade=umidade,
                         timestamp_umidade=timestamp_umidade,
                         mangueira_status=mangueira_status,
                         ventilador_status=ventilador_status,
                         aquecedor_status=aquecedor_status,
                         all_actuators=all_actuators,
                         all_sensors=all_sensors,
                         command_history=command_history[-10:])


@app.route("/dashboard")
@login_required
def detailed_dashboard_page():
    with data_lock:
        all_actuators = Actuator.get_actuators()
        all_sensors = Sensor.get_sensors()

        temp_sensor = Sensor.get_single_sensor(1)
        hum_sensor = Sensor.get_single_sensor(3)

    role = session.get("role", "user", "controller")

    if role == "admin":
        base_template = "baseAdmin.html"
    
    elif role == "controller":
        base_template = "baseController.html"

    else:
        base_template = "baseUser.html"   
        
    umidade = hum_sensor.value if hum_sensor else "N/A"
    temperatura = temp_sensor.value if temp_sensor else "N/A"
    
    return render_template("dashboard.html",
                         role=role,
                         base_template=base_template,
                         all_actuators=all_actuators,
                         all_sensors=all_sensors,
                         temperatura=temperatura,
                         umidade=umidade,
                         command_history=command_history[-10:])
@app.route("/history")
@login_required
def history_page():
    role = session.get("role", "user", "controller")
    if role == "admin":
        base_template = "baseAdmin.html"
    elif role == "controller":
        base_template = "baseController.html"
    else:
        base_template = "baseUser.html"        
    
    return render_template("history_data.html",
                         role=role,
                         base_template=base_template,
                         command_history=command_history[-10:])

# --- API Endpoints ---
@app.route("/api/device_data")
@login_required
def get_device_data():
    with data_lock:
        return jsonify({
            "sensors": devices["sensors"],
            "actuators": devices["actuators"],
            "command_history": command_history[-10:]
        })

@app.route("/api/actuator/raw_command", methods=["POST"])
@login_required
def actuator_raw_command():
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
@login_required
def actuator_command():
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
    with app.app_context():
        standard_admin()
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)