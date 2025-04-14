import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///../DB/db.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = './Ready_doc'
    ALLOWED_EXTENSIONS = {'docx', 'pdf', 'txt'}
    APP_ROOT = os.path.dirname(os.path.abspath(__file__)) # Явно указываем корень приложения
    
