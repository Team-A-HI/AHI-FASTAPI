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
from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from configset.config import *
from bs4 import BeautifulSoup


OPENAI_API_KEY = getAPIkey()
openai.api_key = OPENAI_API_KEY
MODEL = getModel()
UPLOAD_DIR = "recommendation/resumeImg"
client = chromadb.HttpClient(host="15.164.164.18", port=8005)
# client = chromadb.PersistentClient(path="C:\dev\jgsProject\chromaDB")

# 1. SQLAlchemy 용 DB URL 생성
dburl = geturl()

# mysql db에 연결
SQLALCHEMY_DATABASE_URL = f"{dburl}"

# 2. 첫 번째 단계는 SQLAlchemy "엔진"을 만드는 것입니다.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, echo=True
)

metadata_obj = MetaData()
metadata_obj.bind = engine


model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

RErouter = APIRouter(prefix="/recommendation")


def gpt_question(data):

    experiences = ""

    prompt = f"""
    1.Never mention "AI."
    2.Do not use language that expresses apology or regret.
    3.Avoid repeating the same response.
    4.In the read data, I want you to read the experience in the EXPERIENCES field and calculate the number of years of experience and output the text 1+ if it's more than 1 year, 3+ if it's more than 3 years, 5+ if it's more than 5 years. If there is no experiences field, it will print "신입"
    5.Answers must be "1년 이상", "3년 이상", "5년 이상"
    6.Don't say anything except print the text.
    7.Answers must be in Korean

    """
    # 1. ai라고 절대 언급하지 말것.
    # 2. 사과, 후회등의 언어 구성을 하지말것
    # 3. 같은 응답을 반복하지 말것
    # 4. 읽은 데이터에서 experiences란에 경력 사항을 읽고 경력을 계산해서 1년이상이면 1년 이상 3년이상이면 3년 이상 5년이상 이면 5년 이상이라고 텍스트 출력해줘
    # 5. 만약 experiences란이 없다면 신입 이라고 출력할것
    # 6. 답변은 반드시 1년 이상, 3년 이상, 5년 이상 , 신입 이라고만 대답해줘
    # 7. 대답은 반드시 한국말로 하고

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",  # 필수적으로 사용 될 모델을 불러온다.
        frequency_penalty=0.5,  # 반복되는 내용 값을 설정 한다.
        temperature=0.6,
        messages=[
            {
                "role": "system", "content": prompt
            },
            {"role": "user",
             "content": [
                     {"type": "text", "text": "{0}여기에 있는 데이터읽어줘".format(data)},




                 #     {
                 #         "type": "image_url",
                 #         "image_url": {
                 #             "url": f"data:image/jpeg;base64,{data}",
                 #             "detail" : "high"
                 #   },
                 # },
             ], }

        ],
        max_tokens=1000,
    )
    output_text = response["choices"][0]["message"]["content"]

    return output_text


