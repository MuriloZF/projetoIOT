from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Flask-Login integration
    def get_id(self):
        return str(self.id)

    @property
    def privilegio(self):
        # Maintain compatibility with existing session["privilegio"] logic
        return 1 if self.is_admin else 0

class Sensor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sensor_id_str = db.Column(db.String(80), unique=True, nullable=False) # e.g., "temperature_default"
    name = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(200), unique=True, nullable=False)
    unit = db.Column(db.String(20))
    # Add other relevant fields as needed
    logs = db.relationship("DeviceLog", backref="sensor", lazy=True)

class Actuator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actuator_id_str = db.Column(db.String(80), unique=True, nullable=False) # e.g., "water_valve_default"
    name = db.Column(db.String(100), nullable=False)
    command_topic = db.Column(db.String(200), unique=True, nullable=False)
    state_topic = db.Column(db.String(200), unique=True, nullable=True) # Optional state topic
    # Add other relevant fields as needed
    logs = db.relationship("DeviceLog", backref="actuator", lazy=True)

class DeviceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_type = db.Column(db.String(10), nullable=False) # "sensor" or "actuator"
    sensor_id = db.Column(db.Integer, db.ForeignKey("sensor.id"), nullable=True)
    actuator_id = db.Column(db.Integer, db.ForeignKey("actuator.id"), nullable=True)
    value = db.Column(db.String(100)) # For sensor readings or actuator states ('ON', 'OFF', temperature value, etc.)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.CheckConstraint("(sensor_id IS NOT NULL AND actuator_id IS NULL AND device_type = 'sensor') OR (sensor_id IS NULL AND actuator_id IS NOT NULL AND device_type = 'actuator')", name="chk_device_log_type"),
    )

