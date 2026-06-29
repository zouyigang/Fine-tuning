"""模型推理 / 对话对比接口，供评估模块「模型对话对比」页使用。

可手动选择基座模型或任意微调版本进行对话，并排比较微调前后效果。
推理在独立 worker 子进程中执行（见 services/inference.py），按需懒加载。
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok, err
from app.deps import get_current_user
from app.models.user import User
from app.services.inference import manager

router = APIRouter(prefix="/inference", tags=["inference"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatIn(BaseModel):
    modelId: str
    messages: list[ChatMessage]
    maxTokens: int = 512
    temperature: float = 0.7
    topP: float = 0.9
    enableThinking: bool = False


class UnloadIn(BaseModel):
    key: str


@router.get("/models")
def list_models(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """可选模型：离线基座 + 有真实产物的微调版本。"""
    return ok(manager.list_models(db))


@router.post("/chat")
def chat(body: ChatIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """对指定模型发起一轮对话（首次会懒加载该模型，耗时较长）。"""
    params = {"maxTokens": body.maxTokens, "temperature": body.temperature,
              "topP": body.topP, "enableThinking": body.enableThinking}
    msgs = [m.model_dump() for m in body.messages]
    try:
        result = manager.chat(db, body.modelId, msgs, params)
    except Exception as e:
        return err(f"推理失败：{e}", code=5001)
    return ok(result)


@router.get("/loaded")
def loaded(_: User = Depends(get_current_user)):
    """当前常驻的推理 worker（已占用显存）。"""
    return ok(manager.loaded())


@router.post("/unload")
def unload(body: UnloadIn, _: User = Depends(get_current_user)):
    """卸载一个已加载的模型，释放显存。"""
    okf = manager.unload(body.key)
    return ok({"unloaded": okf})
