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
        raise # Re-raise the exception to be caught in the route
