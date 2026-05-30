import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from app.config import Config
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO
import os
import sys


app = Flask(__name__)
csrf = CSRFProtect()
app.config.from_object(Config)
csrf.init_app(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'


is_testing = 'pytest' in sys.modules or 'unittest' in sys.modules or os.environ.get('FLASK_ENV') == 'testing'
async_mode = 'threading' if is_testing else None

socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins="*", manage_session=False)

@login.user_loader
def load_user(id):
    from app.models import User
    return User.query.get(int(id))


from app import routes, models, socket_handlers