    # document_api/routes.py
    from flask import request, jsonify, send_file
    from . import app, db
    from .models import Users, Doctype, LegalEntities, DocTemp, ReadyDoc, Employees
    from .utils import token_required
    from .services.document_service import process_document
    from werkzeug.utils import secure_filename
    import os

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

        if not template_path or not placeholders:
            return jsonify({'error': 'Missing template_path or placeholders'}), 400

        try:
            processed_document = process_document(template_path, placeholders)
            return jsonify({'document': processed_document})  # Возвращаем base64 encoded строку
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # document_api/services/document_service.py
    from docx import Document
    import io
    import base64

    def process_document(template_path, placeholders):
        try:
            document = Document(template_path)

            for paragraph in document.paragraphs:
                for placeholder, value in placeholders.items():
                    if placeholder in paragraph.text:
                        paragraph.text = paragraph.text.replace(placeholder, value)

            output = io.BytesIO()
            document.save(output)
            output.seek(0)

            # Вернуть файл в формате base64 encoded строки
            base64_pdf = base64.b64encode(output.read()).decode('utf-8')

            return base64_pdf

        except Exception as e:
            raise  # Re-raise the exception to be caught in the route
