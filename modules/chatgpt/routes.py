from fastapi import APIRouter, Request, Depends, HTTPException, WebSocket
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .models import ChatSession, ChatMessage
from .services import get_ai_response
from core.database import get_db
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")

@router.get("/")
async def chatgpt_index(request: Request, db: Session = Depends(get_db)):
    """ChatGPT助手首页"""
    try:
        # 获取最近的会话
        recent_sessions = db.query(ChatSession)\
            .order_by(ChatSession.updated_at.desc())\
            .limit(10)\
            .all()
            
        return templates.TemplateResponse(
            "tools/chatgpt/index.html",
            {
                "request": request,
                "current_tool": "/tools/chatgpt",
                "recent_sessions": recent_sessions,
                "year": datetime.now().year
            }
        )
    except Exception as e:
        logger.error(f"访问ChatGPT助手失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: int, db: Session = Depends(get_db)):
    """WebSocket处理实时对话"""
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            
            # 保存用户消息
            chat_message = ChatMessage(
                session_id=session_id,
                role="user",
                content=message
            )
            db.add(chat_message)
            db.commit()
            
            # 获取AI响应
            ai_response = await get_ai_response(message, session_id, db)
            
            # 保存AI响应
            ai_message = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=ai_response
            )
            db.add(ai_message)
            db.commit()
            
            # 发送响应
            await websocket.send_text(ai_response)
            
    except Exception as e:
        logger.error(f"WebSocket错误: {str(e)}")
        await websocket.close()

@router.post("/sessions")
async def create_session(db: Session = Depends(get_db)):
    """创建新的会话"""
    try:
        # 创建新会话
        session = ChatSession(
            title=f"新会话 {datetime.now().strftime('%m-%d %H:%M')}"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return {
            "session_id": session.id,
            "title": session.title
        }
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    """获取会话历史消息"""
    try:
        messages = db.query(ChatMessage)\
            .filter(ChatMessage.session_id == session_id)\
            .order_by(ChatMessage.created_at.asc())\
            .all()
            
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            for msg in messages
        ]
    except Exception as e:
        logger.error(f"获取会话消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_sessions(db: Session = Depends(get_db)):
    """获取所有会话列表"""
    try:
        sessions = db.query(ChatSession)\
            .order_by(ChatSession.updated_at.desc())\
            .all()
            
        return [
            {
                "id": session.id,
                "title": session.title,
                "updated_at": session.updated_at.strftime('%m-%d %H:%M')
            }
            for session in sessions
        ]
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db)):
    """删除会话"""
    try:
        # 删除会话相关的所有消息
        db.query(ChatMessage)\
            .filter(ChatMessage.session_id == session_id)\
            .delete()
            
        # 删除会话
        db.query(ChatSession)\
            .filter(ChatSession.id == session_id)\
            .delete()
            
        db.commit()
        return {"message": "会话已删除"}
        
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 