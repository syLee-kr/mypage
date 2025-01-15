import json
from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import RedirectResponse
from bson import ObjectId
from datetime import datetime

from app.config.ConnectionManager import ConnectionManager
from app.config.templates import templates
from app.database import chat_collection, db, messages_collection, chatroom_collection
from app.models.ChatMessage import ChatMessage
from app.models.ChatRoom import ChatRoom
from app.models.User import User
from app.service.UserService import UserService

router = APIRouter()
manager = ConnectionManager()

@router.get("")
async def get_chat_page(request: Request):
    session = request.session
    user_id = session.get("user_id")
    user_role = session.get("user_role", "user")  # 기본값 'user'

    if not user_id:
        return RedirectResponse(url="/login", status_code=302)

    if user_role == "admin":
        # 관리자는 모든 채팅방을 조회 (admin_id는 항상 "ARIES")
        chat_rooms_cursor = chatroom_collection.find({"admin_id": "ARIES"}).sort("updated_at", -1)
        chat_rooms = []
        async for room in chat_rooms_cursor:
            user = await UserService.find_user_by_user_id(room["user_id"])  # 문자열 user_id 사용
            chat_rooms.append({
                "chat_room_id": str(room["_id"]),
                "user_id": user.user_id if user else "Unknown",  # 문자열 user_id 사용
                "user_name": user.name if user else "Unknown",
                "last_message": room.get("last_message"),
                "updated_at": room.get("updated_at")
            })
    else:
        # 일반 유저는 자신의 채팅방만 조회 (admin_id는 항상 "ARIES")
        chat_rooms_cursor = chatroom_collection.find({"user_id": user_id, "admin_id": "ARIES"}).sort("updated_at", -1)
        chat_rooms = []
        async for room in chat_rooms_cursor:
            chat_rooms.append({
                "chat_room_id": str(room["_id"]),
                "user_id": room["user_id"],  # 문자열 user_id 사용
                "admin_id": room["admin_id"],
                "last_message": room.get("last_message"),
                "updated_at": room.get("updated_at")
            })

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "user_id": user_id,
        "user_role": user_role,
        "chat_rooms": chat_rooms,  # 템플릿에 채팅방 목록 전달
        "admin_id": "ARIES"  # 추가: 관리자 ID 문자열 직접 전달
    })

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket 연결 수락됨")

    # WebSocket 쿼리 파라미터에서 user_id와 user_role 추출
    query_params = websocket.query_params
    user_id = query_params.get("user_id")  # 유저의 user_id 문자열
    user_role = query_params.get("user_role", "user")  # 기본값 'user'

    print(f"수신된 user_id: {user_id}, user_role: {user_role}")

    user = await UserService.find_user_by_user_id(user_id)

    if not user:
        print(f"user_id: {user_id}로 유저를 찾을 수 없습니다.")
        await websocket.close(code=1008)  # 정책 위반 코드
        return
    else:
        print(f"찾은 유저: {user.dict()}")  # 디버깅용

    chat_room_id = None
    selected_user_id = None  # 관리자가 선택한 유저를 추적

    try:
        if user_role == "admin":
            # 관리자는 기본적으로 채팅방에 참여하지 않음
            pass
        else:
            # 일반 유저는 자신의 채팅방에 참여
            chat_room = await chatroom_collection.find_one({"user_id": user.user_id, "admin_id": "ARIES"})
            if not chat_room:
                print(f"유저 {user.user_id}에 대한 채팅방을 찾을 수 없어 새로 생성합니다.")
                new_chat_room = ChatRoom(
                    user_id=user.user_id,  # 문자열 user_id 사용
                    last_message=None,
                    updated_at=datetime.utcnow()
                )
                result = await chatroom_collection.insert_one(new_chat_room.dict(by_alias=True))
                chat_room_id = str(result.inserted_id)
                print(f"새 채팅방 생성됨, ID: {chat_room_id}")
            else:
                chat_room_id = str(chat_room["_id"])
                print(f"기존 채팅방 발견, ID: {chat_room_id}")

            # WebSocket 연결 관리
            await manager.connect(chat_room_id, websocket)
            print(f"유저 {user.user_id}가 채팅방 {chat_room_id}에 연결됨")

            # 이전 메시지 로드 및 전송
            previous_messages_cursor = messages_collection.find({"chat_room_id": chat_room_id}).sort("timestamp", 1)
            async for msg in previous_messages_cursor:
                chat_message = ChatMessage(**msg)
                if chat_message.sender_id == "ARIES":
                    sender_name = "admin"
                else:
                    sender_user = await UserService.find_user_by_user_id(chat_message.sender_id)
                    sender_name = sender_user.name if sender_user else "Unknown"

                serializable_msg = {
                    "id": str(chat_message.id),
                    "chat_room_id": chat_message.chat_room_id,  # 문자열 chat_room_id 사용
                    "sender_id": chat_message.sender_id,        # 문자열 user_id 사용
                    "receiver_id": chat_message.receiver_id,    # 문자열 user_id 사용
                    "message": chat_message.message,
                    "image": chat_message.image,
                    "timestamp": chat_message.timestamp.isoformat(),
                    "message_type": chat_message.message_type,
                    "sender_name": sender_name
                }
                await websocket.send_json(serializable_msg)

        # 메시지 수신 및 처리
        while True:
            data = await websocket.receive_json()
            message_type = data.get("message_type")
            content = data.get("content")
            receiver_id = data.get("receiver_id")  # 관리자일 경우 선택된 유저 ID

            if not message_type or not content:
                continue

            if message_type == "select_user" and user_role == "admin":
                # 관리자가 채팅방 선택
                selected_chat_room_id = content
                chat_room = await chatroom_collection.find_one({"_id": ObjectId(selected_chat_room_id), "admin_id": "ARIES"})
                if not chat_room:
                    await websocket.send_json({"type": "error", "message": "유효하지 않은 채팅방입니다."})
                    continue

                selected_user_id_raw = chat_room["user_id"]  # 문자열 또는 ObjectId
                if isinstance(selected_user_id_raw, ObjectId):
                    selected_user = await UserService.find_user_by_id(str(selected_user_id_raw))
                    selected_user_id = selected_user.user_id if selected_user else "Unknown"
                else:
                    selected_user_id = selected_user_id_raw  # 이미 문자열

                chat_room_id = selected_chat_room_id

                await manager.connect(chat_room_id, websocket)
                print(f"관리자가 채팅방 {chat_room_id}에 연결됨")

                # 이전 메시지 로드 및 전송
                previous_messages_cursor = messages_collection.find({"chat_room_id": chat_room_id}).sort("timestamp", 1)
                async for msg in previous_messages_cursor:
                    chat_message = ChatMessage(**msg)
                    if chat_message.sender_id == "ARIES":
                        sender_name = "admin"
                    else:
                        sender_user = await UserService.find_user_by_user_id(chat_message.sender_id)
                        sender_name = sender_user.name if sender_user else "Unknown"

                    serializable_msg = {
                        "id": str(chat_message.id),
                        "chat_room_id": chat_message.chat_room_id,  # 문자열 chat_room_id 사용
                        "sender_id": chat_message.sender_id,        # 문자열 user_id 사용
                        "receiver_id": chat_message.receiver_id,    # 문자열 user_id 사용
                        "message": chat_message.message,
                        "image": chat_message.image,
                        "timestamp": chat_message.timestamp.isoformat(),
                        "message_type": chat_message.message_type,
                        "sender_name": sender_name
                    }
                    await websocket.send_json(serializable_msg)

            elif message_type in ["text", "image"]:
                if user_role == "admin":
                    if not selected_user_id:
                        await websocket.send_json({"type": "error", "message": "채팅방을 먼저 선택하세요."})
                        continue
                    receiver_id_str = selected_user_id  # 문자열 user_id 사용
                else:
                    receiver_id_str = "ARIES"  # 문자열 "ARIES"

                # 채팅 메시지 생성 및 저장
                chat_message = ChatMessage(
                    chat_room_id=chat_room_id,  # 문자열 chat_room_id 사용
                    sender_id=user.user_id,      # 문자열 user_id 사용
                    receiver_id=receiver_id_str, # 문자열 user_id 사용
                    message=content if message_type == "text" else None,
                    image=content if message_type == "image" else None,
                    message_type=message_type
                )

                await messages_collection.insert_one(chat_message.dict(by_alias=True))
                await chatroom_collection.update_one(
                    {"_id": ObjectId(chat_room_id)},
                    {"$set": {"last_message": chat_message.message or "이미지 전송됨", "updated_at": datetime.utcnow()}}
                )

                # 발신자 이름 결정
                sender_name = "admin" if user_role == "admin" else user.name

                # 메시지 브로드캐스트
                serializable_message = {
                    "id": str(chat_message.id),
                    "chat_room_id": chat_message.chat_room_id,    # 문자열 chat_room_id 사용
                    "sender_id": chat_message.sender_id,          # 문자열 user_id 사용
                    "receiver_id": chat_message.receiver_id,      # 문자열 user_id 사용
                    "message": chat_message.message,
                    "image": chat_message.image,
                    "timestamp": chat_message.timestamp.isoformat(),
                    "message_type": chat_message.message_type,
                    "sender_name": sender_name
                }

                await manager.broadcast(chat_room_id, serializable_message)
                print(f"채팅방 {chat_room_id}에 메시지 브로드캐스트됨: {serializable_message}")

            else:
                print(f"알 수 없거나 권한 없는 메시지 타입: {message_type}")
                continue

    except WebSocketDisconnect:
        print(f"채팅방 {chat_room_id}에서 WebSocket 연결 해제됨")
        if chat_room_id:
            await manager.disconnect(chat_room_id, websocket)

    except Exception as e:
        print(f"WebSocket 오류: {e}")
        if chat_room_id:
            await manager.disconnect(chat_room_id, websocket)
        await websocket.close(code=1011)  # 서버 에러 코드

