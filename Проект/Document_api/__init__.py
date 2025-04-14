from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config
import os

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)

# Импортируем routes после инициализации app и db, чтобы избежать circular imports
from . import routes, models

# Создаем директорию для загрузки файлов, если ее нет
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
