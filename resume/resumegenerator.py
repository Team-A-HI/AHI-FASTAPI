from docx import Document
import os
import subprocess

# LibreOffice 실행 파일 경로 설정
libreoffice_path = 'C:\\Program Files\\LibreOffice\\program\\soffice.exe'

# 이력서 템플릿 파일 경로
template_path = 'tem11.docx'

# 텍스트 치환 함수
def replace_text_in_paragraph(paragraph, context):
    for run in paragraph.runs:
        for key, value in context.items():
            if key in run.text:
                run.text = run.text.replace(key, '' if value is None else value)

# 이력서 템플릿을 채우고 저장하는 함수
def generate_resume(template_path, output_path, resume_data):
    try:
        doc = Document(template_path)

        context = {
            '{Name}': resume_data.get("name"),
            '{Phone}': resume_data.get("phone_number"),
            '{Email}': ', '.join(resume_data.get("email")),
            '{Git}': resume_data.get("git"),
            '{JobTitle}': resume_data.get("job_title"),
            '{Skills}': ', '.join(resume_data.get("skills", [])),
            '{Experiences}': ', '.join(resume_data.get("experiences", [])),
            '{ExperiencesDetail}': ', '.join(resume_data.get("experiences_detail", [])),
            '{Projects}': ', '.join(resume_data.get("projects", [])),
            '{ProjectsDetail}': ', '.join(resume_data.get("projects_detail", [])),  
            '{Education}': ', '.join(resume_data.get("educations", [])),
            '{EducationDetail}': ', '.join(resume_data.get("educations_detail", [])),
            '{AwardsAndCertifications}': ', '.join(resume_data.get("awards_and_certifications", [])),
        }

        for paragraph in doc.paragraphs:
            replace_text_in_paragraph(paragraph, context)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_text_in_paragraph(paragraph, context)

        doc.save(output_path)
        print("Document created successfully. File path:", output_path)
    except Exception as e:
        print(f"Error: {e}")

# Docx 파일을 PDF로 변환하는 함수
def convert_to_pdf(docx_path, pdf_path, libreoffice_path):
    try:
        subprocess.run([libreoffice_path, '--headless', '--convert-to', 'pdf', docx_path, '--outdir', os.path.dirname(pdf_path)])
        print(f"PDF conversion successful. File path: {pdf_path}")
    except Exception as e:
        print(f"Error during PDF conversion: {e}")

# 이 함수는 chat_response를 받아서 이력서 내용을 생성하고 파일로 저장하는 역할을 합니다.
# 필요한 작업을 수행하도록 구현하십시오.
# 예시로 파일에 저장하고 파일 경로를 반환하도록 작성합니다.
def generate_resume_content(chat_response):
    generated_resume_path = 'path_to_generated_resume.docx'  # 예시 경로

    # chat_response를 이력서 내용으로 사용하고 파일로 저장
    with open(generated_resume_path, 'w', encoding='utf-8') as file:
        file.write(chat_response)

    return generated_resume_path

# 함수 호출
resume_data = {...}  # 이력서 데이터
output_path_docx = f'{resume_data["name"]}_resume.docx'
output_path_pdf = f'{resume_data["name"]}_resume.pdf'

generate_resume(template_path, output_path_docx, resume_data)

# DOCX 파일을 PDF로 변환
convert_to_pdf(output_path_docx, output_path_pdf, libreoffice_path)
