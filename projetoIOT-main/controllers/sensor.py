from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
# Import db and the Sensor model
from models.models import db, Sensor
# Import MQTT client for subscription management
from controllers.shared import mqtt_client, data_lock, devices # Import devices cache
import time
import traceback # Import for detailed error logging
import uuid # Import uuid

sensor_main = Blueprint("sensor_main", __name__, template_folder="../templates")

@sensor_main.route("/register", methods=["GET", "POST"])
@login_required
def register_sensor_page():
    if not current_user.is_admin:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("home_page_dashboard"))
    
    if request.method == "POST":
        sensor_name = request.form.get("name")
        sensor_topic = request.form.get("topic")
        sensor_unit = request.form.get("type", None) # Use 'unit' field from model
        
        if not all([sensor_name, sensor_topic]):
            flash("Nome e tópico do sensor são obrigatórios", "error")
            return render_template("register_sensor.html", name=sensor_name, topic=sensor_topic, type=sensor_unit)
        
        # Check if topic already exists in DB
        existing_sensor = Sensor.query.filter_by(topic=sensor_topic).first()
        if existing_sensor:
            flash("Já existe um sensor com este tópico MQTT no banco de dados", "error")
            return render_template("register_sensor.html", name=sensor_name, topic=sensor_topic, type=sensor_unit)
        
        # Generate unique string ID for the sensor
        sensor_id_str = f"sensor_{uuid.uuid4().hex[:8]}"
        
        # Create new Sensor object including the generated ID
        new_sensor = Sensor(
            sensor_id_str=sensor_id_str, # Assign the generated ID
            name=sensor_name, 
            topic=sensor_topic, 
            unit=sensor_unit or None
        )
        
        try:
            db.session.add(new_sensor)
            db.session.commit()
            
            # Subscribe to MQTT topic after successful DB save
            try:
                mqtt_client.subscribe(sensor_topic)
                print(f"🔔 Subscribed to new sensor topic: {sensor_topic}")
            except Exception as e:
                 print(f"Error subscribing to topic {sensor_topic}: {e}")
                 flash(f"Sensor \'{sensor_name}\' registrado no banco de dados, mas ocorreu um erro ao subscrever ao tópico MQTT: {e}", "warning")

            flash(f"Sensor \'{sensor_name}\' registrado com sucesso!", "success")
            return redirect(url_for("sensor_main.manage_sensors_page"))
            
        except Exception as e:
            db.session.rollback()
            print(f"Database error during sensor registration: {e}") # Log detailed error
            traceback.print_exc() # Print traceback
            flash(f"Erro ao registrar sensor no banco de dados: {e}", "error")
            return render_template("register_sensor.html", name=sensor_name, topic=sensor_topic, type=sensor_unit)
    
    # GET request
    return render_template("register_sensor.html")

# --- Other routes remain the same for now ---

@sensor_main.route("/manage")
@login_required
def manage_sensors_page():
    if not current_user.is_admin:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("home_page_dashboard"))
    
    try: # Add try-except block for better error handling
        # Fetch sensors directly from the database
        db_sensors = Sensor.query.order_by(Sensor.name).all()

        # Fetch real-time data from MQTT cache
        with data_lock:
            # Make a copy to avoid modifying the cache directly during iteration
            realtime_data_cache = devices["sensors"].copy()

        # Create a list of dictionaries for the template
        display_sensors = []
        for sensor in db_sensors:
            # Find matching realtime data using topic
            rt_sensor = next((rt for rt in realtime_data_cache.values() if rt.get("topic") == sensor.topic), None)

            sensor_data = {
                "id": sensor.id,
                "name": sensor.name,
                "topic": sensor.topic,
                "unit": sensor.unit,
                "current_value": "N/A", # Default values
                "last_update": "-"
            }

            if rt_sensor:
                sensor_data["current_value"] = rt_sensor.get("value", "N/A")
                sensor_data["last_update"] = rt_sensor.get("timestamp", "-")

            display_sensors.append(sensor_data)

        # Pass the list of dictionaries to the template
        return render_template("manage_sensor.html", devices=display_sensors)

    except Exception as e:
        # Log the error for debugging
        print(f"Error in manage_sensors_page: {e}")
        traceback.print_exc() # Print detailed traceback
        flash("Ocorreu um erro ao carregar a página de gerenciamento de sensores.", "error")
        # Redirect to dashboard to avoid showing a broken page
        return redirect(url_for("home_page_dashboard"))

