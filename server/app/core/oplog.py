"""操作日志记录工具：路径→操作语义映射 + 写库助手 + 自动记录中间件。"""
import json
import re
from datetime import datetime

from starlette.responses import Response

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models.oplog import OperationLog
from app.models.user import User

# (HTTP 方法, 路径匹配, 模块, 操作描述)；路径用正则全匹配
_RULES = [
    ("POST", r"^/api/task$", "微调任务", "创建微调任务"),
    ("PUT", r"^/api/task/\d+/status$", "微调任务", "变更任务状态"),
    ("POST", r"^/api/task/schedule$", "微调任务", "新建批量调度"),
    ("PUT", r"^/api/task/schedule/reorder$", "微调任务", "调整调度顺序"),
    ("DELETE", r"^/api/task/schedule/\d+$", "微调任务", "移除调度项"),
    ("POST", r"^/api/dataset$", "数据集管理", "创建数据集"),
    ("POST", r"^/api/dataset/upload$", "数据集管理", "上传数据集文件"),
    ("DELETE", r"^/api/dataset/\d+$", "数据集管理", "删除数据集"),
    ("POST", r"^/api/dataset/desensitize-rules$", "数据集管理", "新增脱敏规则"),
    ("PUT", r"^/api/dataset/desensitize-rules/\d+$", "数据集管理", "切换脱敏规则"),
    ("POST", r"^/api/dataset/desensitize/run$", "数据集管理", "执行数据脱敏"),
    ("POST", r"^/api/dataset/versions/\d+/rollback$", "数据集管理", "数据集版本回滚"),
    ("PUT", r"^/api/dataset/annotation-tasks/\d+/progress$", "数据集管理", "提交标注进度"),
    ("POST", r"^/api/dataset/permissions$", "数据集管理", "保存数据集权限"),
    ("PUT", r"^/api/model/\d+/status$", "模型版本", "变更模型状态"),
    ("POST", r"^/api/model/gray-releases$", "模型版本", "创建灰度发布"),
    ("PUT", r"^/api/model/gray-releases/\d+/traffic$", "模型版本", "调整灰度流量"),
    ("POST", r"^/api/model/\d+/release$", "模型版本", "模型全量上线"),
    ("POST", r"^/api/model/\d+/rollback$", "模型版本", "模型回滚"),
    ("POST", r"^/api/model/\d+/export$", "模型版本", "导出模型"),
    ("POST", r"^/api/model/\d+/deploy$", "模型版本", "部署模型"),
    ("POST", r"^/api/model/archive/clean$", "模型版本", "批量清理归档模型"),
    ("POST", r"^/api/model/\d+/clean$", "模型版本", "清理归档模型"),
    ("POST", r"^/api/model/\d+/restore$", "模型版本", "恢复归档模型"),
    ("POST", r"^/api/evaluation/reports$", "模型效果评估", "生成评估报告"),
    ("POST", r"^/api/evaluation/review-results$", "模型效果评估", "提交复核结果"),
    ("POST", r"^/api/config/base-models$", "微调配置", "保存基础模型"),
    ("POST", r"^/api/config/hyper-templates$", "微调配置", "保存超参模板"),
    ("DELETE", r"^/api/config/hyper-templates/\d+$", "微调配置", "删除超参模板"),
    ("POST", r"^/api/config/role-permissions$", "微调配置", "保存角色权限"),
    ("POST", r"^/api/config/resource-quotas$", "微调配置", "保存资源配额"),
    ("POST", r"^/api/config/autotune$", "微调配置", "保存自动调优配置"),
    ("POST", r"^/api/user$", "用户管理", "创建用户"),
    ("PUT", r"^/api/user/\d+/status$", "用户管理", "启用/禁用用户"),
    ("POST", r"^/api/user/\d+/reset-password$", "用户管理", "重置密码"),
    ("PUT", r"^/api/user/\d+$", "用户管理", "编辑用户"),
    ("DELETE", r"^/api/user/\d+$", "用户管理", "删除用户"),
    ("POST", r"^/api/auth/logout$", "系统", "退出登录"),
]


def describe(method: str, path: str):
    """返回 (module, action)；命中规则用语义描述，否则回退为通用描述。"""
    m = method.upper()
    for rm, rp, module, action in _RULES:
        if rm == m and re.match(rp, path):
            return module, action
    return "其他", f"{m} {path}"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _username_from_header(authorization: str | None, db) -> tuple[str | None, str | None]:
    """从 Authorization 头解析当前用户 (username, realName)。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None, None
    token = authorization.split(" ", 1)[1].strip()
    username = decode_access_token(token)
    if not username:
        return None, None
    u = db.query(User).filter(User.username == username).first()
    return username, (u.real_name if u else None)


def record(db, *, username, real_name, module, action, method, path, ip, status, detail=""):
    """写一条操作日志（独立提交，失败静默，避免影响主流程）。"""
    try:
        db.add(OperationLog(
            username=username or "-", realName=real_name or "-",
            module=module, action=action, method=method, path=path,
            ip=ip or "-", status=status, detail=detail or "", time=_now(),
        ))
        db.commit()
    except Exception:
        db.rollback()


# 仅记录这些写操作（GET 只读不记）
_LOG_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


async def operation_log_middleware(request, call_next):
    """自动记录所有写操作（登录单独在 auth 路由里记，因为登录前无 token）。

    本平台业务错误（含 RBAC 拒绝、参数校验失败等）统一以 HTTP 200 + 响应体
    `{code!=0}` 返回，故仅看 HTTP 状态码无法区分成败。这里读取响应体的 envelope
    `code` 判定结果：被拒绝/失败的写操作会如实记为「失败」，保证审计可信。
    """
    response = await call_next(request)

    path = request.url.path
    method = request.method.upper()
    if not (path.startswith("/api") and method in _LOG_METHODS and path != "/api/auth/login"):
        return response

    # body_iterator 只能消费一次，读出后需用相同内容重建响应
    body = b""
    async for chunk in response.body_iterator:
        body += chunk
    new_response = Response(content=body, status_code=response.status_code,
                            headers=dict(response.headers), media_type=response.media_type)

    status = "成功" if response.status_code < 400 else "失败"
    detail = ""
    try:
        payload = json.loads(body.decode("utf-8"))
        code = payload.get("code")
        if code is not None and code != 0:
            status = "失败"
            detail = str(payload.get("message") or "")[:200]
    except Exception:
        pass

    db = SessionLocal()
    try:
        username, real_name = _username_from_header(request.headers.get("authorization"), db)
        module, action = describe(method, path)
        ip = request.client.host if request.client else "-"
        record(db, username=username, real_name=real_name, module=module,
               action=action, method=method, path=path, ip=ip, status=status, detail=detail)
    finally:
        db.close()
    return new_response
