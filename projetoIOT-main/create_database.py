import os
import uuid
from app import app, db  # Import app and db instance from the main app file
from models.models import User, Sensor, Actuator, DeviceLog # Import models

# Define the default admin user credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "changeme" # User MUST change this default password after first login

# Define the default device topics as provided by the user
DEFAULT_TOPICS = {
    'sensor': {
        'temperature': b'iot/sensor/temperatura',
        'humidity': b'iot/sensor/umidade'
    },
    'actuator': {
        'ventilador': {
            'command': b'iot/actuator/Ventilador/command',
            'status': b'iot/actuator/Ventilador/status'
        },
        'mangueira': {
            'command': b'iot/actuator/Mangueira_de_agua/command',
            'status': b'iot/actuator/Mangueira_de_agua/status'
        },
        'aquecedor': {
            'command': b'iot/actuator/Aquecedor/command',
            'status': b'iot/actuator/Aquecedor/status'
        }
    }
}

def create_admin_user():
    """Checks if the admin user exists and creates it if not."""
    admin_user = User.query.filter_by(username=ADMIN_USERNAME).first()
    if not admin_user:
        print(f"Creating default admin user: {ADMIN_USERNAME}")
        admin = User(username=ADMIN_USERNAME, is_admin=True)
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        try:
            db.session.commit()
            print(f"Admin user {ADMIN_USERNAME} created successfully with password {ADMIN_PASSWORD}.")
            print("IMPORTANT: Please change this default password immediately after logging in.")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {e}")
    else:
        print(f"Admin user {ADMIN_USERNAME} already exists.")

def create_default_devices():
    """Creates default sensor and actuator entries based on DEFAULT_TOPICS if they don't exist."""
    print("Checking/Creating default devices in database based on TOPICS...")
    created_count = 0
    try:
        # Create default sensors
        for name, topic_bytes in DEFAULT_TOPICS['sensor'].items():
            topic_str = topic_bytes.decode('utf-8')
            sensor = Sensor.query.filter_by(topic=topic_str).first()
            if not sensor:
                # Generate a default name and ID
                default_name = name.replace('_', ' ').capitalize() + " Padrão"
                sensor_id_str = f"sensor_{name}_default"
                unit = "°C" if name == 'temperature' else "%" if name == 'humidity' else None
                
                new_sensor = Sensor(
                    sensor_id_str=sensor_id_str,
                    name=default_name,
                    topic=topic_str,
                    unit=unit
                )
                db.session.add(new_sensor)
                print(f"  Creating sensor: {default_name} (Topic: {topic_str})")
                created_count += 1

        # Create default actuators
        for name, topics in DEFAULT_TOPICS['actuator'].items():
            command_topic_str = topics['command'].decode('utf-8')
            status_topic_str = topics['status'].decode('utf-8')
            
            actuator = Actuator.query.filter_by(command_topic=command_topic_str).first()
            if not actuator:
                # Generate a default name and ID
                default_name = name.replace('_', ' ').capitalize() + " Padrão"
                actuator_id_str = f"actuator_{name}_default"
                
                new_actuator = Actuator(
                    actuator_id_str=actuator_id_str,
                    name=default_name,
                    command_topic=command_topic_str,
                    state_topic=status_topic_str,
                    # state="Desconhecido" # Removed: Actuator model has no state field
                )
                db.session.add(new_actuator)
                print(f"  Creating actuator: {default_name} (Cmd Topic: {command_topic_str})")
                created_count += 1
        
        if created_count > 0:
            db.session.commit()
            print(f"Committed {created_count} new default devices.")
        else:
            print("All default devices based on TOPICS already exist in the database.")
            
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default devices: {e}")


if __name__ == "__main__":
    with app.app_context():
        print("Initializing database...")
        # Get the database path from app config
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///database.db")
        db_path = None
        if db_uri.startswith("sqlite:///"):
            db_path = db_uri.replace("sqlite:///", "", 1)
            if not os.path.isabs(db_path):
                 basedir = os.path.abspath(os.path.dirname(__file__))
                 db_path = os.path.join(basedir, db_path)
            db_dir = os.path.dirname(db_path)
            # Create the directory if it doesn't exist (for SQLite)
            if not os.path.exists(db_dir):
                 try:
                     os.makedirs(db_dir)
                     print(f"Created database directory: {db_dir}")
                 except OSError as e:
                     print(f"Error creating directory {db_dir}: {e}")
        else:
            print(f"Warning: Non-SQLite database URI detected ({db_uri}). Directory creation skipped.")

        # Create tables
        print("Creating database tables (if they don't exist)...")
        try:
            db.create_all()
            print("Tables checked/created successfully.")
        except Exception as e:
            print(f"Error creating tables: {e}")
            exit(1) # Exit if table creation fails

        # Create the default admin user
        create_admin_user()

        # Create default devices based on TOPICS dictionary
        create_default_devices()

        print("\nDatabase initialization script finished.")
        if db_path:
            print(f"Database file located at: {db_path}")

