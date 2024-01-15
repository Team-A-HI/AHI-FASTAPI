from fastapi import APIRouter , Request , Form , HTTPException , FastAPI, File, UploadFile
from pydantic import BaseModel
from typing import List
import chromadb
from chromadb.db.base import UniqueConstraintError
from sentence_transformers import SentenceTransformer
import openai
from typing import List, Optional
from fastapi.responses import JSONResponse
from datetime import datetime
from configset.config import getAPIkey,getModel
import pdfplumber
from io import BytesIO
from sentence_transformers import SentenceTransformer
import ast
from bs4 import BeautifulSoup
import httpx
import json


OPENAI_API_KEY = getAPIkey()
openai.api_key = OPENAI_API_KEY
MODEL = getModel()
UPLOAD_DIR = "recommendation/resumeImg"
client = chromadb.HttpClient(host="52.79.181.213", port=8005)
# client = chromadb.PersistentClient(path="C:\dev\jgsProject\chromaDB")

model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

RErouter = APIRouter(prefix="/recommendation")

def gpt_question(data):
    
    response = openai.ChatCompletion.create(
        model= MODEL, # 필수적으로 사용 될 모델을 불러온다.
        frequency_penalty=0.5, # 반복되는 내용 값을 설정 한다.
        temperature=0.6,
        messages=[
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "{0}여기에 있는 데이터읽어줘".format(data)},
            {"type": "text", "text": "읽은 데이터에서 가진 기술스택 모두 알려줘 임배딩할꺼라 기술스택만 알려줘"},
            {"type": "text", "text": "기술 스택 : 이거붙이지말라고 붙이면 죽여버린다"},
            
            
        #     {
        #         "type": "image_url",
        #         "image_url": {
        #             "url": f"data:image/jpeg;base64,{data}",
        #             "detail" : "high"
        #   },
        # },
      ],
    }
  ],
    max_tokens=1000,
    )
    output_text = response["choices"][0]["message"]["content"]
    
    return output_text

def gpt_selectCompany(data , resume):
    
    response = openai.ChatCompletion.create(
        model= MODEL, # 필수적으로 사용 될 모델을 불러온다.
        frequency_penalty=0.5, # 반복되는 내용 값을 설정 한다.
        temperature=0.6,
        messages=[
    {
        "role": "user",
         "content": [
            {"type": "text", "text": "{0}여기에 있는 공고 데이터를 읽어 주세요.".format(data)},
            {"type": "text", "text": "{0}여기에 있는 이력서 읽어 주세요. ".format(resume)},
            {"type": "text", "text" : "이력서 안의 experiences 란의 유무를 먼저 확인하세요. 만약 경력이 없는 신입이라면, 이력서 내에 해당 experiences 란이 존재하지 않습니다. "},
            {"type": "text", "text" : "이력서의 주인이 experience 란이 존재하지 않는 신입이라면, 신입 개발자를 뽑는 공고만 선별해야 합니다"},
            {"type": "text", "text" : "경력 개발자일 경우 experiences 란 안의 재직 기간을 계산하여, 조건에 충족되는 공고를 추천해 주세요."},
            {"type": "text", "text" : "이력서와 채용 공고의 데이터를 분석하고 비교한 후, 이력서와 가장 잘 맞는 공고의 id를 선별해 보내 주세요."},
            {"type": "text", "text" : "ids를 선별하는 것 외에 다른 모든 행위들을 금지합니다."},
            {"type": "text", "text" : "만약 공고에 신입을 뽑는 공고가 3개 이하라면 ids를 3개 이하로 선별해도 됩니다."},
            {"type": "text", "text" : "ids를 반드시 Json 형태로 뽑아 주세요." "{ matching_job_ids : [] } 형태로 뽑아 주세요."},
            {"type": "text", "text" : "넌 아무말도 하지말고 Json 객체만 뽑아줘 그냥 ids 만 뽑아 헛소리하지말고"},
    ],
    }
  ],
    
    )
    output_text = response["choices"][0]["message"]["content"]
    
    return output_text


@RErouter.post("/resume")
async def get_posting(file: UploadFile = File(...)):

        print(file , "gdgd")
    
        # 파일을 비동기 방식으로 읽고 동기 방식으로 얻기
        content = await file.read()

        # filename = f"{str(uuid.uuid4())}.jpg"  # uuid로 유니크한 파일명으로 변경
        # file_path = os.path.join(UPLOAD_DIR, filename)

        with pdfplumber.open(BytesIO(content), encoding='UTF8') as pdf:
            # 각 페이지의 텍스트를 추출하여 리스트로 저장
            text_content = [page.extract_text() for page in pdf.pages]

        print(text_content)

        resume = "\n".join(text_content)

        print(resume)

        # with open(file_path, "wb") as fp:
        #     fp.write(content)

        question = gpt_question(resume)

        print(question)

        collection_name = "posting"
        collection = client.get_collection(name=collection_name)

        query_text = question
        query_embedding = model.encode(query_text)

        result = collection.query(
            # query_texts=[model.encode("spring")],
            query_embeddings=[query_embedding.tolist()],
            n_results=7
        )

        print(result)

        postingList = []

        for i, (document_html, document_ids) in enumerate(zip(result['documents'][0], result['ids'][0])):
            soup = BeautifulSoup(document_html, 'html.parser')
            # 추출한 정보 출력 또는 사용
            print(f"Document {i + 1} ID: {document_ids}")
            print(f"Document {i + 1} Text:")
            print(soup.get_text(strip=True))
            
            postingData = document_ids , soup.get_text(strip=True)
            postingList.append('\n'.join(postingData))


        # print("gdgd", postingList , "gdgd")

        answer = gpt_selectCompany(postingList , resume)

        print(answer)

        answer = answer.replace("```json", "").replace("```", "").strip()

        # print(answer)


        spring_server_url = "http://localhost:8001/recommendation/selectResume"

        #  # Spring 서버로 데이터 전송
        async with httpx.AsyncClient() as spring:
            response = await spring.post(spring_server_url, json=json.loads(answer) , headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            print("데이터 전송 성공")

            return {"success": True, "response": response.json()}
        else:
            print("데이터 전송 실패")
        return {"success": False, "error": "Spring 서버로의 데이터 전송 실패"}

        
        

