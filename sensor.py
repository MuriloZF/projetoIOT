from flask import Blueprint, render_template, request, redirect, url_for

sensor_main = Blueprint('sensor_main', __name__, template_folder="templates")

# Using a dictionary to store sensor data (temporary solution)
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
        
        # Add new sensor with complete structure
        sensors[mqtt_topic] = {
            "name": sensor_name,
            "topic": mqtt_topic,
            "value": "N/A",
            "timestamp": "N/A",
            "data_type": data_type,
            "id": len(sensors) + 1  # Simple ID assignment
        }
        return redirect(url_for("sensor_main.manage_sensors"))
    
    return render_template("register_sensor.html")

@sensor_main.route("/sensor/delete/<string:sensor_topic>", methods=["POST"])
def delete_sensor(sensor_topic):
    if sensor_topic in sensors:
        del sensors[sensor_topic]
    return redirect(url_for("sensor_main.manage_sensors"))