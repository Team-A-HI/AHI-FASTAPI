from fastapi import APIRouter
import openai
from typing import List
from pydantic import BaseModel
from configset.config import getAPIkey, getModel
import os
from .database import get_database
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi import Body
from typing import Dict, Optional
import re


CBrouter = APIRouter(prefix="/chatbot")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db = get_database()

OPENAI_API_KEY = getAPIkey()
openai.api_key = OPENAI_API_KEY
MODEL = getModel()

class User(BaseModel):
    email: str
    roomId: str
    prompt: str
    message: str



# 채팅 내용 조회 api
@CBrouter.post("/userchatrooms")
async def get_user_chatrooms(request_body: dict = Body(...)):
    email = request_body.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user_data = await db.chatrooms.find_one({"email": email})
    
    if user_data:
        chatrooms = user_data.get("chatroomList", [])
        # 각 채팅방에 프롬프트 정보 추가
        for room in chatrooms:
            room['prompt'] = room.get('prompt', 'Default prompt')  # 프롬프트가 없을 경우 디폴트 값 추가

        return chatrooms
    else:
        print("User data not found")
        return JSONResponse(content={"email": email, "chatroomList": []}, status_code=404)
    



# mongoDB 데이터 저장
async def update_chatroom(email, roomId, user_message, prompt, chatbot_response):
    user_data = await db.chatrooms.find_one({"email": email})

    if user_data:
        # 이미 해당 이메일에 대한 데이터가 있는 경우
        chatroom_exists = False
        for room in user_data.get("chatroomList", []):
            if room["roomId"] == roomId:
                # 해당 roomId가 이미 존재하는 경우
                chatroom_exists = True
                # 저장할 데이터 구조
                room["messageList"].append({"sender": "사용자", "content": user_message})
                room["messageList"].append({"sender": "챗봇", "content": chatbot_response})
                room["prompt"] = prompt
                break

        if not chatroom_exists:
            # 채팅방이 존재하지 않는 경우 새로운 채팅방 생성
            user_data["chatroomList"].append({
                "roomId": roomId,
                "messageList": [
                    {"sender": "사용자", "content": user_message},
                    {"sender": "챗봇", "content": chatbot_response}
                ],
                "prompt": prompt
            })

        # 업데이트된 데이터베이스 정보를 업데이트
        await db.chatrooms.update_one({"email": email}, {"$set": user_data}, upsert=True)
    else:
        # 해당 이메일에 대한 데이터가 없는 경우 새로운 데이터 생성
        new_user_data = {
            "email": email,
            "chatroomList": [
                {
                    "roomId": roomId,
                    "messageList": [
                        {"sender": "사용자", "content": user_message},
                        {"sender": "챗봇", "content": chatbot_response}
                    ],
                    "prompt": prompt
                }
            ]
        }
        await db.chatrooms.insert_one(new_user_data)



# 채팅방 삭제 api
@CBrouter.post("/deleteChatRoom")
async def delete_chatroom(request_data: dict = Body(...)):
    email = request_data.get("email")
    room_id = request_data.get("roomId")

    # db에서 사용자의 도큐먼트 찾기
    user_data = await db.chatrooms.find_one({"email": email})

    if user_data:
        # 해당 사용자 채팅방 목록에서 특정 roomId를 가진 채팅방 찾아서 삭제
        new_chatroom_list = [room for room in user_data["chatroomList"] if room["roomId"] != room_id]
        await db.chatrooms.update_one({"email": email}, {"$set": {"chatroomList": new_chatroom_list}})
        return {"detail": "채팅방 삭제 성공"}
    else:
        raise HTTPException(status_code=404, detail="유저가 존재하지 않습니다")





