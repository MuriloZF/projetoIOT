from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from controllers.shared import devices, data_lock, mqtt_client
import uuid
import time
import paho.mqtt.client as mqtt
from functools import wraps
from models.db import db
from models.iot.sensor_model import Sensor

sensor_main = Blueprint('sensor_main', __name__, template_folder="templates")

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Acesso não autorizado", "error")
            return redirect(url_for("user.login_page"))
        return f(*args, **kwargs)
    return decorated_function

@admin_required
@sensor_main.route("/register", methods=["GET", "POST"])
def register_sensor_page():
    
    if request.method == "POST":
        sensor_name = request.form.get("name", "").strip()
        sensor_topic = request.form.get("topic", "").strip()
        sensor_type = request.form.get("type", "").strip()
        
        if not all([sensor_name, sensor_topic]):
            flash("Nome e tópico do sensor são obrigatórios", "error")
            return redirect(url_for("sensor_main.register_sensor_page"))
        
        for sensor in Sensor.get_sensors():
            if sensor.topic == sensor_topic:
                flash("Já existe um sensor com este tópico MQTT", "error")
                return redirect(url_for("sensor_main.register_sensor_page"))
        
        Sensor.save_sensor(name = sensor_name, topic = sensor_topic, unit = sensor_type)
        
        # Subscribe to MQTT topic
        mqtt_client.subscribe(sensor_topic)
        print(f"🔔 Subscribed to new sensor topic: {sensor_topic}")
        
        flash(f"Sensor '{sensor_name}' registrado com sucesso!", "success")
        return redirect(url_for("sensor_main.manage_sensors_page"))
    
    return render_template("register_sensor.html")

@admin_required
@sensor_main.route("/manage")
def manage_sensors_page():
    sensors = Sensor.get_sensors()    
    return render_template("manage_sensor.html", sensors=sensors)

@admin_required
@sensor_main.route("/delete/<int:sensor_id>", methods=["POST"])
def delete_sensor(sensor_id):
    from app import app
    with app.app_context():
        sensor = Sensor.query.get(sensor_id)

        if not sensor:
            print(f"⚠️ Sensor com ID {sensor_id} não encontrado.")
            return redirect(url_for("sensor_main.manage_sensors_page"))

        if sensor.topic:
            mqtt_client.unsubscribe(sensor.topic)
            print(f"🔕 Unsubscrito do tópico: {sensor.topic}")

        Sensor.delete_sensor(sensor_id)

        flash(f"Atuador '{sensor.name}' removido com sucesso", "success")
        print(f"🗑️ Deleted actuator: {sensor.name}")
        return redirect(url_for("sensor_main.manage_sensors_page"))

@admin_required
@sensor_main.route("/edit/<int:sensor_id>", methods=["GET", "POST"])
def edit_sensor(sensor_id):
    sensor = Sensor.get_single_sensor(sensor_id)
    if not sensor:
        flash("Sensor não encontrado!", "error")
        return redirect(url_for("sensor_main.manage_sensors_page"))
    
    if request.method == "POST":
        sensor_name = request.form.get("sensor_name", "").strip()
        data_type = request.form.get("data_type", "").strip()
        
        if not sensor_name:
            flash("Nome do sensor é obrigatório!", "error")
            return render_template("edit_sensor.html", sensor=sensor)
        
        Sensor.update_sensor(sensor_id, sensor_name, unit = data_type)
        
        flash("Sensor atualizado com sucesso!", "success")
        return redirect(url_for("sensor_main.manage_sensors_page"))
    
    return render_template("edit_sensor.html", sensor=sensor)