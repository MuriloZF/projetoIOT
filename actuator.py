from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Actuator  # Make sure you have this model defined

actuator_main = Blueprint('actuator_main', __name__, template_folder="templates")

@actuator_main.route("/register", methods=["GET", "POST"])
def register_actuator_page():
    if request.method == "POST":
        try:
            # Get form data
            name = request.form.get("actuator_name")
            command_topic = request.form.get("mqtt_command_topic")
            status_topic = request.form.get("mqtt_status_topic", None)
            
            # Create new actuator
            new_actuator = Actuator(
                name=name,
                command_topic=command_topic,
                status_topic=status_topic,
                state="OFF"  # Default state
            )
            
            # Add to database
            db.session.add(new_actuator)
            db.session.commit()
            
            flash("Atuador registrado com sucesso!", "success")
            return redirect(url_for("actuator_main.manage_actuators"))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao registrar atuador: {str(e)}", "error")
    
    return render_template("register_actuator.html")

@actuator_main.route("/manage")
def manage_actuators():
    devices = Actuator.query.order_by(Actuator.id.desc()).all()
    return render_template("manage_actuators.html", devices=devices)

@actuator_main.route("/delete/<int:actuator_id>", methods=["POST"])
def delete_actuator(actuator_id):
    try:
        actuator = Actuator.query.get_or_404(actuator_id)
        db.session.delete(actuator)
        db.session.commit()
        flash("Atuador removido com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao remover atuador: {str(e)}", "error")
    
    return redirect(url_for("actuator_main.manage_actuators"))

@actuator_main.route("/toggle/<int:actuator_id>", methods=["POST"])
def toggle_actuator(actuator_id):
    try:
        actuator = Actuator.query.get_or_404(actuator_id)
        actuator.state = "ON" if actuator.state == "OFF" else "OFF"
        db.session.commit()
        flash(f"Atuador {actuator.name} {actuator.state}!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao alterar estado: {str(e)}", "error")
    
    return redirect(url_for("actuator_main.manage_actuators"))