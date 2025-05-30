from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from controllers.shared import devices, data_lock, mqtt_client
import uuid
import time
import paho.mqtt.client as mqtt

actuator_main = Blueprint('actuator_main', __name__, template_folder="templates")

@actuator_main.route("/register", methods=["GET", "POST"])
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

@actuator_main.route("/manage")
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

@actuator_main.route("/edit/<actuator_id>", methods=["GET", "POST"])
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

@actuator_main.route("/toggle/<actuator_id>", methods=["POST"])
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

@actuator_main.route("/delete/<actuator_id>", methods=["POST"])
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