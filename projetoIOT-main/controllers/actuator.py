from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
# Import db and the Actuator model
from models.models import db, Actuator
# Import MQTT client for subscription/publishing
from controllers.shared import mqtt_client, data_lock, devices # Keep devices for real-time state?
import time
import uuid # Import uuid

actuator_main = Blueprint("actuator_main", __name__, template_folder="../templates")

@actuator_main.route("/register", methods=["GET", "POST"])
@login_required
def register_actuator_page():
    if not current_user.is_admin:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("home_page_dashboard"))
    
    if request.method == "POST":
        actuator_name = request.form.get("name", "").strip()
        cmd_topic = request.form.get("command_topic", "").strip()
        status_topic = request.form.get("status_topic", "").strip() or None # Store None if empty
        
        if not actuator_name or not cmd_topic:
            flash("Nome e tópico de comando são obrigatórios", "error")
            return render_template("register_actuator.html", name=actuator_name, command_topic=cmd_topic, status_topic=status_topic)
        
        # Check if command topic already exists in DB
        existing_actuator = Actuator.query.filter_by(command_topic=cmd_topic).first()
        if existing_actuator:
            flash("Já existe um atuador com este tópico de comando no banco de dados", "error")
            return render_template("register_actuator.html", name=actuator_name, command_topic=cmd_topic, status_topic=status_topic)
        
        # Generate unique string ID for the actuator
        actuator_id_str = f"actuator_{uuid.uuid4().hex[:8]}" 
        
        # Create new Actuator object including the generated ID
        new_actuator = Actuator(
            actuator_id_str=actuator_id_str, # Assign the generated ID
            name=actuator_name, 
            command_topic=cmd_topic, 
            state_topic=status_topic,
            state="Desconhecido" # Default state
        )
        
        try:
            db.session.add(new_actuator)
            db.session.commit()
            
            # Subscribe to status topic if provided
            if status_topic:
                try:
                    mqtt_client.subscribe(status_topic)
                    print(f"🔔 Subscribed to actuator status topic: {status_topic}")
                except Exception as e:
                    print(f"Error subscribing to topic {status_topic}: {e}")
                    flash(f"Atuador \'{actuator_name}\' registrado no DB, mas erro ao subscrever ao tópico MQTT: {e}", "warning")

            flash(f"Atuador \'{actuator_name}\' registrado com sucesso!", "success")
            return redirect(url_for("actuator_main.manage_actuators_page"))
            
        except Exception as e:
            db.session.rollback()
            # Provide more specific error message if possible
            flash(f"Erro ao registrar atuador no banco de dados: {e}", "error") 
            print(f"Database error during actuator registration: {e}") # Log detailed error
            return render_template("register_actuator.html", name=actuator_name, command_topic=cmd_topic, status_topic=status_topic)
    
    # GET request
    return render_template("register_actuator.html")

# --- Other routes remain the same for now ---

@actuator_main.route("/manage")
@login_required
def manage_actuators_page():
    if not current_user.is_admin:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("home_page_dashboard"))
    
    # Fetch actuators directly from the database
    actuators_list = Actuator.query.order_by(Actuator.name).all()
    
    # Add real-time state from MQTT cache (devices dict)
    with data_lock:
        realtime_data = devices["actuators"]
        
    for actuator in actuators_list:
        # Match DB actuators with realtime data, perhaps using command_topic?
        rt_actuator = next((rt for rt in realtime_data.values() if rt.get("command_topic") == actuator.command_topic), None)
        if rt_actuator:
            actuator.current_state = rt_actuator.get("state", "Desconhecido")
            actuator.last_update = rt_actuator.get("timestamp", "-")
        else:
            # If not found in realtime cache, maybe use DB state or default?
            actuator.current_state = actuator.state or "Desconhecido" # Assuming Actuator model has a state field
            actuator.last_update = "-"
            
    return render_template("manage_actuator.html", devices=actuators_list)

@actuator_main.route("/edit/<int:actuator_id>", methods=["GET", "POST"])
@login_required
def edit_actuator_page(actuator_id):
    if not current_user.is_admin:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("home_page_dashboard"))
    
    actuator_to_edit = Actuator.query.get_or_404(actuator_id)
    
    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        new_cmd_topic = request.form.get("command_topic", "").strip()
        new_status_topic = request.form.get("status_topic", "").strip() or None
        
        if not new_name or not new_cmd_topic:
            flash("Nome e tópico de comando são obrigatórios", "error")
            return render_template("edit_actuator.html", actuator=actuator_to_edit)
        
        # Check if command topic is being changed to one that already exists
        if new_cmd_topic != actuator_to_edit.command_topic:
            existing_actuator = Actuator.query.filter(Actuator.command_topic == new_cmd_topic, Actuator.id != actuator_id).first()
            if existing_actuator:
                flash(f"Tópico de comando MQTT \'{new_cmd_topic}\' já está em uso.", "error")
                return render_template("edit_actuator.html", actuator=actuator_to_edit)
        
        old_status_topic = actuator_to_edit.state_topic
        status_topic_changed = (new_status_topic != old_status_topic)

        # Update actuator details in DB
        actuator_to_edit.name = new_name
        actuator_to_edit.command_topic = new_cmd_topic
        actuator_to_edit.state_topic = new_status_topic
            
        try:
            db.session.commit()
            
            # If status topic changed, manage MQTT subscriptions
            if status_topic_changed:
                if old_status_topic:
                    try:
                        mqtt_client.unsubscribe(old_status_topic)
                        print(f"🔕 Unsubscribed from old status topic: {old_status_topic}")
                    except Exception as e:
                        print(f"Error unsubscribing from old topic {old_status_topic}: {e}")
                if new_status_topic:
                    try:
                        mqtt_client.subscribe(new_status_topic)
                        print(f"🔔 Subscribed to new status topic: {new_status_topic}")
                    except Exception as e:
                        print(f"Error subscribing to new topic {new_status_topic}: {e}")
                        flash(f"Atuador atualizado, mas erro ao (re)subscrever ao tópico MQTT: {e}", "warning")
            
            # Update in-memory dict if necessary?
            # This is complex. Maybe rely on MQTT updates or refresh cache?

            flash("Atuador atualizado com sucesso!", "success")
            return redirect(url_for("actuator_main.manage_actuators_page"))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar atuador no banco de dados: {e}", "error")
            return render_template("edit_actuator.html", actuator=actuator_to_edit)

    # GET request
    return render_template("edit_actuator.html", actuator=actuator_to_edit)

