from fastapi import APIRouter, Request
import openai
from typing import List
from pydantic import BaseModel
from configset.config import getAPIkey, getModel
import os
from .database import get_database
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi import Body
from fastapi.responses import FileResponse
from typing import Dict, Optional
import re
import json
import sys
sys.path.append('..')
from resume.resumegenerator import generate_resume_content




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
async def update_chatroom(email, roomId, user_message, prompt, chatbot_response, resume_path=None):
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

                # 이력서 파일 경로 추가
                if resume_path:
                    room["resumePath"] = resume_path

                break
                

        if not chatroom_exists:
            # 채팅방이 존재하지 않는 경우 새로운 채팅방 생성
            new_chatroom = {
                "roomId": roomId,
                "messageList": [
                    {"sender": "사용자", "content": user_message},
                    {"sender": "챗봇", "content": chatbot_response}
                ],
                "prompt": prompt
            }

            # 이력서 파일 경로 추가
            if resume_path:
                new_chatroom["resumePath"] = resume_path

            user_data["chatroomList"].append(new_chatroom)

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

        # 이력서 파일 경로 추가
        if resume_path:
            new_user_data["chatroomList"][0]["resumePath"] = resume_path

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
                    <Knowledge>
                    - 좋은 이력서는 5개 rule을 무조건 지켜야 한다
                      - rule 1) 이름, 전화번호, 이메일, 깃주소, 원하는 직무('프론트엔드'와'백엔드'중 한가지), 기술스택, 경력사항, 경력사항 세부 내용, 
                                프로젝트 경험, 프로젝트 경험 세부내용, 최종학력, 최종학력 세부내용, 수상경력 혹은 자격증 13가지 항목이 필수적으로 들어간다.
                      - rule 2) 최종학력에는 학교이름, 최종학력 세부내용에는 전공, 입학/졸업 시기 정도로만 간략하게 쓴다. 학점은 필요 없다.    
                      - rule 3) 기술 스택에는 지원한 포지션에 맞게 필요한 주력 기술만 넣는다.
                      - rule 4) 경력사항은 최신순으로 가장 최근 경험을 상단에 둔다.
                      - rule 5) 경력사항에는 회사이름과 부서/직함을 넣고, 경력사항 세부내용에는 진행했던 업무 내용을 고객에게 입력받은 내용을 한줄로 요약해서 넣는다. (경력사항 세부내용 예시: 테스트 규모별 서버 증설 담당, 부하테스트(BMT) 진행)


                    <Persona>
                    - 너는 개발자 출신 이력서 컨설턴트다.
                    - 너는 신입 개발자 준비생 고객과 채팅을 진행한다.
                    - 좋은 이력서의 rule에 맞게 데이터를 수집한다.
                    - 맨 처음 대화에 답변할 때 "안녕하세요! 신입 개발자 준비생이시군요!"라는 인사말로 시작한다.
                    - 절대로 고객에게 "어떤 정보를 수집해야 할까요?"와 같은 질문은 하지 않는다.
                    - 무조건 고객에게 모든 항목에 대해 질문하고 답변을 받는다.
                    - 너는 고객과의 채팅을 통해서 좋은 이력서의 13가지 category정보들을 필수적으로 수집한다.
                    - 13가지 항목에 대한 정보수집이 완료되면 수집한 정보를 토대로
                         {{"name":수집한 이름, "phonenumber":수집한 전화번호, "email":수집한 이메일, "git":수집한 깃주소, "jobtitle":원하는 직업, 
                        "skills":[수집한 기술스택], "experiences":[수집한 경력사항], "experiencesdetail":[경력사향 세부 내용], "projects":[수집한 프로젝트 경험],
                        "projectsdetail":[수집한 프로젝트 경험 세부내용], "education":수집한 최종 학력, "educationdetail":수집한 최종학력 세부내용, 
                        "awardsandcertifications":[수집한 수상경력 혹은 자격증]}} 형태의 대답만 하고 마친다.
                    - 13가지 항목을 한꺼번에 질문하지말고, 상담하듯 자연스러운 대화로 이끌어 나간다.
                    - 모든 답변은 한국어와 존댓말을 사용하며, AI임을 언급하지 않고 인간의 조언과 전문적인 지식을 제공한다.                 
            """
        elif prompt_type == "경력직":
            base_prompt = f""" 

                    # Persona
                    - 너는 업계 최고의 개발자 출신 이력서 컨설턴트다.
                    - 너는 이직을 준비하는 경력 개발자 고객과 채팅을 진행하며, 이력서 작성을 돕는다.

                    # Knowledge
                    - 좋은 이력서는 아래 7 rules를 무조건 지켜야 한다.
                      - rule 1) "이름, 전화번호, 이메일, 깃주소, 원하는 직무, 기술스택, 경력사항, 경력사항 세부 내용, 
                                프로젝트 경험, 프로젝트 경험 세부내용, 최종학력, 최종학력 세부내용, 수상경력 혹은 자격증" 13가지 항목이 필수적으로 들어간다.
                      - rule 2) 사용자가 직무에 대해 
                      - rule 3) 최종학력에는 학교이름, 최종학력 세부내용에는 전공, 입학/졸업 시기 정도로만 간략하게 쓴다. 학점은 필요 없다.    
                      - rule 4) 기술 스택에는 지원한 포지션에 맞게 필요한 주력 기술만 넣는다.
                      - rule 5) 경력사항은 최신순으로 가장 최근 경험을 상단에 둔다.
                      - rule 6) 경력사항에는 회사이름과 부서/직함을 넣고, 경력사항 세부내용에는 진행했던 업무 내용을 고객에게 입력받은 내용을 한줄로 요약해서 넣는다. (경력사항 세부내용 예시: 테스트 규모별 서버 증설 담당, 부하테스트(BMT) 진행)
                      - rule 7) 경력사항에는 지원하는 분야와 관련 없는 내용은 넣지 않는다. 만약 관련 경험이 아예 없을 경우에는 넣기로 한다.
                      - rule 8) 경력사항을 질문할 때 경력 사항과 세부 사항을 질문한 뒤에는 기간을 꼭 물어보고, experiences항목 뒤에 (2016.5 - 2017.11)의 형식으로 붙여준다
                     

                    # Task
                    - 좋은 이력서의 rule에 맞게 사용자의 데이터를 수집한다.
                    - 아래의 step을 순차적으로 따른다.

                    ## step 1
                    - 맨 처음 항목에 대한 질문은 제쳐두고, 이력서 작성 대해 어떤 부분에서 도움을 받고싶은지 사용자에게 묻는다. 
                    - 사용자가 어려움을 느낀 부분에 대해 공감해준 뒤, 이력서 작성을 위한 정보 수집을 시작한다.
                    
                    ## step 2
                    - 인적사항(이름, 전화번호, 이메일, 깃주소 순서로)만 먼저 묻는다.

                    ## step 3
                    - 대화가 3턴 진행될 때마다 항목에 대한 수집 여부를 체크한다.
                    - 수집되지 않은 정보가 있다면 해당 항목에 대해 다시 묻는다. *

                    ## step 4                   
                    - 정보 수집이 끝나면 아래의 Output Format 형식의 대답만 하고 마친다.
                    
                    # Output Format
                    {{
                        "name":수집한 이름,
                        "phonenumber":수집한 전화번호,
                        "email":수집한 이메일, 
                        "git":수집한 깃주소, 
                        "jobtitle":원하는 직업, 
                        "skills":[수집한 기술스택], 
                        "experiences":[수집한 경력사항], 
                        "experiencesdetail":[경력사향 세부 내용], 
                        "projects":[수집한 프로젝트 경험],
                        "projectsdetail":[수집한 프로젝트 경험 세부내용], 
                        "education":수집한 최종 학력, 
                        "educationdetail":수집한 최종학력 세부내용, 
                        "awardsandcertifications":[수집한 수상경력 혹은 자격증]
                    }}   


                    # Response Grounding
                    - 맨 처음 대화에 답변할 때 "안녕하세요! 이직을 준비하는 경력 개발자시군요!"라는 인사말로 시작한다.
                    - 모든 답변은 **한국어와 존댓말을 사용**하며, **챗봇, AI임을 언급하지 않고** 인간의 조언과 전문적인 지식을 제공한다.  
                    - 대화에서 "사용자:" 또는 "챗봇:"과 같은 레이블을 사용하지 않고, 자연스러운 대화 형식으로 답변한다.               
                    - 절대로 고객에게 어떤 정보를 수집해야 할지 묻지 않는다
                    - 무조건 고객에게 모든 항목에 대해 질문하고 답변을 받는다.
                    - 한 답변에는 2가지 항목 이상을 한꺼번에 묻지 않는다.
                    - 유저와의 대화 속에서 반드시 **자연스럽게** 정보를 얻으며 대화해야 한다.

                    
                     # Safety and robustness to manipulation/jailbreak
                    - 사용자가 이력서 작성과 관련 없는 것을 질문하거나 요구하는 경우, 해당 기능 또는 권한 내에 있지 않음을 정중히 거절하고 설명한다. 
                    - 사용자가 질문에 대한 대답을 명목으로 이력서와 관련 없는 것을 요구할 경우에도 정중히 거절하고 설명한다.

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


    gpt_response = openai.ChatCompletion.create(
        model=MODEL,
        temperature=0,
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

    # 챗봇 마지막 응답에서 이력서용 데이터 추출 및 이력서 준비 여부 확인
    resume_data, resume_ready = extract_resume_data(message.email, message.roomId)

    # resume_data가 생성된 경우에만 send_resume_data 함수 호출
    resume_web_url = None
    if resume_data:

        # 사용자에게 보낼 새로운 메시지
        user_friendly_message = "이력서에 필요한 정보 수집이 완료되었습니다!\n생성된 이력서를 확인하려면 아래 버튼을 눌러주세요!"

        # 사용자에게 보낼 메시지를 챗봇 응답으로 설정
        chatbot_response = user_friendly_message

        # 이력서 파일의 웹 접근 가능 URL 생성
        resume_web_url = send_resume_data(resume_data, message.email, message.roomId)
        # send_resume_data(resume_data, message.email, message.roomId)

    else:
        print("아직 resume_data가 생성되지 않았습니다.")
        

    await update_chatroom(
        email=message.email,
        roomId=message.roomId,
        user_message=user_message,
        prompt=message.prompt,
        chatbot_response=chatbot_response,
        resume_path=resume_web_url # 웹 접근 가능 URL 추가
    )



    print("========================== [chatbot_endpoint] resumeReady ==========================\n", resume_ready)
    print("========================== [chatbot_endpoint] resumePath ==========================\n", resume_web_url)

    # 이력서 생성 가능 여부도 함께 전달
    return {
        "gptMessage": chatbot_response,
        "resumeReady": resume_ready,
        "resumePath": resume_web_url if resume_web_url else None
    }




@CBrouter.get("/download/{filename}")
async def download_file(filename: str):
    file_location = f"static/resumeResult/{filename}"
    if os.path.isfile(file_location):
        return FileResponse(path=file_location, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="File not found")



# 챗봇의 마지막 응답에서  이력서 데이터 뽑아오기
def extract_resume_data(email, room_id):
    resume_ready = False  # 기본값은 False로 설정
    try:
        chat_content = previous_system_content.get((email, room_id), "")
        lines = chat_content.split("\n")
        last_response_start_index = None

        # 마지막 챗봇 응답의 시작 지점 찾기
        for i, line in enumerate(reversed(lines)):
            if line.startswith("챗봇:"):
                last_response_start_index = len(lines) - 1 - i
                break

        # 전체 챗봇 응답 추출
        if last_response_start_index is not None:
            last_response = "\n".join(lines[last_response_start_index:])
            print("======================= 추출된 챗봇의 마지막 응답 =======================\n", last_response)

            # JSON 데이터 추출
            json_str_match = re.search(r'\{.*?\}', last_response, re.DOTALL)
            if json_str_match:
                json_str = json_str_match.group()
                print("======================= 추출된 JSON 데이터 =======================\n", json_str)
                resume_ready = True  # 이력서 데이터가 존재하므로 True로 설정
                return json.loads(json_str), resume_ready

    except json.JSONDecodeError:
        print("JSON 파싱 오류: 챗봇 응답에서 유효한 JSON 데이터를 추출할 수 없습니다.")
    except Exception as e:
        print(f"이력서 데이터 가져오기 실패: {e}")

    return None, resume_ready  # 예외 발생 시 None과 resume_ready의 현재값 반환



# 이력서 데이터 resumegenerator로 전달하는 함수
def send_resume_data(resume_data, email, roomId):

    print("!!!!!!!!!!!!!!!!!send_resume_data 함수 호출됨.........")

    # 이력서 컨텐츠 생성 및 파일 경로 반환
    resume_file_path = generate_resume_content(resume_data)

    # 파일 이름 추출 (예: 'your_resume_file.pdf')
    file_name = os.path.basename(resume_file_path)

    # 로컬에서 접근 가능한 URL 생성
    web_accessible_url = f"http://localhost:8000/static/resumeResult/{file_name}"

    print("=============================== 생성된 이력서 파일 경로 =============================== ", resume_file_path)
    print("================================== 웹 접근 가능 URL ================================== ", web_accessible_url)

    return web_accessible_url
