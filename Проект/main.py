from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
import os
from werkzeug.utils import secure_filename  # Для безопасного имени файла


app = Flask(__name__)

UPLOAD_FOLDER = './Ready_doc'  # Папка для сохранения файлов
ALLOWED_EXTENSIONS = {'docx', 'pdf', 'txt'}  # Разрешенные расширения файлов

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Функция для проверки расширения файла
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




# Конфигурация базы данных (SQLite в папке DB)
DATABASE_URL = "sqlite:///./DB/db.db"  # Путь к БД
engine = create_engine(DATABASE_URL, echo=True)  # echo=True для отладки SQL-запросов
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Определение моделей таблиц
class Doctype(Base):
    __tablename__ = "Doctype"
    type = Column(String, primary_key=True, index=True)

class LegalEntities(Base):
    __tablename__ = "LegalEntities"
    name = Column(String, primary_key=True, index=True)
    director = Column(String)

class Ourfirm(Base):
    __tablename__ = "Ourfirm"
    name = Column(String, primary_key=True, index=True)
    director = Column(String)

class ReadyDoc(Base):
    __tablename__ = "ReadyDoc"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)  
    sum = Column(Integer)
    legalEntities = Column(String, ForeignKey("LegalEntities.name"))
    signatories = Column(String)  
    link = Column(String)

class DocTemp(Base):
    __tablename__ = "DocTemp"
    id = Column(Integer, primary_key=True, index=True)
    compName = Column(String, ForeignKey("LegalEntities.name"))
    docType = Column(String, ForeignKey("Doctype.type"))
    link = Column(String)

    legal_entity = relationship("LegalEntities", backref="templates")
    doctype = relationship("Doctype", backref="templates")

# Создание таблиц (если их еще нет)
Base.metadata.create_all(bind=engine)

# Функция для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API endpoint для поиска шаблона
@app.route("/get_template", methods=["POST"])
def get_template():
    db = SessionLocal()
    try:
        data = request.get_json()
        user_input_type = data.get("document_type", "").strip().lower()
        user_input_company = data.get("company_name", "").strip()
        user_input_director = data.get("director_name", "").strip()

        # 1. Нормализация типа документа
        if user_input_type == "заявка":
            document_type = "Заказ"  # Приведение "заявка" к "Заказ"
        elif user_input_type == "заказ":
            document_type = "Заказ" 
        elif user_input_type == "акт":
            document_type = "Акт" 
        elif user_input_type == "отчёт":
            document_type = "Отчет"
        else:
            document_type = user_input_type.capitalize()  # Приведение к нужному виду

        # 2. Поиск шаблона в DocTemp
        template = db.query(DocTemp).join(Doctype).join(LegalEntities).filter(
            LegalEntities.name == user_input_company,
            Doctype.type == document_type
        ).first()


        if template:
            # Шаблон найден
            return jsonify({"template_link": template.link})
        else:
            # Шаблон не найден, проверка и добавление компании/типа при необходимости
            company = db.query(LegalEntities).filter(LegalEntities.name == user_input_company).first()
            if not company:
                # Компания не найдена, добавляем новую
                new_company = LegalEntities(name=user_input_company, director=user_input_director)
                db.add(new_company)
                db.commit()
            else:
                # Компания найдена
                # Проверяем, присутствует ли поле director_name в запросе
                if "director_name" in data:
                    director_name = data["director_name"]
                    if director_name:  # Проверяем, не пустое ли значение
                        company.director = director_name  # Обновляем директора
                        db.commit()  # Сохраняем изменения

            doctype = db.query(Doctype).filter(Doctype.type == document_type).first()
            if not doctype:
                new_doctype = Doctype(type=document_type)
                db.add(new_doctype)
                db.commit()

            return jsonify({"message": "Шаблон не найден. Необходимо создать шаблон вручную."})


    finally:
        db.close() # Не забываем закрывать сессию!
        
@app.route("/add_signed_document", methods=["POST"])
def add_signed_document():
    db = SessionLocal()
    try:
        # Проверяем, есть ли файл в запросе
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']

        # Если пользователь не выбрал файл, браузер отправляет пустой файл
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)  # Безопасное имя файла

            # Создаем папку, если она не существует
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)  # Сохраняем файл

            # Получаем остальные данные из формы
            date = request.form.get("date") #request.form вместо request.get_json()
            hours = request.form.get("hours")
            rate_per_hour = request.form.get("rate_per_hour")
            legalEntities = request.form.get("legalEntities")
            signatories = request.form.get("signatories")

            # Вычисляем сумму контракта
            sum = float(hours) * float(rate_per_hour)

            # Создаем новую запись в таблице ReadyDoc
            new_doc = ReadyDoc(
                date=date,
                sum=sum,
                legalEntities=legalEntities,
                signatories=signatories,
                link=filepath  # Сохраняем путь к файлу
            )

            db.add(new_doc)
            db.commit()

            return jsonify({"message": "Документ успешно добавлен."}), 201

        else:
            return jsonify({"error": "Invalid file type"}), 400

    except Exception as e:
        print(e)  # Логировать ошибку!
        return jsonify({"error": str(e)}), 500

    finally:
         db.close()



if __name__ == "__main__":
    app.run(debug=True)