# API endpoint for toggling - Now uses DB to find actuator
@actuator_main.route("/toggle/<int:actuator_id>", methods=["POST"])
@login_required
def toggle_actuator(actuator_id):
    if not current_user.is_admin:
        return jsonify({"status": "error", "message": "Não autorizado"}), 403
    
    actuator = Actuator.query.get(actuator_id)
    if not actuator:
        return jsonify({"status": "error", "message": "Atuador não encontrado no banco de dados"}), 404
    
    # Determine new state based on *current* state (from MQTT cache or DB fallback?)
    # Let's use the MQTT cache for responsiveness if available
    current_state = "Desconhecido"
    with data_lock:
        rt_actuator = next((rt for rt in devices["actuators"].values() if rt.get("command_topic") == actuator.command_topic), None)
        if rt_actuator:
            current_state = rt_actuator.get("state", "Desconhecido")
        # Fallback to DB state if needed?
        # elif actuator.state:
        #     current_state = actuator.state
            
    new_state_str = "Ligado" if current_state.lower() == "desligado" else "Desligado"
    mqtt_payload = "ON" if new_state_str == "Ligado" else "OFF"
    
    try:
        mqtt_client.publish(actuator.command_topic, mqtt_payload)
        print(f"✅ Command {mqtt_payload} sent to {actuator.name} (ID: {actuator_id})")
        
        # Update state in DB (optional, MQTT callback might do this)
        # actuator.state = new_state_str
        # db.session.commit()
        
        # Update state in MQTT cache immediately for UI feedback
        with data_lock:
             if rt_actuator: # Update existing entry
                 rt_actuator["state"] = new_state_str
                 rt_actuator["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
             # else: # Add if missing? Might be complex if keys aren't DB IDs
                 # devices["actuators"][f"db_{actuator.id}"] = { ... } # Create entry

        # TODO: Log this action to the DeviceLog table

        return jsonify({
            "status": "success",
            "new_state": new_state_str,
            "actuator_id": actuator_id
        })
    except Exception as e:
        print(f"Error publishing MQTT command for actuator {actuator_id}: {e}")
        return jsonify({"status": "error", "message": "Erro ao enviar comando MQTT"}), 500

@actuator_main.route("/delete/<int:actuator_id>", methods=["POST"])
@login_required
def delete_actuator(actuator_id):
    if not current_user.is_admin:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("actuator_main.manage_actuators_page"))
    
    actuator_to_delete = Actuator.query.get(actuator_id)
    
    if not actuator_to_delete:
        flash("Atuador não encontrado no banco de dados.", "error")
        return redirect(url_for("actuator_main.manage_actuators_page"))
        
    # Check if it's a default actuator (if flag added to model)
    # if actuator_to_delete.is_default:
    #     flash("Não é possível remover atuadores padrão.", "error")
    #     return redirect(url_for("actuator_main.manage_actuators_page"))
        
    status_topic = actuator_to_delete.state_topic
    command_topic = actuator_to_delete.command_topic # Needed for removing from cache
    actuator_name = actuator_to_delete.name
    
    try:
        db.session.delete(actuator_to_delete)
        db.session.commit()
        
        # Unsubscribe from MQTT status topic after successful DB delete
        if status_topic:
            try:
                mqtt_client.unsubscribe(status_topic)
                print(f"🔕 Unsubscribed from status topic: {status_topic}")
            except Exception as e:
                print(f"Error unsubscribing from topic {status_topic}: {e}")
                flash(f"Atuador removido do DB, mas erro ao remover subscrição MQTT: {e}", "warning")
        
        # Also remove from in-memory dict (using command_topic as key?)
        with data_lock:
            key_to_remove = None
            for key, rt_actuator in devices["actuators"].items():
                if rt_actuator.get("command_topic") == command_topic:
                    key_to_remove = key
                    break
            if key_to_remove:
                del devices["actuators"][key_to_remove]
                print(f"Removed actuator {key_to_remove} from in-memory dict")

        flash(f"Atuador \'{actuator_name}\' removido com sucesso.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao remover atuador do banco de dados: {e}", "error")
            
    return redirect(url_for("actuator_main.manage_actuators_page"))

