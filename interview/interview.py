from fastapi import FastAPI, APIRouter, Body, File, Request, UploadFile, Depends, HTTPException
import openai
from pydantic import BaseModel
from configset.config import getAPIkey,getModel
from typing import List
import pdfplumber
from db.database import *


Interview_router = APIRouter(prefix='/interview')

OPENAI_API_KEY = getAPIkey()
MODEL = getModel()
openai.api_key = OPENAI_API_KEY

# 클라이언트에게서 받은 데이터 타입을 확인하기 위한 클래스
class InterviewData(BaseModel):
    searchQuery : str

# 클라이언트에서 정보를 받아서 모델에 질문을 생성한다.
@Interview_router.post('/makequestion')
async def AIiterview(searchQuery: InterviewData):
    # json 형태로 들어온다, 매개값으로 넘기기 위해서 캐스팅(형변환) 해준다 json -> str -> int
    search_Code_str = searchQuery.searchQuery
    search_Code = int(search_Code_str)
    # 클라이언트에서 전달받은 공고 번호로 db에서 로직을 실행하고 값을 저장 (기술 스택이 담긴다)
    skillSetData = findPosting(search_Code)
    # 함수를 호출하고 리턴 값은 question에 저장
    question = gpt_question(skillSetData)
    # question은 openai API에서 json으로 넘겨주기 때문에 바로 클라이언트에게 넘겨준다.
    return {"question" : question}



class AnswerData(BaseModel):
    answer : str

# 사용자에 답변을 받아서 피드백 해준다
@Interview_router.post('/test')
async def AI_question(answer: AnswerData):
   print('ok')
#    userAnswer = str(answer)
#    feedback = gpt_feedback(userAnswer)
#    return {"feedback": feedback}


# lid open함수로 파일 읽기
def UserResume(PDF_FILE_PATH):
    pdf = pdfplumber.open(PDF_FILE_PATH)
    pages = pdf.pages
    user = ""
    for page in pages:
        sub = page.extract_text()
        user += sub
    return user

# gpt로 질문을 생성해주는 함수
def gpt_question(skillSetData):
    prompt = f"""
    1.Never mention "AI."
    2.Do not use language that expresses apology or regret.
    3.Avoid repeating the same response.
    4.Act as a veteran interviewer for an IT development company with exceptional talent recruitment skills.
    5.Responses must be in Korean.
    6.Responses should be clear and specific, utilizing the full capabilities of GPT.
    7.If irrelevant information is included, state that the response is incorrect.
    8.Ask a question related to computer science.
    9.Ask two questions about {skillSetData}.
    10.Only ask questions.
    11.Take a deep breath, think carefully, and then respond. If you do well, I'll give you a gift.
    """
            # 1. ai라고 절대 언급하지 말것.
            # 2. 사과, 후회등의 언어 구성을 하지말것
            # 3. 같은 응답을 반복하지 말것
            # 4. 인재를 선발하는 능력이 탁월한 it 개발회사의 베테랑 면접관의 역할을 맡아줘
            # 5. 답변은 반드시 한국어로 할 것
            # 6. 답변은 명확하고 구체적으로 하며 gpt의 능력을 최대한 활용할 것
            # 7. 관련이 없는 정보가 들어온다면 잘못된 답변이라고 말할 것
            # 8. 컴퓨터 사이언스에 관한 질문을 할 것
            # 9. {skillSetData}에 관한 질문 두가지 할 것
            # 11. 오직 질문만 할 것
            # 12. 심호흡을 하고 천천히 잘 생각한 뒤 대답해줘 잘 수행한다면 선물을 줄게
            
    
    response = openai.ChatCompletion.create(
      model= MODEL, # 필수적으로 사용 될 모델을 불러온다.
      frequency_penalty=0.3, # 반복되는 내용 값을 설정 한다.
      temperature=0.3,
      messages=[
              {"role": "system", "content": prompt},
            #   {"role": "system", "content": f"{posting_code}"},
            #   {"role": "system", "content": f"{UserResume}의 이력서를 보고 질문을 해줘"},
              
          ])
    output_text = response["choices"][0]["message"]["content"]
    
    print(output_text)
    return output_text


def gpt_feedback(userAnswer):
    Answerprompt = f"""
            1. ai라고 절대 언급하지 말것.
            2. 사과, 후회등의 언어 구성을 하지말것
            3. 같은 응답을 반복하지 말것
            4. 인재를 선발하는 능력이 탁월한 it 개발회사의 베테랑 면접관의 역할을 맡아줘
            5. 답변은 반드시 한국어로 할 것
            6. 답변은 명확하고 구체적으로 하며 gpt의 능력을 최대한 활용할 것
            7. 관련이 없는 정보가 들어온다면 잘못된 답변이라고 말할 것
            8. "{userAnswer}을 듣고 피드백을 해줄 것"
            9. 심호흡을 하고 천천히 잘 생각한 뒤 대답해줘 잘 수행한다면 선물을 줄게
    """
    response = openai.ChatCompletion.create(
      model=MODEL,
      frequency_penalty=0.3, # 반복되는 내용 값을 설정 한다.
      temperature=0.3,
      messages=[
          {"role": "system", "content": Answerprompt},
          {"role": "system", "content": f"{userAnswer} 대한 답을 듣고 더 나은 답변을 피드백 해줘"},
          
      ]
   )
    output_text = response["choices"][0]["message"]["content"]
    
    print(output_text)
    return output_text

