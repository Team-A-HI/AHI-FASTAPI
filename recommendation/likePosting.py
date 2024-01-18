from fastapi import APIRouter, Request, Form, HTTPException, FastAPI, File, UploadFile
from pydantic import BaseModel
from typing import List
import chromadb
from chromadb.db.base import UniqueConstraintError
from sentence_transformers import SentenceTransformer
import openai
from typing import List, Optional
from fastapi.responses import JSONResponse
from datetime import datetime
from configset.config import getAPIkey, getModel
import pdfplumber
from io import BytesIO
from sentence_transformers import SentenceTransformer
import ast
from bs4 import BeautifulSoup
import httpx
import json

MODEL = getModel()

model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

client = chromadb.HttpClient(host="15.164.164.18", port=8005)
# client = chromadb.PersistentClient(path="C:\dev\jgsProject\chromaDB")

LIrouter = APIRouter(prefix="/likePosting")

class WorkTypeDTO(BaseModel):
    workCode: int
    workConditions: str
    postingCode: int


class SkillDTO(BaseModel):
    skillCode: int
    skillName: str
    postingCode: int


class PostingExperienceDTO(BaseModel):
    experienceCode: int
    experienceLevel: str
    postingCode: int


class CompanyDTO(BaseModel):
    companyId: int
    email: Optional[str]
    password: Optional[str]
    phoneNumber: Optional[str]
    company: str
    companyType: str
    employeesNumber: int
    establishmentDate: datetime
    companyHomepage: Optional[str]


class PostingDTO(BaseModel):
    postingCode: int
    postingDate: str
    endDate: str
    education: str
    viewCount: int
    location: str
    position: str
    closingForm: str
    content: str
    postingTitle: str
    selectedCareer: Optional[str]
    selectedConditions: Optional[str]
    selectedSkills: Optional[str]
    workTypeList: List[WorkTypeDTO]
    skillList: List[SkillDTO]
    postingExperienceList: List[PostingExperienceDTO]
    company: CompanyDTO


@LIrouter.post("/postingList")
async def get_posting(posting_dto_list: List[PostingDTO]):

    matchingCode = []

    result_list = []
    merged_string = []

    result = []

    existing_posting_codes = {str(posting.postingCode) for posting in posting_dto_list}
    
    for posting in posting_dto_list:

        postingCode = posting.postingCode

        print(postingCode)

        company = posting.company

        postingData = [posting.content , posting.postingTitle , posting.postingDate , posting.endDate, posting.education,
                    company.email , company.company, company.companyType, str(company.employeesNumber),
                    company.establishmentDate]
    


        for work_type in posting.workTypeList:
        
            postingData.append(work_type.workConditions)


        for skill in posting.skillList:
        
            postingData.append(skill.skillName)

    
        for exp in posting.postingExperienceList:
        
            postingData.append(exp.experienceLevel)


        merged_string.append(" ".join(map(str, postingData)))

    all_results = []
        
    for posting in merged_string:



        collection_name = "posting"
        collection = client.get_collection(name=collection_name)

        query_text = posting
        query_embedding = model.encode(query_text)

        result = collection.query(
            # query_texts=[model.encode("spring")],
        query_embeddings=[query_embedding.tolist()],
        n_results=2
        )

        
        if result.get("ids"):
                for id in result["ids"][0]:
                    # 여기서 중복과 postingCode 체크
                    if len(all_results) < 5 and id not in all_results and id not in existing_posting_codes:
                        all_results.append(id)

                    if len(all_results) >= 5:
                        break
    


    print(all_results , "?")

    response_data = {"result": "success", "message": "Your response message", "data": all_results}


    return response_data
