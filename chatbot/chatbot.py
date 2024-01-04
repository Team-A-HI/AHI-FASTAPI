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
# from fastapi.responses import StreamingResponse
# from fastapi import BackgroundTasks
# import asyncio

def create_chatbot_router(wsConnection):
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

    def read_prompt_file(prompt_type: str) -> str:
        # 프롬프트 유형에 따라 파일명 매핑
        file_map = {
            "신입": "beginner_prompt.txt",
            "경력직": "experienced_prompt.txt"
        }

        file_name = os.path.join(BASE_DIR, file_map.get(prompt_type, ""))
        print(f"Trying to read file: {file_name}")

        # 파일이 존재하는지 확인하고 내용 읽기
        if os.path.exists(file_name):
            with open(file_name, "r", encoding="utf-8") as file:
                prompt_text = file.read()
                return prompt_text
        else:
            print("File not found or prompt type not recognized") 
            return "Default system message."



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





    previous_system_content = {}  # 이전 대화의 시스템 콘텐츠 저장



    @CBrouter.post("/")
    async def chatbot_endpoint(message: User):
        user_message = message.message
        prompt_type = message.prompt

        system_message = previous_system_content.get(message.email, "")

        if not system_message:
            # 이전 대화가 없는 경우 파일에서 프롬프트 읽어오기
            system_message = read_prompt_file(prompt_type)

        print(f"Previous system content for {message.email}: {system_message}")


        gpt_response = openai.ChatCompletion.create(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            model=MODEL,
        )

        chatbot_response = gpt_response["choices"][0]["message"]["content"]

        # 이전 대화의 시스템 콘텐츠 업데이트
        previous_system_content[message.email] = f"{system_message}\nQ:{user_message}\nA:{chatbot_response}"

        await update_chatroom(
            email=message.email,
            roomId=message.roomId,
            user_message=user_message,
            prompt=message.prompt,
            chatbot_response=chatbot_response
        )
        
        print("check_data_complete 호출 전")
        print("message.email ==============> ", message.email)
        print("message.roomId ==============> ", message.roomId)

        # 데이터 완성도 확인
        if check_data_complete(message.email, message.roomId):
            # 웹소켓 연결 찾아 메시지 보내기
            websocket = find_websocket_connection(message.email)
            if websocket:
                await wsConnection.send_message("데이터 수집 완료. 이력서를 생성할 수 있습니다.", websocket)

        return {"gptMessage": chatbot_response}



    async def check_data_complete(email: str, roomId: str) -> bool:
        chatroom_data = await db.chatrooms.find_one({"email": email, "roomId": roomId})
        print("check_data_complete 호출 ..........")
        if chatroom_data:
                name_collected = False
                phone_number_collected = False
                email_collected = False
                job_title_collected = False
                skills_collected = False
                experiences_collected = False
                experiences_detail_collected = False
                projects_collected = False
                projects_detail_collected = False
                educations_collected = False
                educations_detail_collected = False
                awards_and_certifications_collected = False

                for message in chatroom_data.get("messageList", []):
                    # 메시지 내용을 분석하여 필요한 정보가 있는지 확인
                    if "name" in message["content"]: # 이름
                        name_collected = True
                    if "phone_number" in message["content"]: # 폰번호
                        phone_number_collected = True
                    if "email" in message["content"]: # 이메일 
                        email_collected = True
                    if "job_title" in message["content"]: # 프론트 / 백 str
                        job_title_collected = True
                    if "skills" in message["content"]: # 기술스택 List[str]
                        skills_collected = True 
                    if "experiences" in message["content"]: # 경력 List[str]
                        experiences_collected = True
                    if "experiences_detail" in message["content"]: # 경력 상세 List[str]
                        experiences_detail_collected = True
                    if "projects" in message["content"]: # 프로젝트 경험 List[str]
                        projects_collected = True
                    if "projects_detail" in message["content"]: # 프로젝트 상세 List[str]
                        projects_detail_collected = True
                    if "educations" in message["content"]: # 학력 str
                        educations_collected = True
                    if "educations_detail" in message["content"]: # 학력 상세 str
                        educations_detail_collected = True
                    if "awards_and_certifications" in message["content"]: # 수상경력 List[str]
                        awards_and_certifications_collected = True
                    
                    # 모든 필요 정보가 수집되었는지 확인
                    if job_title_collected and skills_collected and name_collected and phone_number_collected and email_collected and experiences_collected and experiences_detail_collected and projects_collected and projects_detail_collected and educations_collected and educations_detail_collected and awards_and_certifications_collected:
                        return True

        return False

    # 웹소켓 연결 찾기
    def find_websocket_connection(email: str):
        return wsConnection.active_connections.get(email) 

    return CBrouter