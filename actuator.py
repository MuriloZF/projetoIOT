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

@actuator.route("/update_actuator", methods=["GET", "POST"])
def updUser():
    global actuators
    if request.method == "POST":
        actuator = request.form["actuator"]
        field = request.form["field"]
    else:
        actuator = request.form.get("actuator")
        field = request.form.get("field")

    if not actuator or actuator not in actuators:
        return "Usuário não encontrado.", 400

    if field == "actuator":
        new_actuator = request.form["new_actuator"]
        if new_actuator:
            actuators[new_actuator] = actuators.pop(actuator)
    elif field == "valor":
        new_valor = request.form["new_valor"]
        if new_valor:
            actuators[actuator] = new_valor
    else:
        return "Campo inválido.", 400

    return redirect("/manage_actuator")