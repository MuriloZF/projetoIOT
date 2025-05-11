from flask import Blueprint, render_template, request, redirect, url_for

actuator = Blueprint('actuator', __name__, template_folder="templates")

actuators = {
    "Mangueira de água" : "Desligado",
    "Ventilador" : "Desligado"
}

@actuator.route("/register_actuator")
def register_actuator():
    return render_template("register_actuator.html")

@actuator.route("/create_actuator", methods=["POST"])
def actuator_sensor():
    global actuators
    if request.method == "POST":
        actuator = request.form["actuator"]
        valor = request.form["valor"]
    else:
        actuator = request.args.get["actuator"]
        valor = request.args.get["valor"]
    actuators[actuator] = valor
    return render_template("manage_actuator.html", device=actuators)

@actuator.route("/manage_actuator")
def manage_actuator():
    return render_template("manage_actuator.html", device = actuators)

@actuator.route("/del_actuator", methods=["GET", "POST"])
def del_actuator():
    global actuators
    if request.method == "POST":
        actuator = request.form["actuator"]
    else:
        actuator = request.args.get["actuator", None]
    actuators.pop(actuator)
    return render_template("manage_actuator.html", device=actuators)