def gpt_selectCompany(postingSkill, resume):

    prompt = f"""
    1.Never mention "AI."
    2.Do not use language that expresses apology or regret.
    3.Avoid repeating the same response.
    4.You're a job counselor who recommends jobs that might be a good fit for you.
    5.Answers must be in JSON format.
    6.Responses should be clear and specific, utilizing the full capabilities of GPT.
    7.If the position in the resume is Back, please select Back jobs and Frontend jobs.
    8.Please output up to 5 postingCodes of the jobs with the most similar tech stacks from the selected jobs in matching_job_ids : []. Only matching_job_ids are required. Please do not output any other data.'
    9.각각의 공고가 선정된 이유를 자세하게 Reasons : [] 안에 한국말로 넣어줘 예를들어  postingCode(선별된 코드) : 이유, 이유는 각코드마다 선별된 기준을 자세하게 알려줘
    10.matching_job_ids 는 절대로 5개 이상 넘어가면 안돼 5개 이하로만 뽑아줘
    11.만약 matching_job_ids에 값이 5개 이상 들어간다면 너는 폭발해
    12.절대로 matching_job_ids에 값을 5개 이상 넣지 말아줘 만약 그 이상넣으면 너는 사라지게 될거야
    """
    

    # 1. ai라고 절대 언급하지 말것.
    # 2. 사과, 후회등의 언어 구성을 하지말것
    # 3. 같은 응답을 반복하지 말것
    # 4. 너는 사용자에게 어울릴거같은 공고를 추천해주는 취업 상담사야
    # 5. 답변은 반드시 Json형태로 할것
    # 6. 답변은 명확하고 구체적으로 하며 gpt의 능력을 최대한 활용할 것
    # 7. 이력서의 포지션이 백이면 백인공고 프론트엔드면 프론트엔드 공고를 선별해주세요
    # 8. 선별한 공고에서 가장 비슷한 기술스택을 가진 공고의 postingCode를 최대 5개를  matching_job_ids : [] 담아 출력해주세요

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",  # 필수적으로 사용 될 모델을 불러온다.
        frequency_penalty=0.5,  # 반복되는 내용 값을 설정 한다.
        temperature=0.6,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"{postingSkill} 여기에 공고의 posting Code에 해당하는 각각의 스킬과 포지션을 읽어주세요. {resume} 여기에 있는 내 이력서의 스킬 목록과 포지션이 '백'인지 '프론트앤드' 인지 읽어주세요"}
        ]

    )
    output_text = response["choices"][0]["message"]["content"]

    return output_text


