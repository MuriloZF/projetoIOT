from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from controllers.shared import devices, data_lock, mqtt_client
import uuid
import time
import paho.mqtt.client as mqtt

sensor_main = Blueprint('sensor_main', __name__, template_folder="templates")

@sensor_main.route("/register", methods=["GET", "POST"])
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

@sensor_main.route("/manage")
def manage_sensors_page():
    if session.get("privilegio") != 1:
        return redirect(url_for("user.login_page"))
    
    with data_lock:
        sensors_list = list(devices["sensors"].values())
        # Sort by timestamp (newest first)
        sensors_list.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return render_template("manage_sensor.html", devices=sensors_list)

@sensor_main.route("/delete/<sensor_id>", methods=["POST"])
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

@sensor_main.route("/edit/<sensor_id>", methods=["GET", "POST"])
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