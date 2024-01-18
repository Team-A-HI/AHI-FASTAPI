import openai
import json
from fastapi import APIRouter, HTTPException, UploadFile, Depends
from typing import List
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .resumegenerator import generate_resume, generate_resume_content
from motor.motor_asyncio import AsyncIOMotorClient
from configset.config import getAPIkey, getModel
import os
import requests
import json

from db.database import db, FileTBL


# FastAPI 라우터
resume_router = APIRouter(prefix="/resume")

# 이력서 데이터를 입력받을 Pydantic 모델

class ResumeData(BaseModel):
    name: str
    phone_number: str
    email: str
    job_title: str
    skills: List[str]
    experiences: List[str]
    experiences_detail: List[str]
    projects: List[str]
    projects_detail: List[str]
    educations: str
    educations_detail: str
    awards_and_certifications: List[str]


# OpenAI API 설정
OPENAI_API_KEY = getAPIkey()
OPENAI_MODEL = getModel()
openai.api_key = OPENAI_API_KEY

async def get_resume_data(file: UploadFile):
    contents = await file.read()
    resume_data = json.loads(contents)
    return resume_data


def save_pdf_info(email, file_name, file_path):
    try:
        # 새 파일 정보 객체 생성
        new_file_info = FileTBL(email=email, file_name=file_name, file_path=file_path)
        # 세션에 추가하고 커밋
        db.add(new_file_info)
        db.commit()
        print("File info saved to database successfully.")
    except Exception as e:
        print(f"Error saving file info to database: {e}")
        db.rollback()


@resume_router.post("/create-resume/")
async def create_resume(file: UploadFile = None, resume_data: ResumeData = Depends()):
    # 파일 업로드가 있는 경우
    if file:
        resume_data = await get_resume_data(file)
    # 파일 업로드가 없는 경우, 챗봇 서비스에서 데이터가 전달됨

    if not resume_data:
        raise HTTPException(status_code=404, detail="이력서 데이터를 찾을 수 없습니다.")

    # 가져온 이력서 데이터를 사용하여 이력서 생성
    chat_response = generate_resume(resume_data)

    if chat_response is None:
        raise HTTPException(status_code=500, detail="이력서 내용 생성 중 오류가 발생했습니다.")

    # 생성된 이력서 내용을 파일로 저장하고 저장된 파일 경로를 반환
    generated_resume_path = generate_resume_content(chat_response)

    # PDF 파일 정보를 데이터베이스에 저장
    save_pdf_info(resume_data.email, generated_resume_path)

    return {"message": "이력서가 성공적으로 생성되었습니다.", "resume_path": generated_resume_path}


@resume_router.get("/download-resume/{filename}")
async def download_resume(filename: str):
    file_path = os.path.join("path_to_saved_resumes", filename)  # 이력서가 저장된 경로
    return FileResponse(file_path, media_type='application/pdf', filename=filename)
