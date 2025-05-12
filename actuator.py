from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import uuid
from threading import Lock
import time

actuator_bp = Blueprint("actuator_main", __name__, template_folder="templates", url_prefix="/actuator")

@actuator_bp.route("/register", methods=["GET", "POST"])
def register_actuator_page():
    if session.get("privilegio") != 1:
        return redirect(url_for("user.login_page"))
    
    if request.method == "POST":
        actuator_name = request.form.get("actuator_name")
        command_topic = request.form.get("mqtt_command_topic")
        status_topic = request.form.get("mqtt_status_topic", "")
        
        if not all([actuator_name, command_topic]):
            flash("Nome e tópico de comando são obrigatórios", "error")
            return render_template("register_actuator.html")
        
        with data_lock:
            # Check if command topic already exists
            if any(a["command_topic"] == command_topic for a in devices["actuators"].values()):
                flash("Já existe um atuador com este tópico de comando", "error")
                return render_template("register_actuator.html")
            
            actuator_id = f"actuator_{uuid.uuid4().hex[:6]}"
            devices["actuators"][actuator_id] = {
                "id": actuator_id,
                "name": actuator_name,
                "command_topic": command_topic,
                "status_topic": status_topic,
                "state": "OFF",
                "is_default": False
            }
            
            # Subscribe to status topic if provided
            if status_topic:
                mqtt_client.subscribe(status_topic)
            
            flash(f"Atuador '{actuator_name}' registrado com sucesso!", "success")
            return redirect(url_for("actuator_main.manage_actuators_page"))
    
    return render_template("register_actuator.html")

@actuator_bp.route("/manage")
def manage_actuators_page():
    if session.get("privilegio") != 1:
        return redirect(url_for("user.login_page"))
    
    with data_lock:
        actuators_list = list(devices["actuators"].values())
    
    return render_template("manage_actuator.html", devices=actuators_list)

@actuator_bp.route("/edit/<actuator_id>", methods=["GET", "POST"])
def edit_actuator_page(actuator_id):
    if session.get("privilegio") != 1:
        return redirect(url_for("user.login_page"))
    
    with data_lock:
        actuator = devices["actuators"].get(actuator_id)
        if not actuator:
            flash("Atuador não encontrado", "error")
            return redirect(url_for("actuator_main.manage_actuators_page"))
        
        if request.method == "POST":
            actuator_name = request.form.get("actuator_name")
            command_topic = request.form.get("mqtt_command_topic")
            status_topic = request.form.get("mqtt_status_topic", "")
            
            if not all([actuator_name, command_topic]):
                flash("Nome e tópico de comando são obrigatórios", "error")
                return render_template("edit_actuator.html", actuator=actuator)
            
            # Unsubscribe from old status topic if it changed
            if actuator["status_topic"] and actuator["status_topic"] != status_topic:
                mqtt_client.unsubscribe(actuator["status_topic"])
            
            # Update actuator data
            actuator["name"] = actuator_name
            actuator["command_topic"] = command_topic
            actuator["status_topic"] = status_topic
            
            # Subscribe to new status topic if provided
            if status_topic:
                mqtt_client.subscribe(status_topic)
            
            flash("Atuador atualizado com sucesso!", "success")
            return redirect(url_for("actuator_main.manage_actuators_page"))
    
    return render_template("edit_actuator.html", actuator=actuator)

@actuator_bp.route("/toggle/<actuator_id>", methods=["POST"])
def toggle_actuator(actuator_id):
    if session.get("privilegio") != 1:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    with data_lock:
        actuator = devices["actuators"].get(actuator_id)
        if not actuator:
            return jsonify({"status": "error", "message": "Actuator not found"}), 404
        
        new_state = "ON" if actuator["state"] == "OFF" else "OFF"
        actuator["state"] = new_state
        
        # Send MQTT command
        mqtt_client.publish(actuator["command_topic"], new_state)
        
        return jsonify({
            "status": "success",
            "new_state": new_state,
            "actuator_id": actuator_id
        })

@actuator_bp.route("/delete/<actuator_id>", methods=["POST"])
def delete_actuator(actuator_id):
    if session.get("privilegio") != 1:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    with data_lock:
        actuator = devices["actuators"].get(actuator_id)
        if not actuator:
            flash("Atuador não encontrado", "error")
            return redirect(url_for("actuator_main.manage_actuators_page"))
        
        if actuator.get("is_default", False):
            flash("Não é possível remover atuadores padrão", "error")
            return redirect(url_for("actuator_main.manage_actuators_page"))
        
        # Unsubscribe from topics
        if actuator["status_topic"]:
            mqtt_client.unsubscribe(actuator["status_topic"])
        
        del devices["actuators"][actuator_id]
        flash(f"Atuador '{actuator['name']}' removido com sucesso", "success")
    
    return redirect(url_for("actuator_main.manage_actuators_page"))