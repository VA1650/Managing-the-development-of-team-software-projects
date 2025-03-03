
from flask import Flask, request, jsonify, abort
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import functools


app = Flask(__name__)

UPLOAD_FOLDER = './Ready_doc'
ALLOWED_EXTENSIONS = {'docx', 'pdf', 'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


DATABASE_URL = "sqlite:///./DB/db.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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


class Employees(Base):
    __tablename__ = "Employees"
    employee = Column(String, primary_key=True, unique=True, index=True)
    rate = Column(Integer, nullable=False)


class Users(Base):
    __tablename__ = "Users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def token_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not auth.username or not auth.password:
            return jsonify({'message': 'Authentication required'}), 401

        db = SessionLocal()
        try:
            user = db.query(Users).filter_by(username=auth.username).first()
            if not user or not user.check_password(auth.password):
                return jsonify({'message': 'Invalid credentials'}), 401
        finally:
            db.close()

        return f(*args, **kwargs)

    return decorated


@app.route('/login', methods=['POST'])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return jsonify({'message': 'Authentication required'}), 401

    db = SessionLocal()
    try:
        user = db.query(Users).filter_by(username=auth.username).first()
        if not user or not user.check_password(auth.password):
            return jsonify({'message': 'Invalid credentials'}), 401

        return jsonify({'message': 'Login successful'})
    finally:
        db.close()


@app.route('/create_user', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'message': 'Missing data'}), 400

    username = data['username']
    password = data['password']

    db = SessionLocal()
    try:
        # Проверяем, существует ли уже пользователь с таким username
        existing_user = db.query(Users).filter(Users.username == username).first()
        if existing_user:
            return jsonify({'message': 'User already exists'}), 400

        new_user = Users(username=username)
        new_user.set_password(password)
        db.add(new_user)
        db.commit()
        return jsonify({'message': 'User created successfully'}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'message': str(e)}), 500
    finally:
        db.close()


@app.route("/get_template", methods=["POST"])
@token_required
def get_template():
    db = SessionLocal()
    try:
        data = request.get_json()
        user_input_type = data.get("document_type", "").strip().lower()
        user_input_company = data.get("company_name", "").strip()
        user_input_director = data.get("director_name", "").strip()

        document_type_mapping = {
            "заявка": "Заказ",
            "заказ": "Заказ",
            "акт": "Акт",
            "отчёт": "Отчет"
        }
        document_type = document_type_mapping.get(user_input_type, user_input_type.capitalize())

        template = db.query(DocTemp).join(Doctype).join(LegalEntities).filter(
            LegalEntities.name == user_input_company,
            Doctype.type == document_type
        ).first()

        if template:
            return jsonify({"template_link": template.link})
        else:
            company = db.query(LegalEntities).filter(LegalEntities.name == user_input_company).first()
            if not company:
                new_company = LegalEntities(name=user_input_company, director=user_input_director)
                db.add(new_company)
                db.commit()
            else:
                if "director_name" in data and data["director_name"]:
                    company.director = data["director_name"]
                    db.commit()

            doctype = db.query(Doctype).filter(Doctype.type == document_type).first()
            if not doctype:
                new_doctype = Doctype(type=document_type)
                db.add(new_doctype)
                db.commit()

            return jsonify({"message": "Шаблон не найден. Необходимо создать шаблон вручную."})

    finally:
        db.close()


@app.route("/add_signed_document", methods=["POST"])
@token_required
def add_signed_document():
    db = SessionLocal()
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            date = request.form.get("date")
            legalEntities = request.form.get("legalEntities")
            signatories = request.form.get("signatories")
            hours_worked_str = request.form.get("hours_worked")
            employee_name = request.form.get("employee_name")  # Получаем имя сотрудника из формы

            if not hours_worked_str or not employee_name:
                return jsonify({"error": "Missing hours_worked or employee_name value"}), 400

            try:
                hours_worked = float(hours_worked_str)
            except ValueError:
                return jsonify({"error": "Invalid hours_worked value"}), 400

            employee = db.query(Employees).filter(Employees.employee == employee_name).first()
            if not employee:
                return jsonify({"error": "Employee not found"}), 404

            hourly_rate = employee.rate
            sum = int(hourly_rate * hours_worked)

            new_doc = ReadyDoc(
                date=date,
                sum=sum,
                legalEntities=legalEntities,
                signatories=signatories,
                link=filepath
            )

            db.add(new_doc)
            db.commit()

            return jsonify({"message": "Документ успешно добавлен."}), 201

        else:
            return jsonify({"error": "Invalid file type"}), 400

    except Exception as e:
        db.rollback()
        print(e)
        return jsonify({"error": str(e)}), 500

    finally:
        db.close()


@app.route("/create_template", methods=["POST"])
@token_required
def create_template():
    db = SessionLocal()
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            company_name = request.form.get("company_name")
            document_type = request.form.get("document_type")

            company = db.query(LegalEntities).filter(LegalEntities.name == company_name).first()
            doctype = db.query(Doctype).filter(Doctype.type == document_type).first()

            if not company:
                return jsonify({"error": "Company not found"}), 400

            if not doctype:
                return jsonify({"error": "Document type not found"}), 400

            new_template = DocTemp(
                compName=company_name,
                docType=document_type,
                link=filepath
            )

            db.add(new_template)
            db.commit()

            return jsonify({"message": "Шаблон успешно создан."}), 201
        else:
            return jsonify({"error": "Invalid file type"}), 400

    except Exception as e:
        db.rollback()
        print(e)
        return jsonify({"error": str(e)}), 500

    finally:
        db.close()


if __name__ == "__main__":
    app.run(debug=True)
