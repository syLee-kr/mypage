# app/routes/chat_routes.py

from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import RedirectResponse
from bson import ObjectId
from datetime import datetime

from app.config.templates import templates
from app.database import chat_collection, db
from app.models.ChatMessage import ChatMessage
from app.models.ChatRoom import ChatRoom
from app.models.User import User
from app.service.ChatService import ConnectionManager
from app.service.UserService import UserService  # UserService 임포트

router = APIRouter()
manager = ConnectionManager()

@router.get("")
async def get_chat_page(request: Request):
    session = request.session
    user_id = session.get("user_id")
    user_role = session.get("user_role", "user")  # 기본값 'user'

    if not user_id:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "user_id": user_id,
        "user_role": user_role
    })

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted")

    # 쿼리 파라미터에서 user_id와 user_role 추출
    query_params = websocket.query_params
    user_id = query_params.get("user_id")
    user_role = query_params.get("user_role", "user")  # 기본값 'user'

    print(f"User ID: {user_id}, User Role: {user_role}")

    if not user_id or not user_role:
        await websocket.close(code=1008)  # 정책 위반 코드
        return

    chat_room_id = ""

    if user_role == "admin":
        # 관리자는 여러 채팅방을 처리할 수 있으므로 연결 후 유저 ID를 지정해야 함
        pass
    else:
        # 사용자의 경우 관리자와의 채팅방을 찾거나 생성
        chat_room = await chat_collection.chatrooms.find_one({"user_id": ObjectId(user_id), "admin_id": {"$exists": True}})
        if not chat_room:
            # 새로운 채팅방 생성
            new_chat_room = ChatRoom(
                user_id=ObjectId(user_id),
                admin_id=None,  # 추후 관리자를 할당
                last_message=None,
                updated_at=datetime.utcnow()
            )
            result = await chat_collection.insert_one(new_chat_room.dict(by_alias=True))
            chat_room_id = str(result.inserted_id)
            print(f"New chat room created with ID: {chat_room_id}")
        else:
            chat_room_id = str(chat_room["_id"])

    try:
        await manager.connect(chat_room_id, websocket)
        print(f"User {user_id} connected to chat room {chat_room_id}")
        while True:
            data = await websocket.receive_json()
            message_type = data.get("message_type", "text")
            content = data.get("content")

            if not content:
                continue  # 빈 메시지는 무시

            if user_role == "admin" and message_type == "select_user":
                # 관리자가 유저를 선택하는 경우
                target_user_id = content
                if not target_user_id:
                    await websocket.send_json({"type": "error", "message": "유효하지 않은 유저 ID입니다."})
                    continue

                # 유저 ID로 유저 정보 조회
                user = await UserService.find_user_by_id(target_user_id)
                if not user:
                    await websocket.send_json({"type": "error", "message": "유저를 찾을 수 없습니다."})
                    continue

                # 유저와의 채팅방 찾기 또는 생성
                chat_room = await chat_collection.chatrooms.find_one({
                    "user_id": ObjectId(user.id),
                    "admin_id": ObjectId(user_id)
                })
                if not chat_room:
                    # 새로운 채팅방 생성
                    new_chat_room = ChatRoom(
                        user_id=ObjectId(user.id),
                        admin_id=ObjectId(user_id),
                        last_message=None,
                        updated_at=datetime.utcnow()
                    )
                    result = await chat_collection.insert_one(new_chat_room.dict(by_alias=True))
                    chat_room_id = str(result.inserted_id)
                    print(f"New chat room created with ID: {chat_room_id}")
                else:
                    chat_room_id = str(chat_room["_id"])
                    print(f"Admin selected existing chat room ID: {chat_room_id}")

                # 기존 연결 해제 후 새로운 채팅방으로 연결
                await manager.disconnect(chat_room_id, websocket)
                await manager.connect(chat_room_id, websocket)
                await websocket.send_json({"type": "info", "message": f"Connected to chat room {chat_room_id}"})
                continue

            # ChatMessage 인스턴스 생성
            chat_message = ChatMessage(
                sender_id=user_id,
                receiver_id="admin_id" if user_role == "user" else "user_id",
                message=content if message_type == "text" else None,
                image=content if message_type == "image" else None,
                message_type=message_type
            )

            message_doc = chat_message.dict(by_alias=True)
            message_doc["timestamp"] = datetime.utcnow()
            result = await chat_collection.chatmessages.insert_one(message_doc)
            chat_message.id = result.inserted_id

            # ChatRoom 업데이트
            await chat_collection.update_one(
                {"_id": ObjectId(chat_room_id)},
                {"$set": {"last_message": message_doc, "updated_at": datetime.utcnow()}}
            )

            # 채팅방의 모든 연결에 메시지 방송
            await manager.broadcast(chat_room_id, {
                "sender_id": chat_message.sender_id,
                "message": chat_message.message,
                "image": chat_message.image,
                "message_type": chat_message.message_type,
                "timestamp": chat_message.timestamp.isoformat()
            })

    except WebSocketDisconnect:
        manager.disconnect(chat_room_id, websocket)
        print(f"WebSocket disconnected: User {user_id} from chat room {chat_room_id}")
    except Exception as e:
        manager.disconnect(chat_room_id, websocket)
        print(f"WebSocket error: {e}")
        await websocket.close()

@router.get("/chatrooms", response_model=List[User])
async def get_chatrooms(request: Request):
    session = request.session
    admin_id = session.get("user_id")
    user_role = session.get("user_role")

    if user_role != "admin":
        # 일반 사용자는 자신의 채팅방만 조회
        chat_rooms_cursor = chat_collection.chatrooms.find({"user_id": ObjectId(admin_id), "admin_id": {"$exists": True}})
    else:
        # 관리자는 자신과 연결된 모든 채팅방 조회, 최신순 정렬
        chat_rooms_cursor = chat_collection.chatrooms.find({"admin_id": ObjectId(admin_id)}).sort("updated_at", -1)

    user_ids = []
    async for room in chat_rooms_cursor:
        user_ids.append(ObjectId(room["user_id"]))

    # 중복 제거
    user_ids = list(set(user_ids))

    # 유저 정보 조회
    users_cursor = await db["users"].find({"_id": {"$in": user_ids}}).to_list(length=50)
    users = [User(**user) for user in users_cursor]
    return users

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

