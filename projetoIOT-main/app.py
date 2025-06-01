from flask import Flask, flash, render_template, Blueprint, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_required, current_user
import time
import threading
import os

# Import database and models
from models.models import db, User, Sensor, Actuator, DeviceLog

# Import MQTT related components
from controllers.shared import mqtt_client, data_lock, devices, command_history, MQTT_BROKER_HOST, MQTT_BROKER_PORT, mqtt_thread_worker

# Import blueprints
from controllers.user import user_bp
from controllers.sensor import sensor_main
from controllers.actuator import actuator_main

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey_for_iot_project") # Use env var or default

# --- Database Configuration (MySQL or SQLite) ---

# Check for MySQL environment variables
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
MYSQL_HOST = os.environ.get("MYSQL_HOST")
MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306") # Default MySQL port
MYSQL_DB = os.environ.get("MYSQL_DB")

if MYSQL_USER and MYSQL_PASSWORD and MYSQL_HOST and MYSQL_DB:
    # Use MySQL if all variables are set
    print("Configuring database connection for MySQL...")
    app.config["SQLALCHEMY_DATABASE_URI"] = \
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    print(f"Using MySQL database: {MYSQL_DB} on {MYSQL_HOST}:{MYSQL_PORT}")
else:
    # Fallback to SQLite
    print("MySQL environment variables not fully set. Falling back to SQLite.")
    basedir = os.path.abspath(os.path.dirname(__file__))
    sqlite_path = os.path.join(basedir, "database.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + sqlite_path
    print(f"Using SQLite database at: {sqlite_path}")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# --- End Database Configuration ---

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "user.login_page" # Redirect to login page if unauthorized
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    try:
        # Use Session.get() for SQLAlchemy 2.0 compatibility
        return db.session.get(User, int(user_id))
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
        return None

# Register blueprints (keeping original prefixes)
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(sensor_main, url_prefix="/sensor")
app.register_blueprint(actuator_main, url_prefix="/actuator")

# Start MQTT thread
threading.Thread(target=mqtt_thread_worker, daemon=True).start() # Removed args=(app,)

# --- Main Routes (Dashboard, etc.) ---
@app.route("/")
@app.route("/home")
@login_required # Protect route
def home_page_dashboard():
    # Fetch devices from DB for structure/metadata
    db_actuators = Actuator.query.all()
    db_sensors = Sensor.query.all()
    
    # Fetch real-time data from MQTT cache
    with data_lock:
        rt_actuators_cache = devices["actuators"].copy()
        rt_sensors_cache = devices["sensors"].copy()
        current_command_history = command_history[-10:].copy()

    # Combine DB data with real-time cache for display
    display_actuators = {}
    for act in db_actuators:
        rt_data = next((rt for rt in rt_actuators_cache.values() if rt.get("command_topic") == act.command_topic), None)
        # Use actuator_id_str as key for consistency with JS/template if needed, but pass DB ID
        display_actuators[act.actuator_id_str] = {
            "id": act.id, # Pass the numerical DB ID
            "actuator_id_str": act.actuator_id_str, # Keep the string ID if used elsewhere
            "name": act.name,
            "state": rt_data.get("state", "Desconhecido") if rt_data else "Desconhecido", # Simplified state logic
            "timestamp": rt_data.get("timestamp", "-") if rt_data else "-",
            "command_topic": act.command_topic,
            "state_topic": act.state_topic
        }
        
    display_sensors = {}
    for sen in db_sensors:
        rt_data = next((rt for rt in rt_sensors_cache.values() if rt.get("topic") == sen.topic), None)
        # Use sensor_id_str as key
        display_sensors[sen.sensor_id_str] = {
            "id": sen.id,
            "sensor_id_str": sen.sensor_id_str,
            "name": sen.name,
            "value": rt_data.get("value", "N/A") if rt_data else "N/A",
            "timestamp": rt_data.get("timestamp", "-") if rt_data else "-",
            "unit": sen.unit
        }

    # Find specific default devices for cards using their string IDs
    temp_sensor_display = display_sensors.get("sensor_temperature_default", {})
    hum_sensor_display = display_sensors.get("sensor_humidity_default", {})
    water_valve_display = display_actuators.get("actuator_mangueira_default", {})
    ventilator_display = display_actuators.get("actuator_ventilador_default", {})
    heater_display = display_actuators.get("actuator_aquecedor_default", {})

    return render_template("home.html",
                         privilegio=current_user.privilegio, # Use is_admin boolean
                         # Pass the full sensor/actuator dictionaries
                         temperatura=temp_sensor_display,
                         umidade=hum_sensor_display,
                         mangueira=water_valve_display,
                         ventilador=ventilator_display,
                         aquecedor=heater_display,
                         # Pass all devices if needed for other parts of the template
                         all_actuators=list(display_actuators.values()), 
                         all_sensors=list(display_sensors.values()),
                         command_history=current_command_history)

@app.route("/dashboard")
@login_required # Protect route
def detailed_dashboard_page():
    # Similar logic as home_page_dashboard to fetch and combine data
    db_actuators = Actuator.query.all()
    db_sensors = Sensor.query.all()
    with data_lock:
        rt_actuators_cache = devices["actuators"].copy()
        rt_sensors_cache = devices["sensors"].copy()
        current_command_history = command_history[-10:].copy()

    display_actuators = []
    for act in db_actuators:
        rt_data = next((rt for rt in rt_actuators_cache.values() if rt.get("command_topic") == act.command_topic), None)
        display_actuators.append({
            "id": act.id,
            "name": act.name,
            "state": rt_data.get("state", "Desconhecido") if rt_data else "Desconhecido",
            "timestamp": rt_data.get("timestamp", "-") if rt_data else "-"
        })
        
    display_sensors = []
    for sen in db_sensors:
        rt_data = next((rt for rt in rt_sensors_cache.values() if rt.get("topic") == sen.topic), None)
        display_sensors.append({
            "id": sen.id,
            "name": sen.name,
            "value": rt_data.get("value", "N/A") if rt_data else "N/A",
            "timestamp": rt_data.get("timestamp", "-") if rt_data else "-",
            "unit": sen.unit
        })
        
    temp_sensor_display = next((s for s in display_sensors if s.get("name") == "Temperatura Padrão"), {})
    hum_sensor_display = next((s for s in display_sensors if s.get("name") == "Umidade Padrão"), {})

    return render_template("dashboard.html",
                         privilegio=current_user.privilegio,
                         all_actuators=display_actuators,
                         all_sensors=display_sensors,
                         # Pass the full sensor dictionaries here too for consistency
                         temperatura=temp_sensor_display,
                         umidade=hum_sensor_display,
                         command_history=current_command_history)

# --- API Endpoints ---

# Refactored: Get combined data (DB + Cache)
@app.route("/api/device_data")
@login_required
def get_device_data():
    db_actuators = Actuator.query.all()
    db_sensors = Sensor.query.all()
    with data_lock:
        rt_actuators_cache = devices["actuators"].copy()
        rt_sensors_cache = devices["sensors"].copy()
        current_command_history = command_history[-10:].copy()

    api_actuators = {}
    for act in db_actuators:
        rt_data = next((rt for rt in rt_actuators_cache.values() if rt.get("command_topic") == act.command_topic), None)
        api_actuators[act.id] = { # Use DB ID as key
            "id": act.id,
            "name": act.name,
            "state": rt_data.get("state", "Desconhecido") if rt_data else "Desconhecido",
            "timestamp": rt_data.get("timestamp", "-") if rt_data else "-",
            "command_topic": act.command_topic,
            "state_topic": act.state_topic
        }
        
    api_sensors = {}
    for sen in db_sensors:
        rt_data = next((rt for rt in rt_sensors_cache.values() if rt.get("topic") == sen.topic), None)
        api_sensors[sen.id] = { # Use DB ID as key
            "id": sen.id,
            "name": sen.name,
            "value": rt_data.get("value", "N/A") if rt_data else "N/A",
            "timestamp": rt_data.get("timestamp", "-") if rt_data else "-",
            "unit": sen.unit,
            "topic": sen.topic
        }

    return jsonify({
        "sensors": api_sensors,
        "actuators": api_actuators,
        "command_history": current_command_history
    })

# Updated: Use DB to find actuator by ID for raw command
@app.route("/api/actuator/raw_command", methods=["POST"])
@login_required
def actuator_raw_command():
    if not current_user.is_admin:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400
        
    try:
        # Expecting DB actuator ID now
        actuator_id = int(data.get("actuator_id")) 
    except (ValueError, TypeError, AttributeError):
        return jsonify({"status": "error", "message": "Invalid or missing Actuator ID format"}), 400
        
    raw_command = data.get("raw_command", "").upper()
    
    if raw_command not in ["ON", "OFF"]:
        return jsonify({"status": "error", "message": "Invalid raw_command value (must be ON or OFF)"}), 400
    
    # Find actuator in the database by ID
    target_actuator = db.session.get(Actuator, actuator_id)
        
    if target_actuator and target_actuator.command_topic:
        try:
            mqtt_client.publish(target_actuator.command_topic, raw_command)
            print(f"✅ Raw command {raw_command} sent to {target_actuator.name} (ID: {actuator_id})")
            
            new_state_str = "Ligado" if raw_command == "ON" else "Desligado"
            
            # Update state in MQTT cache immediately for UI feedback
            with data_lock:
                # Find the cache entry (assuming it exists and key might not be DB ID)
                cache_key = None
                for key, rt_actuator in devices["actuators"].items():
                     if rt_actuator.get("command_topic") == target_actuator.command_topic:
                         cache_key = key
                         break
                if cache_key and cache_key in devices["actuators"]:
                    devices["actuators"][cache_key]["state"] = new_state_str
                    devices["actuators"][cache_key]["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                # else: Consider adding to cache if missing?

            # Log command history (still using in-memory list)
            log_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "user": current_user.username,
                "actuator_name": target_actuator.name,
                "command": new_state_str,
                "topic": target_actuator.command_topic,
                "payload": raw_command
            }
            command_history.append(log_entry)
            # Keep command_history trimmed (optional)
            # while len(command_history) > 50: command_history.pop(0)
                
            # TODO: Log to DeviceLog table in DB
            
            return jsonify({
                "status": "success", 
                "message": f"Raw command {raw_command} sent",
                "new_state": new_state_str,
                "actuator_id": actuator_id # Return the ID for potential UI updates
            })
        except Exception as e:
            print(f"Error publishing MQTT command for actuator {actuator_id}: {e}")
            return jsonify({"status": "error", "message": "Erro ao enviar comando MQTT"}), 500
    else:
        return jsonify({"status": "error", "message": "Actuator not found in DB or has no command topic"}), 404
        
# This route seems redundant now that /actuator/toggle exists in actuator.py
# and raw_command is updated. Consider removing or adapting.
# Keeping it for now, but updating to use DB.
@app.route("/api/actuator/command", methods=["POST"])
@login_required
def actuator_command():
    if not current_user.is_admin:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400
        
    try:
        actuator_id = int(data.get("actuator_id"))
    except (ValueError, TypeError, AttributeError):
         return jsonify({"status": "error", "message": "Invalid or missing Actuator ID format"}), 400
         
    command = data.get("command", "").lower()

    if command not in ["ligar", "desligar"]:
        return jsonify({"status": "error", "message": "Invalid command value (must be ligar or desligar)"}), 400

    # Find actuator in the database by ID
    target_actuator = db.session.get(Actuator, actuator_id)

    if target_actuator and target_actuator.command_topic:
        mqtt_payload = "ON" if command == "ligar" else "OFF"
        try:
            mqtt_client.publish(target_actuator.command_topic, mqtt_payload)
            print(f"✅ Command {command} ({mqtt_payload}) sent to {target_actuator.name} (ID: {actuator_id})")

            new_state_str = "Ligado" if command == "ligar" else "Desligado"

            # Update state in MQTT cache immediately
            with data_lock:
                cache_key = None
                for key, rt_actuator in devices["actuators"].items():
                     if rt_actuator.get("command_topic") == target_actuator.command_topic:
                         cache_key = key
                         break
                if cache_key and cache_key in devices["actuators"]:
                    devices["actuators"][cache_key]["state"] = new_state_str
                    devices["actuators"][cache_key]["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

            # Log command history
            log_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "user": current_user.username,
                "actuator_name": target_actuator.name,
                "command": new_state_str,
                "topic": target_actuator.command_topic,
                "payload": mqtt_payload
            }
            command_history.append(log_entry)
            # while len(command_history) > 50: command_history.pop(0)

            # TODO: Log to DeviceLog table in DB

            return jsonify({
                "status": "success",
                "message": f"Comando \n{command}\n enviado",
                "new_state": new_state_str,
                "actuator_id": actuator_id
            })
        except Exception as e:
            print(f"Error publishing MQTT command for actuator {actuator_id}: {e}")
            return jsonify({"status": "error", "message": "Erro ao enviar comando MQTT"}), 500
    else:
        return jsonify({"status": "error", "message": "Actuator not found in DB or has no command topic"}), 404


# --- Error Handlers --- (No changes needed here)
@app.errorhandler(404)
def page_not_found(e):
    base_template = "baseAdmin.html" if current_user.is_authenticated and current_user.is_admin else "baseUser.html" if current_user.is_authenticated else "errorBase.html"
    return render_template("errors/404.html", base_template=base_template), 404

@app.errorhandler(500)
def internal_server_error(e):
    # Log the actual error
    print(f"Internal Server Error: {e}") 
    # Potentially add traceback logging: import traceback; traceback.print_exc()
    base_template = "baseAdmin.html" if current_user.is_authenticated and current_user.is_admin else "baseUser.html" if current_user.is_authenticated else "errorBase.html"
    return render_template("errors/500.html", base_template=base_template), 500

@app.errorhandler(401)
def unauthorized_error(e):
    return render_template("errors/401.html", base_template="errorBase.html"), 401

@app.errorhandler(403)
def forbidden_error(e):
    base_template = "baseAdmin.html" if current_user.is_authenticated and current_user.is_admin else "baseUser.html" if current_user.is_authenticated else "errorBase.html"
    return render_template("errors/403.html", base_template=base_template), 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False) # Set debug=False for production

