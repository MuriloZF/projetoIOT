from models.db import db
from sqlalchemy.sql import func

class Sensor(db.Model):
    __tablename__ = "sensors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(50))
    value = db.Column(db.Float)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    def save_sensor(name, topic, unit):
        sensor = Sensor(name = name, topic = topic, unit = unit)
        db.session.add(sensor)
        db.session.commit()

    def get_sensors():
        sensors = Sensor.query.all()
        return sensors
    
    def get_single_sensor(id):
        sensor = Sensor.query.filter(Sensor.id == id).first()
        return sensor

        
    def update_sensor(id, name, unit):
        sensor = Sensor.query.filter(Sensor.id == id).first()
        if sensor is not None:
            sensor.name = name
            sensor.unit = unit
            db.session.commit()
            return Sensor.get_sensors()
        
    def delete_sensor(id):
        sensor = Sensor.query.filter(Sensor.id == id).first()

        db.session.delete(sensor)
        db.session.commit()
        return Sensor.get_sensors()