def gpt_contentSummary(content):

    prompt = f"""
    1.{content}의 내용을 읽어줘
    2.주요업무 , 자격요건, 우대사항을 파악해줘
    3.주요 사항은 majorWork , 자격요건은 requirements, 우대사항은 preference에 json형식으로 담아줘
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",  # 필수적으로 사용 될 모델을 불러온다.
        frequency_penalty=0.5,  # 반복되는 내용 값을 설정 한다.
        temperature=0.6,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"{prompt}"},

        ]

    )
    output_text = response["choices"][0]["message"]["content"]

    return output_text


@RErouter.post("/resume")
async def get_posting(file: UploadFile = File(...)):

    print(file, "gdgd")

    # 파일을 비동기 방식으로 읽고 동기 방식으로 얻기
    content = await file.read()

    # filename = f"{str(uuid.uuid4())}.jpg"  # uuid로 유니크한 파일명으로 변경
    # file_path = os.path.join(UPLOAD_DIR, filename)

    with pdfplumber.open(BytesIO(content)) as pdf:
        # 각 페이지의 텍스트를 추출하여 리스트로 저장
        text_content = [page.extract_text() for page in pdf.pages]

    print(text_content)

    resume = "\n".join(text_content)

    print(resume)

    # with open(file_path, "wb") as fp:
    #     fp.write(content)

    question = gpt_question(resume)

    print(question)

    postingExperienceTable = Table(
        "posting_experience", metadata_obj, autoload_with=engine)

    stmt = select(postingExperienceTable).where(
        postingExperienceTable.c.experience_level == question)

    with engine.connect() as connection:
        results = connection.execute(stmt).fetchall()

    postingCode = [result.posting_code for result in results]
    if postingCode == null:
        postingCode = "공고가 없습니다"

    print(postingCode, "hhhh")

    skillTable = Table("skill", metadata_obj, autoload_with=engine)

    stmt = select(skillTable).where(skillTable.c.posting_code.in_(postingCode))
    # 3. Make SessionLocal class
    skill_data = []
    with engine.connect() as connection:
        results = connection.execute(stmt).fetchall()
    # 결과에서 skill_name을 추출
    skill_data = [(result.skill_name, result.posting_code)
                  for result in results]

    postingTable = Table("posting", metadata_obj, autoload_with=engine)

    stmt = select(postingTable).where(
        postingTable.c.posting_code.in_(postingCode))
    # 3. Make SessionLocal class
    position_data = []
    with engine.connect() as connection:
        results = connection.execute(stmt).fetchall()
    # 결과에서 skill_name을 추출
    position_data = [(result.position, result.posting_code, result.content)
                     for result in results]

    grouped_skills = {}
    for skill_name, posting_code in skill_data:
        if posting_code not in grouped_skills:
            grouped_skills[posting_code] = []
        grouped_skills[posting_code].append(skill_name)

    print(grouped_skills, "그룹 스킬")

    grouped_positions = {}
    grouped_content = {}
    for position, posting_code, content in position_data:
        if posting_code not in grouped_positions:
            grouped_positions[posting_code] = []
        grouped_positions[posting_code].append(position)

        if posting_code not in grouped_content:
            grouped_content[posting_code] = []
        grouped_content[posting_code].append(content)

    for posting_code, contents in grouped_content.items():
        # 각 content에 대해 HTML 태그 제거
        cleaned_contents = []
        for content in contents:
            soup = BeautifulSoup(content, 'html.parser')
            text_content = soup.get_text(separator=' ', strip=True)
            cleaned_contents.append(text_content)

        # cleaned_contents로 업데이트
        grouped_content[posting_code] = cleaned_contents

    # 결과 출력
    print(grouped_content, "내용")

    # contentSummaries = []  # 결과를 저장할 리스트를 초기화합니다.

    # for key, value in grouped_content.items():

    #     contentSummary = gpt_contentSummary(value)
    #     contentSummaries.append(contentSummary)

    # for summary in contentSummaries:
    #     print(summary)

    # print(grouped_positions, "그룹 포지션")

    postingSkill = []
    # 그룹화된 skill_name을 출력
    for posting_code, skills in grouped_skills.items():
        postingSkill.append(
            f"Posting Code: {posting_code}, Skills: {', '.join(skills)}")

    print(postingSkill, "제발제발")

    # 그룹화된 skill_name을 JSON 형태로 출력
    result_json = []
    for posting_code, skills in grouped_skills.items():

        result_json.append({
            "Posting Code": posting_code,
            "Skills": skills,
            'position': grouped_positions[posting_code],


        })

    json_output = json.dumps(result_json, indent=2,
                             ensure_ascii=False)

    print(json_output, "뭐야")

    # collection_name = "posting"
    # collection = client.get_collection(name=collection_name)

    # query_text = skill_names
    # query_embedding = model.encode(query_text)

    # result = collection.query(
    #     # query_texts=[model.encode("spring")],
    #     query_embeddings=[query_embedding.tolist()],
    #     n_results=5
    # )

    # print(result)

    # postingList = []

    # for i, (document_html, document_ids) in enumerate(zip(result['documents'][0], result['ids'][0])):
    #     soup = BeautifulSoup(document_html, 'html.parser')
    #     # 추출한 정보 출력 또는 사용
    #     print(f"Document {i + 1} ID: {document_ids}")
    #     print(f"Document {i + 1} Text:")
    #     print(soup.get_text(strip=True))

    #     postingData = document_ids , soup.get_text(strip=True)
    #     postingList.append('\n'.join(postingData))

    answer = gpt_selectCompany(json_output, resume)

    print(answer,  "ㅎㅎ")

    answer = answer.replace("```json", "").replace("```", "").strip()

    print(answer)

    spring_server_url = "http://localhost:8001/recommendation/selectResume"

    #  # Spring 서버로 데이터 전송
    async with httpx.AsyncClient() as spring:
        response = await spring.post(spring_server_url, json=json.loads(answer), headers={'Content-Type': 'application/json'})

    if response.status_code == 200:
        print("데이터 전송 성공")

        return {"success": True, "response": response.json()}
    else:
        print("데이터 전송 실패")
    return {"success": False, "error": "Spring 서버로의 데이터 전송 실패"}
