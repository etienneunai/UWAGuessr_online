import os

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
default_db_path = 'sqlite:///' + os.path.join(basedir, 'app.db')
default_db_url = 'postgresql://uwaguessr@localhost:5432/uwaguessr'

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or (
        default_db_url if os.environ.get('FLASK_ENV') == 'production' else default_db_path
    )
    SECRET_KEY = os.environ.get('UWAGUESSR_SECRET_KEY')

    # R2 Configuration
    R2_ENABLED = os.environ.get('R2_ENABLED', 'false').lower() == 'true'
    R2_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL', '')
    R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID', '')
    R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY', '')
    R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'uwaguessr-photos')
    PHOTO_BASE_URL = os.environ.get('PHOTO_BASE_URL', '')

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_pre_ping': True,
    }