from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from controllers.shared import devices, data_lock, mqtt_client
import uuid
import time
import paho.mqtt.client as mqtt
from functools import wraps
from models.iot.actuator_model import Actuator
from models.db import db

actuator_main = Blueprint('actuator_main', __name__, template_folder="templates")

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Acesso não autorizado", "error")
            return redirect(url_for("user.login_page"))
        return f(*args, **kwargs)
    return decorated_function

admin_required
@actuator_main.route("/register", methods=["GET", "POST"])
def register_actuator_page():
    if request.method == "POST":
        actuator_name = request.form.get("name", "").strip()
        topic_command = request.form.get("command_topic", "").strip()
        topic_status = request.form.get("status_topic", "").strip()
        unit = request.form.get("unit")
        is_active = False

        if not actuator_name or not topic_command:
            flash("Nome e tópico de comando são obrigatórios", "error")
            return render_template("register_actuator.html")


        for actuator in Actuator.get_actuators():
            if actuator.topic_command == topic_command:
                flash("Já existe um atuador com este tópico de comando", "error")
                return render_template("register_actuator.html")
            if topic_status and actuator.topic_status == topic_status:
                flash("Já existe um atuador com este tópico de status", "warning")
                return render_template("register_actuator.html")

        Actuator.save_actuator(actuator_name, topic_command, topic_status, is_active, unit )
        
        # Subscribe to status topic if provided
        if topic_status:
            mqtt_client.subscribe(topic_status)
            print(f"🔔 Subscribed to actuator status topic: {topic_status}")
        
        flash(f"Atuador '{actuator_name}' registrado com sucesso!", "success")
        return redirect(url_for("actuator_main.manage_actuators_page"))
    
    return render_template("register_actuator.html")

admin_required
@actuator_main.route("/manage")
def manage_actuators_page():
    actuators = Actuator.get_actuators()
    return render_template("manage_actuator.html", actuators=actuators)

admin_required
@actuator_main.route("/edit/<int:actuator_id>", methods=["GET", "POST"])
def edit_actuator_page(actuator_id):
    
    actuator = Actuator.get_single_actuator(actuator_id)
    if not actuator:
        flash("Atuador não encontrado", "error")
        return redirect(url_for("actuator_main.manage_actuators_page"))
    
    if request.method == "POST":
        actuator_name = request.form.get("name", "").strip()
        topic_command = request.form.get("command_topic", "").strip()
        topic_status = request.form.get("status_topic", "").strip()
        unit = request.form.get("unit")
        is_active = False
        
        if not actuator_name or not topic_command:
            flash("Nome e tópico de comando são obrigatórios", "error")
            return render_template("register_actuator.html")
        
        if actuator.topic_status and actuator.topic_status != topic_status:
            mqtt_client.unsubscribe(actuator.topic_status)
            print(f"🔕 Unsubscribed from old status topic: {actuator.topic_status}")
        
        Actuator.update_actuator(actuator_id, actuator_name, topic_command, topic_status, is_active, unit )
        
        # Subscribe to new status topic if provided
        if topic_status:
            mqtt_client.subscribe(topic_status)
            print(f"🔔 Subscribed to new status topic: {topic_status}")
        
        flash("Atuador atualizado com sucesso!", "success")
        return redirect(url_for("actuator_main.manage_actuators_page"))
    
    return render_template("edit_actuator.html", actuator=actuator)

@admin_required
@actuator_main.route("/toggle/<int:actuator_id>", methods=["POST"])
def toggle_actuator(actuator_id):
    actuator = Actuator.get_single_actuator(actuator_id)
    if not actuator:
        return jsonify({"status": "error", "message": "Atuador não encontrado"}), 404

    actuator.is_active = not actuator.is_active
    new_state = "Ligado" if actuator.is_active else "Desligado"

    mqtt_state = "ON" if actuator.is_active else "OFF"
    mqtt_client.publish(actuator.topic_command, mqtt_state)

    db.session.commit()

    flash(f"Atuador '{actuator.name}' foi {'ligado' if new_state == 'Ligado' else 'desligado'} com sucesso.", "success")
    return redirect(url_for("actuator_main.manage_actuators_page"))



admin_required
@actuator_main.route("/delete/<int:actuator_id>", methods=["POST"])
def delete_actuator(actuator_id):
    actuator = Actuator.get_single_actuator(actuator_id)
    
    if not actuator:
        flash("Atuador não encontrado", "error")
        return redirect(url_for("actuator_main.manage_actuators_page"))
    
    if actuator.topic_status:
        mqtt_client.unsubscribe(actuator.topic_status)
        print(f"🔕 Unsubscribed from status topic: {actuator.topic_status}")
    
    Actuator.delete_actuator(actuator_id)
    
    flash(f"Atuador '{actuator.name}' removido com sucesso", "success")
    print(f"🗑️ Deleted actuator: {actuator_id}")
    
    return redirect(url_for("actuator_main.manage_actuators_page"))