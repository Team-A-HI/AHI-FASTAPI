from configset.config import getAPIkey,getModel
import openai
from fastapi import APIRouter, UploadFile, File, Form
import pdfplumber
from io import BytesIO
from fastapi.responses import JSONResponse
from pydantic import BaseModel

OPENAI_API_KEY = getAPIkey()
openai.api_key = OPENAI_API_KEY
MODEL = getModel()

userInterViewrouter = APIRouter(prefix="/userinterview")


def gpt_question(userdata):
    prompt = f"""
            1. ai라고 절대 언급하지 말것.
            2. 사과, 후회등의 언어 구성을 하지말것
            3. 같은 응답을 반복하지 말것
            4. 인재를 선발하는 능력이 탁월한 it 개발회사의 베테랑 면접관의 역할을 맡아줘
            5. 답변은 반드시 한국어로 할 것
            6. 답변은 명확하고 구체적으로 하며 gpt의 능력을 최대한 활용할 것
            7. 관련이 없는 정보가 들어온다면 잘못된 답변이라고 말할 것
            8. 컴퓨터 사이언스에 관한 질문을 2개 이상 할 것
            9. {userdata}에 관한 질문 2개 이상 할 것
            11. 오직 질문만 할 것
            12. 심호흡을 하고 천천히 잘 생각한 뒤 대답해줘 잘 수행한다면 선물을 줄게
    """
    
    response = openai.ChatCompletion.create(
      model= MODEL, # 필수적으로 사용 될 모델을 불러온다.
      frequency_penalty=0.3, # 반복되는 내용 값을 설정 한다.
      temperature=0.3,
      messages=[
              {"role": "system", "content": prompt},
              
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



@userInterViewrouter.post("/userinterview")
async def get_userPDF(file: UploadFile = File(...)):

    userdata = await file.read()
    
    with pdfplumber.open(BytesIO(userdata)) as pdf:
        textPDF = [page.extract_text() for page in pdf.pages]
    
    # print(textPDF)
    question =  gpt_question(textPDF)
    print("akdsfhusdf", type(question))
    return JSONResponse(content={"question": question})


class AnswerData(BaseModel):
    answer : str

@userInterViewrouter.post('/sendAnswer')
async def AI_question(answer: AnswerData):
   userAnswer = str(answer)
   feedback = gpt_feedback(userAnswer)
   return {"feedback": feedback}