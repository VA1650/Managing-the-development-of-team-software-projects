
# document_api/routes.py
from flask import request, jsonify, send_file
from . import app, db
from .models import Users, Doctype, LegalEntities, DocTemp, ReadyDoc, Employees, Settings
from .utils import token_required
from .services.document_service import process_document
from werkzeug.utils import secure_filename
import os
import datetime
from workalendar.europe import Russia
import calendar #Импорт calendar для определения кол-ва дней в месяце

TEMPLATE_FOLDER = os.path.join(Config.APP_ROOT, '../Templates') # Используем Путь к папке с шаблонами

@app.route("/get_template", methods=["POST"])
@token_required
def get_template():
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

    template = DocTemp.query.join(Doctype).join(LegalEntities).filter(
        LegalEntities.name == user_input_company,
        Doctype.type == document_type
    ).first()

    if template:
        template_path = os.path.join(TEMPLATE_FOLDER, os.path.basename(template.link)) #Получаем путь к шаблону
        return jsonify({"template_path": template_path})  # Отправляем путь к шаблону на фронтенд
    else:
        company = LegalEntities.query.filter(LegalEntities.name == user_input_company).first()
        if not company:
            new_company = LegalEntities(name=user_input_company, director=user_input_director)
            db.session.add(new_company)
            db.session.commit()
        else:
            if "director_name" in data and data["director_name"]:
                company.director = data["director_name"]
                db.session.commit()

        doctype = Doctype.query.filter(Doctype.type == document_type).first()
        if not doctype:
            new_doctype = Doctype(type=document_type)
            db.session.add(new_doctype)
            db.session.commit()

        return jsonify({"message": "Шаблон не найден. Необходимо создать шаблон вручную."})

@app.route('/process_document', methods=['POST'])
@token_required
def process_document_route():
    data = request.get_json()
    template_path = data.get("template_path")  # Получаем путь с фронтенда
    placeholders = data.get("placeholders")
    sum = data.get("sum")
    legalEntities = data.get("legalEntities")
    signatories = data.get("signatories")
    date_str = data.get("date") #дата из запроса
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date() # Преобразуем строку в объект datetime.date

    if not template_path or not placeholders:
        return jsonify({'error': 'Missing template_path or placeholders'}), 400

    try:
        processed_document = process_document(template_path, placeholders)

        # Получаем последний номер документа за текущий месяц
        last_doc = ReadyDoc.query.filter(db.extract('year', ReadyDoc.date) == date.year,
                                        db.extract('month', ReadyDoc.date) == date.month).order_by(ReadyDoc.document_number.desc()).first()

        if last_doc:
            next_document_number = last_doc.document_number + 1
        else:
            next_document_number = 1

        # Создаем новую запись о документе
        new_document = ReadyDoc(
            date=date,
            sum=sum,
            legalEntities=legalEntities,
            signatories=signatories,
            link=template_path,  # Или как вы сохраняете ссылку на документ
            document_number=next_document_number
        )
        db.session.add(new_document)
        db.session.commit()

        return jsonify({'document': processed_document})  # Возвращаем base64 encoded строку
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/calculate_salary', methods=['POST'])
@token_required
def calculate_salary():
    data = request.get_json()
    employee_name = data.get('employee')
    hours_worked = data.get('hours')

    employee = Employees.query.filter_by(employee=employee_name).first()
    if not employee:
        return jsonify({'error': 'Employee not found'}), 400

    try:
        hours_worked = float(hours_worked)  # Преобразуем часы в число с плавающей точкой
    except ValueError:
        return jsonify({'error': 'Invalid hours format'}), 400

    salary_before_vat = employee.rate * hours_worked

    # Получаем ставку НДС из настроек
    settings = Settings.query.first()
    if settings:
        vat_rate = settings.vat_rate
    else:
        vat_rate = 0.05  # Используем значение по умолчанию, если настроек нет

    vat_amount = salary_before_vat * vat_rate
    salary_with_vat = salary_before_vat + vat_amount

    return jsonify({
        'employee': employee_name,
        'salary_before_vat': salary_before_vat,
        'vat_rate': vat_rate,
        'vat_amount': vat_amount,
        'salary_with_vat': salary_with_vat
    })

@app.route('/working_days', methods=['POST'])
@token_required
def get_working_days():
    data = request.get_json()
    year = data.get('year')
    month = data.get('month')

    if not year or not month:
        return jsonify({'error': 'Year and month are required'}), 400

    try:
        year = int(year)
        month = int(month)
    except ValueError:
        return jsonify({'error': 'Invalid year or month format'}), 400

    cal = Russia()
    month_dates = [datetime.date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1])] #Генерируем все даты месяца
    working_days = [day for day in month_dates if cal.is_working_day(day)]

    if working_days:
        start_date = working_days[0].strftime('%Y-%m-%d') #Форматируем дату
        end_date = working_days[-1].strftime('%Y-%m-%d')
        return jsonify({'start_date': start_date, 'end_date': end_date})
    else:
        return jsonify({'message': 'No working days in the specified month'}), 404
with app.app_context():  # Создаем контекст приложения Flask
    if not Settings.query.first():  # Проверяем, есть ли уже настройки
        default_settings = Settings(vat_rate=0.05)  # Создаем настройки по умолчанию
        db.session.add(default_settings)
        db.session.commit()

with app.app_context():
    db.create_all()