@sensor_main.route("/delete/<int:sensor_id>", methods=["POST"])
@login_required
def delete_sensor(sensor_id):
    if not current_user.is_admin:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("sensor_main.manage_sensors_page"))

    sensor_to_delete = db.session.get(Sensor, sensor_id) # Use Session.get()
    
    if not sensor_to_delete:
        flash("Sensor não encontrado no banco de dados.", "error")
        return redirect(url_for("sensor_main.manage_sensors_page"))
        
    topic_to_unsubscribe = sensor_to_delete.topic
    sensor_name = sensor_to_delete.name
    
    try:
        db.session.delete(sensor_to_delete)
        db.session.commit()
        
        # Unsubscribe from MQTT topic after successful DB delete
        if topic_to_unsubscribe:
            try:
                mqtt_client.unsubscribe(topic_to_unsubscribe)
                print(f"🔕 Unsubscribed from sensor topic: {topic_to_unsubscribe}")
            except Exception as e:
                print(f"Error unsubscribing from topic {topic_to_unsubscribe}: {e}")
                flash(f"Sensor removido do banco de dados, mas ocorreu um erro ao remover a subscrição do tópico MQTT: {e}", "warning")
        
        # Also remove from in-memory dict if present (using topic as key?)
        with data_lock:
            key_to_remove = None
            # Use items() for safe iteration while potentially modifying
            for key, rt_sensor in list(devices["sensors"].items()): 
                if rt_sensor.get("topic") == topic_to_unsubscribe:
                    key_to_remove = key
                    break # Assuming topic is unique enough
            if key_to_remove and key_to_remove in devices["sensors"]:
                del devices["sensors"][key_to_remove]
                print(f"Removed sensor {key_to_remove} from in-memory dict")

        flash(f"Sensor \'{sensor_name}\' removido com sucesso.", "success")
        
    except Exception as e:
        db.session.rollback()
        print(f"Database error during sensor deletion: {e}") # Log detailed error
        traceback.print_exc() # Print traceback
        flash(f"Erro ao remover sensor do banco de dados: {e}", "error")
            
    return redirect(url_for("sensor_main.manage_sensors_page"))

@sensor_main.route("/edit/<int:sensor_id>", methods=["GET", "POST"])
@login_required
def edit_sensor(sensor_id):
    if not current_user.is_admin:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("home_page_dashboard"))
    
    sensor_to_edit = db.session.get(Sensor, sensor_id) # Use Session.get()
    if not sensor_to_edit:
        flash("Sensor não encontrado.", "error")
        return redirect(url_for("sensor_main.manage_sensors_page"))
    
    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        new_topic = request.form.get("topic", "").strip()
        new_unit = request.form.get("type", None) # Use 'unit' field
        
        if not new_name or not new_topic:
            flash("Nome e tópico do sensor são obrigatórios!", "error")
            # Pass current data back to template
            return render_template("edit_sensor.html", sensor=sensor_to_edit) 

        # Check if topic is being changed to one that already exists (excluding current sensor)
        if new_topic != sensor_to_edit.topic:
            existing_sensor = Sensor.query.filter(Sensor.topic == new_topic, Sensor.id != sensor_id).first()
            if existing_sensor:
                flash(f"Tópico MQTT \'{new_topic}\' já está em uso por outro sensor.", "error")
                return render_template("edit_sensor.html", sensor=sensor_to_edit)
        
        old_topic = sensor_to_edit.topic
        topic_changed = (new_topic != old_topic)

        # Update sensor details in DB
        sensor_to_edit.name = new_name
        sensor_to_edit.topic = new_topic
        sensor_to_edit.unit = new_unit or None
            
        try:
            db.session.commit()
            
            # If topic changed, unsubscribe from old and subscribe to new
            if topic_changed:
                if old_topic:
                    try:
                        mqtt_client.unsubscribe(old_topic)
                        print(f"🔕 Unsubscribed from old sensor topic: {old_topic}")
                    except Exception as e:
                        print(f"Error unsubscribing from old topic {old_topic}: {e}")
                try:
                    mqtt_client.subscribe(new_topic)
                    print(f"🔔 Subscribed to new sensor topic: {new_topic}")
                except Exception as e:
                    print(f"Error subscribing to new topic {new_topic}: {e}")
                    flash(f"Sensor atualizado, mas erro ao (re)subscrever ao tópico MQTT: {e}", "warning")
            
            # Update in-memory dict if necessary (e.g., if key depends on topic)
            # This part is tricky. MQTT callback should handle updates based on topic.

            flash("Sensor atualizado com sucesso!", "success")
            return redirect(url_for("sensor_main.manage_sensors_page"))
            
        except Exception as e:
            db.session.rollback()
            print(f"Database error during sensor edit: {e}") # Log detailed error
            traceback.print_exc() # Print traceback
            flash(f"Erro ao atualizar sensor no banco de dados: {e}", "error")
            return render_template("edit_sensor.html", sensor=sensor_to_edit)

    # GET request - show edit form
    return render_template("edit_sensor.html", sensor=sensor_to_edit)