# 이전 채팅 기록을 포함하여 GPT 프롬프트 생성
def create_gpt_prompt(previous_chat, new_user_message, chatbot_response, prompt_type):
    # 이전 채팅 기록이 없을 때만 기본 프롬프트를 설정
    if not previous_chat:
        if prompt_type == "신입":
            base_prompt = f""" 
                답변하실 때는 아래의 규칙을 꼭 지켜주시기 바랍니다.
                1. 맨 처음 대화에 답변할 때 "안녕하세요! 신입 개발자 준비생이시군요!"라는 인사말로 시작한 뒤 이어서 답변해주세요.
                2. 개발자들이 경력 개발자들의 이직 이력서를 작성할 수 있도록 도와주는 상황입니다.
                3. 사용자에게 이름, 학력, 백앤드와 프론트엔드 중 원하는 직무, 본인의 기술 스택, 프로젝트 경험, 자격증에 대한 정보를 필수적으로 추출합니다.
                4. 각 항목에 대한 사용자의 답변 중 부족하다고 느껴지는 부분이 있으면 해당 항목에 대한 내용을 유도하는 질문을 합니다.
                5. 다른 곳에서 정보를 찾는 것을 절대 권장하지 않습니다.
                6. 한국어로 존댓말을 사용해야 하며, AI임을 언급하지 않고 인간의 조언과 전문적인 지식을 제공해야 합니다.
                7. 답은 명확하고 구체적이어야 하며, gpt의 능력을 최대한 활용해야 합니다.
                8. 사용자가 자신의 정보를 단순 나열만한 이력서를 작성하는 것과 깔끔하고 보기 쉬운 이력서를 작성하는 것은 전혀 다른 이야기라는 것을 알게 합니다.
                9. 베테랑 개발자 출신 인터뷰어로서 어떤 항목이 필요한지, 항목의 우선순위는 무엇인지, 신입 개발자의 이력서에 무엇을 넣어야 하는지 안내해야 합니다.
                10. 인사는 대화가 시작될 때 맨 처음 한번만 합니다. 이후 답변에서는 인사를 하지 말아주세요.
            """
        elif prompt_type == "경력직":
            base_prompt = f""" 
                답변하실 때는 아래의 규칙을 꼭 지켜주시기 바랍니다.
                1. 맨 처음 대화에 답변할 때 "안녕하세요! 이직을 원하는 경력직 개발자시군요!"라는 인사말로 시작한 뒤 이어서 답변해주세요.
                2. 개발자들이 경력 개발자들의 이직 이력서를 작성할 수 있도록 도와주는 상황입니다.
                3. 사용자에게 이름, 학력, 백앤드와 프론트엔드 중 원하는 직무, 본인의 기술 스택, 경력 상세 내용, 자격증에 대한 정보를 필수적으로 추출합니다.
                4. 각 항목에 대한 사용자의 답변 중 부족하다고 느껴지는 부분이 있으면 해당 항목에 대한 내용을 유도하는 질문을 합니다.
                5. 다른 곳에서 정보를 찾는 것을 절대 권장하지 않습니다.
                6. 한국어로 존댓말을 사용해야 하며, AI임을 언급하지 않고 인간의 조언과 전문적인 지식을 제공해야 합니다.
                7. 답은 명확하고 구체적이어야 하며, gpt의 능력을 최대한 활용해야 합니다.
                8. 사용자가 자신의 정보를 단순 나열만한 이력서를 작성하는 것과 깔끔하고 보기 쉬운 이력서를 작성하는 것은 전혀 다른 이야기라는 것을 알게 합니다.
                9. 베테랑 개발자 출신 인터뷰어로서 어떤 항목이 필요한지, 항목의 우선순위는 무엇인지, 경력 개발자의 이력서에 무엇을 넣어야 하는지 안내해야 합니다.
                10. 인사는 대화가 시작될 때 맨 처음 한번만 합니다. 이후 답변에서는 인사를 하지 말아주세요.
            """
        else:
            base_prompt = "기본 프롬프트 내용"
        full_prompt = base_prompt
    else:
        full_prompt = previous_chat

    # 새로운 채팅 기록 추가
    updated_chat = f"사용자: {new_user_message}\n챗봇: {chatbot_response}"
    print("============================ [create_gpt_prompt] 새로운 채팅기록 추가 updated_chat ============================ \n", updated_chat)
    full_prompt += f"\n{updated_chat}"
    print("============================ [create_gpt_prompt] 새로운 채팅기록 추가 full_prompt ============================ \n", full_prompt)

    return full_prompt




# 이전 대화의 시스템 콘텐츠 저장할 딕셔너리
previous_system_content = {}

@CBrouter.post("/")
async def chatbot_endpoint(message: User):
    user_message = message.message
    prompt_type = message.prompt

    # 이전 대화 내용을 previous_system_content 딕셔너리에서 가져오기
    previous_chat = previous_system_content.get((message.email, message.roomId), "")    
    print("================================= Previous chat ================================= \n", previous_chat)

    # 새로운 GPT 프롬프트 생성
    full_prompt = create_gpt_prompt(previous_chat, user_message, "", prompt_type)
    print("================================= Full prompt ================================= \n", full_prompt)


    # 사용자 메시지를 extract_resume_data 함수에 전달하여 이력서 데이터 추출
    resume_data = await extract_resume_data(user_message)

    # 추출된 데이터 출력 - 테스트용
    print("!!!!!!!!!!!!!!!!!!!!!! [extract_resume_data]로 추출된 이력서 데이터 !!!!!!!!!!!!!!!!!!!!!! \n", resume_data, "여기까지")

    gpt_response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": full_prompt},
            {"role": "user", "content": user_message}
        ]
    )

    chatbot_response = gpt_response["choices"][0]["message"]["content"]


    # 이전 대화 내용 업데이트
    updated_chat = f"사용자: {user_message}\n챗봇: {chatbot_response}"
    previous_system_content[(message.email, message.roomId)] = full_prompt + f"\n{updated_chat}"
    print("============================== Updated previous_system_content ============================== \n", previous_system_content[(message.email, message.roomId)])

    await update_chatroom(
        email=message.email,
        roomId=message.roomId,
        user_message=user_message,
        prompt=message.prompt,
        chatbot_response=chatbot_response
    )



    return {"gptMessage": chatbot_response}