@router.get("/chatrooms", response_model=List[dict])
async def get_chatrooms(request: Request):
    session = request.session
    admin_id = session.get("user_id")
    user_role = session.get("user_role", "user")

    if user_role != "admin":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    chat_rooms_cursor = chatroom_collection.find({"admin_id": "ARIES"}).sort("updated_at", -1)
    chat_rooms = []
    async for room in chat_rooms_cursor:
        user = await UserService.find_user_by_user_id(room["user_id"])  # 문자열 user_id 사용
        chat_rooms.append({
            "chat_room_id": str(room["_id"]),
            "user_id": user.user_id if user else "Unknown",  # 문자열 user_id 사용
            "user_name": user.name if user else "Unknown",
            "last_message": room.get("last_message", "없음"),
            "updated_at": room.get("updated_at")
        })

    return chat_rooms

@router.get("/search_users", response_model=List[User])
async def search_users(request: Request, user_id: Optional[str] = None):
    session = request.session
    user_role = session.get("user_role")
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    query = {}
    if user_id:
        # 유저 ID를 기준으로 검색 (대소문자 구분 없이)
        query["user_id"] = {"$regex": user_id, "$options": "i"}

    users_cursor = await db["users"].find(query).to_list(length=50)
    users = [User(**user) for user in users_cursor]
    return users

@router.get("/chatroom/{user_id}", response_model=dict)
async def get_or_create_chatroom(user_id: str):
    user = await UserService.find_user_by_user_id(user_id)  # 문자열 user_id 사용
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")

    chat_room = await chatroom_collection.find_one({"user_id": user.user_id, "admin_id": "ARIES"})  # 문자열 user_id 사용
    if not chat_room:
        # 새 채팅방 생성
        new_chat_room = ChatRoom(
            user_id=user.user_id,  # 문자열 user_id 사용
            last_message=None,
            updated_at=datetime.utcnow()
        )
        result = await chatroom_collection.insert_one(new_chat_room.dict(by_alias=True))
        chat_room_id = str(result.inserted_id)
    else:
        chat_room_id = str(chat_room["_id"])

    return {
        "chat_room_id": chat_room_id,
        "user_id": user.user_id  # 문자열 user_id 사용
    }
