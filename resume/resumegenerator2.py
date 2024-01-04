# from docx import Document
# import subprocess
# import os
# from docx import Document
# import subprocess
# from typing import List
# from pydantic import BaseModel


# class ResumeData(BaseModel):
#     name: str
#     phone_number: str
#     email: str
#     job_title: str
#     skills: List[str]
#     experiences: List[str]
#     experiences_detail: List[str]
#     projects: List[str]
#     projects_detail: List[str]
#     educations: List[str]
#     educations_detail: List[str]
#     awards_and_certifications: List[str]
    

# def generate_resume_content(data):
#     # 이력서 데이터를 메시지 형식으로 변환
#     messages = [
#         {"role": "system", "content": "당신은 이력서 작성을 도와주는 AI 비서입니다."},
#         {"role": "user", "content": f"이름: {data.name}, 휴대폰 번호: {data.phone_number}, 이메일: {data.email}, 직무: {data.job_title}, 기술 스택: {', '.join(data.skills)}, 경력 사항: {', '.join(data.experiences)}, 프로젝트 내용: {', '.join(data.projects)}, 학력: {', '.join(data.educations)}, 수상 내역 및 자격증: {', '.join(data.awards_and_certifications)}"}
#     ]

#     try:
#         response = call_openai_gpt(messages)
#         chat_response = response['choices'][0]['message']['content']
#         return chat_response
#     except Exception as e:
#         print(f"Error: {e}")
#         return None

# def fill_template(template_path, output_path, context):
#     doc = Document(template_path)

#     for paragraph in doc.paragraphs:
#         for key, value in context.items():
#             if key in paragraph.text:
#                 paragraph.text = paragraph.text.replace(key, value)

#     for table in doc.tables:
#         for row in table.rows:
#             for cell in row.cells:
#                 for key, value in context.items():
#                     if key in cell.text:
#                         cell.text = cell.text.replace(key, value)
    
#     # 최종 문서를 저장
#     doc.save(output_path)
    
# def convert_docx_to_pdf(docx_file_path, pdf_file_path):
#     # LibreOffice 실행 파일 경로
#     libreoffice_path = '/path/to/soffice'  # 실제 경로로 변경 필요

#     # subprocess를 사용하여 DOCX 파일을 PDF로 변환
#     try:
#         subprocess.run([libreoffice_path, '--headless', '--convert-to', 'pdf:writer_pdf_Export', docx_file_path, '--outdir', pdf_file_path.rsplit('/', 1)[0]])
#         print(f"{docx_file_path} 파일을 PDF로 변환하여 {pdf_file_path}에 저장했습니다.")
#     except Exception as e:
#         print(f"변환 중 오류 발생: {e}")  