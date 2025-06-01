from models.db import db
from sqlalchemy.sql import func

class Actuator(db.Model):
    __tablename__ = "Actuators"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    topic_command = db.Column(db.String(100), nullable=False)
    topic_status = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    unit = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    def save_actuator(name, topic_command, topic_status, is_active, unit):
        actuator = Actuator(name = name, topic_command = topic_command, topic_status = topic_status, is_active = is_active, unit = unit)
        db.session.add(actuator)
        db.session.commit()

    def get_actuators():
        actuators = Actuator.query.all()
        return actuators
    
    def get_single_actuator(id):
        actuator = Actuator.query.filter(Actuator.id == id).first()
        return actuator

        
    def update_actuator(id, name, topic_command, topic_status, is_active, unit):
        actuator = Actuator.query.filter(Actuator.id == id).first()
        if actuator is not None:
            actuator.name = name
            actuator.topic_command = topic_command
            actuator.topic_status = topic_status
            actuator.unit = unit 
            actuator.is_active = is_active
            db.session.commit()
            return Actuator.get_actuators()
        
    def delete_actuator(id):
        actuator = Actuator.query.filter(Actuator.id == id).first()

        db.session.delete(actuator)
        db.session.commit()
        return Actuator.get_actuators()

