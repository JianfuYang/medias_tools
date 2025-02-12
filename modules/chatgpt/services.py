import logging
from sqlalchemy.orm import Session
from .models import ChatMessage
from openai import OpenAI
from config.openai_config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS
import httpx

logger = logging.getLogger(__name__)

# 初始化OpenAI客户端
client = OpenAI(
    api_key=OPENAI_API_KEY,
    http_client=httpx.Client(
        proxies={
            "http://": "http://127.0.0.1:7890",
            "https://": "http://127.0.0.1:7890"
        }
    )
)

async def get_ai_response(message: str, session_id: int, db: Session) -> str:
    """获取AI响应"""
    try:
        # 获取历史消息作为上下文
        history = db.query(ChatMessage)\
            .filter(ChatMessage.session_id == session_id)\
            .order_by(ChatMessage.created_at.desc())\
            .limit(10)\
            .all()
            
        # 构建对话历史
        messages = []
        for msg in reversed(history):
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        messages.append({
            "role": "user",
            "content": message
        })
        
        # 调用OpenAI API
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"获取AI响应失败: {str(e)}")
        return f"抱歉,出现了一些问题: {str(e)}"