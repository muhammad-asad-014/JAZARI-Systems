import sys

from flask import Flask, session, render_template, current_app
import os
import random
import string
from .adminViews import adminViews
from .teacherViews import teacherViews
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from .manager import PluginManager
from flask_socketio import SocketIO
import importlib
import json
import importlib.util
import sys

csrf = CSRFProtect()

db = SQLAlchemy()
DB_NAME = 'database.db'
socketio = SocketIO(async_mode='threading', cors_allowed_origins="*")

PLUGINS_DIR = os.path.join(os.path.dirname(__file__), 'plugins')

from .auth import auth


def register_plugin_dynamic(folder_name):
    """Register plugin with versioned folder names"""
    try:
        plugin_path = os.path.join(PLUGINS_DIR, folder_name)
        manifest_path = os.path.join(plugin_path, 'manifest.json')

        if not os.path.exists(manifest_path):
            print(f"No manifest.json in {folder_name}")
            return False

        with open(manifest_path) as f:
            manifest = json.load(f)

        plugin_id = manifest.get('id')  # e.g., "ikaris"
        if not plugin_id:
            print(f"No 'id' in manifest of {folder_name}")
            return False

        # === BEST METHOD: Use file-based import ===
        init_file = os.path.join(plugin_path, '__init__.py')
        
        if not os.path.exists(init_file):
            print(f"No __init__.py in {folder_name}")
            return False

        # Create a spec and load the module
        spec = importlib.util.spec_from_file_location(
            f"plugins.{folder_name}", 
            init_file
        )
        
        if spec is None:
            print(f"Could not create spec for {folder_name}")
            return False

        plugin_module = importlib.util.module_from_spec(spec)
        sys.modules[f"plugins.{folder_name}"] = plugin_module
        spec.loader.exec_module(plugin_module)

        # Get the blueprint
        bp = getattr(plugin_module, 'bp', None)
        if not bp:
            print(f"No 'bp' blueprint found in {folder_name}")
            return False

        url_prefix = f"/{plugin_id}"

        if url_prefix not in current_app.blueprints:
            current_app.register_blueprint(bp, url_prefix=url_prefix)
            print(f"SUCCESS: {manifest.get('name')} registered at {url_prefix}")
            return True
        else:
            print(f"{manifest.get('name')} already registered")
            return True

    except Exception as e:
        print(f"Failed to register {folder_name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_all_plugins(app):
    """Load all plugins from plugins/ directory"""
    if not os.path.exists(PLUGINS_DIR):
        os.makedirs(PLUGINS_DIR)
        return

    # Make sure we have access to current_app inside the function
    with app.app_context():
        for folder in os.listdir(PLUGINS_DIR):
            full_path = os.path.join(PLUGINS_DIR, folder)
            if os.path.isdir(full_path):
                register_plugin_dynamic(folder)

def create_admin():
    from .models import Administrator
    if not Administrator.query.first():
        admin = Administrator(
            username="admin",
            fname="John",
            lname="Doe",
            email="admin@jazari.com",
            role= 'admin',
            password=generate_password_hash('admin',  method='pbkdf2:sha256')
        )
        from . import db
        db.session.add(admin)
        db.session.commit()
        print("Initial admin record created!")
    else:
        print('admin record exists.')


def create_photo_folder():
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    PHOTOS_FOLDER = os.path.join(BASE_PATH, '.student-pictures')
    SETTINGS_PATH = os.path.join(BASE_PATH, '.system-settings')
    if not os.path.exists(PHOTOS_FOLDER):
        os.mkdir(PHOTOS_FOLDER)

    if not os.path.exists(SETTINGS_PATH):
        os.mkdir(SETTINGS_PATH)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'JAZARI'.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*()", k=32))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app)

    app.register_blueprint(adminViews, url_prefix = '/admin')
    app.register_blueprint(teacherViews, url_prefix = '/teacher')
    app.register_blueprint(auth, url_prefix = '/')

    load_all_plugins(app)
    # manager = PluginManager(app, plugin_folder=os.path.join(os.path.dirname(__file__), 'plugins'))
    # manager.load_plugins()

    @app.context_processor
    def inject_plugins():
        installed = []
        plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
        
        if os.path.exists(plugins_dir):
            for folder in os.listdir(plugins_dir):
                manifest_path = os.path.join(plugins_dir, folder, 'manifest.json')
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path) as f:
                            data = json.load(f)
                            installed.append({
                                'id': data.get('id'),
                                'name': data.get('name'),
                                'version': data.get('version'),
                                'author': data.get('author'),
                                'summary': data.get('summary'),
                                'home': data.get('home', 'home'),           # Important
                                'folder_name': folder
                            })
                    except Exception as e:
                        print(f"Error loading manifest for {folder}: {e}")
        
        return dict(active_plugins=installed)

    @app.errorhandler(403)
    def error_403(e):
        return render_template('error.html', 
            code="403", 
            title="Restricted Access", 
            message="You don't have the clearance for this sector."), 403

    @app.errorhandler(404)
    def error_404(e):
        return render_template('error.html', 
            code="404", 
            title="Lost in Space", 
            message="The page you're looking for has vanished into the void."), 404

    @app.errorhandler(500)
    def error_500(e):
        return render_template('error.html', 
            code="500", 
            title="Internal Glitch", 
            message="Our servers encountered an unexpected reality shift."), 500


    
    from .models import Administrator,Class, Student, Teacher
    create_database(app)
    create_photo_folder()
    with app.app_context():
        system_setup()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        user_role = session.get('user_role')
        if user_role == 'admin':
            return Administrator.query.get(user_id)
        elif user_role == 'teacher':
            return Teacher.query.get(user_id)
        return None
    
    return app



def create_database(app):
    if not os.path.exists("core/"+DB_NAME):
        with app.app_context():
            from . import db
            db.create_all()
            create_admin()
            print("Database created!")


def system_setup():
    from .models import Settings
    if not Settings.query.first():
        from . import db
        system = Settings()
        db.session.add(system)
        db.session.commit()
        print("Default setting setted.")
    else:
        print("Default setting exists.")