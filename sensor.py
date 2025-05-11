from flask import Blueprint, render_template, request, redirect, url_for

sensor = Blueprint('sensor', __name__, template_folder="templates")

sensors = {
    "Sensor de Temperatura" : "0",
    "Sensor de umidade" : "0"
}

@sensor.route("/register_sensor")
def register_sensor():
    return render_template("register_sensor.html")

@sensor.route("/create_sensor", methods=["POST"])
def create_sensor():
    global sensors
    if request.method == "POST":
        sensor = request.form["sensor"]
        valor = request.form["valor"]
    else:
        sensor = request.args.get["sensor"]
        valor = request.args.get["valor"]
    sensors[sensor] = valor
    return render_template("manage_sensor.html", device=sensors)

@sensor.route("/manage_sensor")
def manage_sensor():
    return render_template("manage_sensor.html", device = sensors)

@sensor.route("/del_sensor", methods=["GET", "POST"])
def del_sensor():
    global sensors
    if request.method == "POST":
        sensor = request.form["sensor"]
    else:
        sensor = request.args.get["sensor", None]
    sensors.pop(sensor)
    return render_template("manage_sensor.html", device=sensors)

@sensor.route("/update_sensor", methods=["GET", "POST"])
def updUser():
    global sensors
    if request.method == "POST":
        sensor = request.form["sensor"]
        field = request.form["field"]
    else:
        sensor = request.form.get("sensor")
        field = request.form.get("field")

    if not sensor or sensor not in sensors:
        return "Usuário não encontrado.", 400

    if field == "sensor":
        new_sensor = request.form["new_sensor"]
        if new_sensor:
            sensors[new_sensor] = sensors.pop(sensor)
    elif field == "valor":
        new_valor = request.form["new_valor"]
        if new_valor:
            sensors[sensor] = new_valor
    else:
        return "Campo inválido.", 400

    return redirect("/manage_sensor")