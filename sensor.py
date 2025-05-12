from flask import Blueprint, render_template, request, redirect, url_for, flash

sensor_main = Blueprint('sensor_main', __name__, template_folder="templates")

# Using a dictionary to store sensor data with topic as key
sensors = {}

@sensor_main.route("/sensor/manage")
def manage_sensors():
    return render_template("manage_sensors.html", devices=sensors)

@sensor_main.route("/sensor/register", methods=["GET", "POST"])
def register_sensor_page():
    if request.method == "POST":
        sensor_name = request.form.get("sensor_name")
        mqtt_topic = request.form.get("mqtt_topic")
        data_type = request.form.get("data_type", "N/A")
        
        if not sensor_name or not mqtt_topic:
            flash("Nome do sensor e tópico MQTT são obrigatórios!", "error")
            return redirect(url_for("sensor_main.register_sensor_page"))
        
        if mqtt_topic in sensors:
            flash("Já existe um sensor com este tópico MQTT!", "error")
            return redirect(url_for("sensor_main.register_sensor_page"))
        
        # Add new sensor with complete structure
        sensors[mqtt_topic] = {
            "name": sensor_name,
            "topic": mqtt_topic,
            "value": "N/A",
            "timestamp": "N/A",
            "data_type": data_type,
            "id": len(sensors) + 1
        }
        
        flash(f"Sensor '{sensor_name}' registrado com sucesso!", "success")
        return redirect(url_for("sensor_main.manage_sensors"))
    
    return render_template("register_sensor.html")

@sensor_main.route("/sensor/edit/<string:sensor_topic>", methods=["GET", "POST"])
def edit_sensor(sensor_topic):
    if sensor_topic not in sensors:
        flash("Sensor não encontrado!", "error")
        return redirect(url_for("sensor_main.manage_sensors"))
    
    if request.method == "POST":
        sensor_name = request.form.get("sensor_name")
        data_type = request.form.get("data_type", "N/A")
        
        if not sensor_name:
            flash("Nome do sensor é obrigatório!", "error")
            return redirect(url_for("sensor_main.edit_sensor", sensor_topic=sensor_topic))
        
        sensors[sensor_topic]["name"] = sensor_name
        sensors[sensor_topic]["data_type"] = data_type
        
        flash("Sensor atualizado com sucesso!", "success")
        return redirect(url_for("sensor_main.manage_sensors"))
    
    return render_template("edit_sensor.html", sensor=sensors[sensor_topic])

@sensor_main.route("/sensor/delete/<string:sensor_topic>", methods=["POST"])
def delete_sensor(sensor_topic):
    if sensor_topic in sensors:
        sensor_name = sensors[sensor_topic]["name"]
        del sensors[sensor_topic]
        flash(f"Sensor '{sensor_name}' removido com sucesso!", "success")
    else:
        flash("Sensor não encontrado!", "error")
    
    return redirect(url_for("sensor_main.manage_sensors"))