# 채팅 내용 분석 및 추출 api
# GPT 모델을 사용하여 주어진 사용자의 메시지를 분석하고, 그 메시지에서 이력서에 필요한 데이터를 추출
# 함수 내부에서 GPT API를 호출하여 사용자의 메시지(message)에 대한 모델의 응답을 받고, 이 응답에서 이력서 데이터를 파싱
# 이 함수의 반환값은 ^주어진 메시지를 분석한 결과^로, 이력서의 각 항목에 대한 데이터가 포함된 딕셔너리
# 개별 메시지에 대한 분석
@CBrouter.post("/analyze") # 테스트 후 지우기
async def extract_resume_data(message: str) -> Dict[str, Optional[str]]:

    extraction_prompt = f"""
                        너는 사용자의 채팅을 분석 후 이력서에 들어갈 필수 항목들을  추출할거야.
                        아래 항목들이 니가 추출해야될 13가지 데이터 목록이고, 사용자의 채팅에서 각 항목에 맞는 내용을 추출해내야돼.
                        1. name
                        2. phone_number
                        3. email
                        4. git
                        5. job_title
                        6. skills
                        7. experiences
                        8. experiences_detail
                        9. projects
                        10. projects_detail
                        11. educations
                        12. educations_detail
                        13. awards_and_certifications

                        사용자의 채팅을 받아서 분석해보고 위의 13가지 항목과 비교해서 맞는 항목에 관련 데이터를 담아서
                        {{"name": "사용자이름"}} 와 같은 json형태로 데이터를 반환해줘
                        name, phone_number, email, git, job_title은 스트링으로 받으면 되고, 나머지는 배열로 담아줘(ex. {{ "job_title": "백엔드 엔지니어","skills": ["자바", "파이썬", "리액트", "오라클"],
                        "experiences": [ "라이브쇼핑 백엔드 시스템 구축 및 보수 (카카오)", "실시간 방송 재생 정보 HTTP에서 Socket 방식으로 전환하여 대역폭 리스크 감소"], "projects": ["라이브쇼핑 방송 송출 서비스 Backend API 개발 및 운영"]}})

                        주의할 점은 
                        1. 최종학력을 물어볼때 졸업년도도 함께 질문해줘. 그리고 학력은 educations, 졸업년도는 educations_detail에 담아줘
                        2. 경력을 질문할 때 이후 세부사항도 질문해줘. 그리고 experiences항목에는 회사명과 직책을 넣고,   experiences_detail 항목에는 프로젝트의 세부사항을 넣어줘.
                        
                        마지막으로 json데이터 이외에 그 어떤 말도 하지말고 데이터만 보내줘야돼. 만약 채팅내용에 추출할 데이터가 없는 경우에는 아무것도 반환하지마.
    """


    # GPT로부터 응답 받기
    gpt_response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": extraction_prompt},
            {"role": "user", "content": message}
        ]
    )


    # GPT 모델의 응답을 직접 반환
    return gpt_response["choices"][0]["message"]["content"]
   




# 사용자의 메시지와 이전에 수집된 데이터를 기반으로 새 데이터를 추출하고 통합하는 함수
# extract_resume_data 함수를 사용하여 새로운 사용자 메시지에서 데이터를 추출하고, 이 데이터를 이전에 수집된 데이터와 통합
# 분석 결과를 기존 데이터와 통합
async def update_and_extract_resume_data(message: str, previous_data: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    # GPT 모델에게 데이터 추출 요청
    extracted_data = await extract_resume_data(message)

    # 이전 데이터와 새로 추출된 데이터 통합
    # 통합할 때 중복을 막아야되는데....
    for key, value in extracted_data.items():
        if value is not None:
            previous_data[key] = value

    return previous_data


# 예시: 모든 데이터가 수집되었는지 확인하는 함수
def is_resume_complete(resume_data: Dict[str, Optional[str]]) -> bool:
    return all(value is not None for value in resume_data.values())