import openai
import json
from fastapi import APIRouter, HTTPException, UploadFile, Depends
from typing import List
from pydantic import BaseModel
from .resumegenerator import generate_resume, generate_resume_content
from motor.motor_asyncio import AsyncIOMotorClient
from configset.config import getAPIkey, getModel
import requests
import json

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
    return {"message": "이력서가 성공적으로 생성되었습니다.", "resume_path": generated_resume_path}