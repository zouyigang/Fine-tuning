"""FastAPI 应用入口。

启动：  uvicorn app.main:app --reload --port 8000
文档：  http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import init_db
from app.core.response import ok, err
from app.deps import enforce_rbac
from app.routers import dataset, auth, task, evaluation, model, config, dashboard, log, user, screen
from app.core.oplog import operation_log_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 建表（开发期 create_all；生产用 Alembic）
    init_db()
    # 账号与评估参考数据始终幂等保证（与演示业务种子解耦）：
    # 即使 AUTO_SEED=false（清库只留真实数据），登录账号与评估三页参考数据仍存在。
    from scripts.seed import (
        ensure_users, ensure_eval_aggregates, ensure_convert_rules,
        ensure_dataset_types, ensure_convert_rule_links, ensure_dataset_stage,
        ensure_path_pipeline,
    )
    ensure_users()
    ensure_eval_aggregates()
    ensure_dataset_types()      # 须在 convert_rules 之前：新库灌规则时解析类型 FK
    ensure_convert_rules()
    ensure_convert_rule_links()  # 既有库补链：旧规则按 typeMatch 关联到 dataset_type
    ensure_path_pipeline()       # 幂等补齐「路径分析」类型 + 转换规则（既有库不会被表空种子覆盖）
    ensure_dataset_stage()       # 流水线 P1：回填旧数据 stage / 脱敏规则 maskType
    # 仅 AUTO_SEED 时灌入演示业务数据（数据集/任务/模型/评估记录等，库空才灌）
    if settings.AUTO_SEED:
        from scripts.seed import seed_if_empty
        seed_if_empty()
    # 训练调度：real=真实 LLaMA-Factory 引擎；sim=模拟训练调度器（P4）
    if settings.ENGINE_MODE == "real":
        from app.services.engine import start_engine
        start_engine()
    else:
        from app.services.trainer import start_scheduler
        start_scheduler()
    yield


app = FastAPI(title="模型微调通用平台 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 操作日志中间件：自动记录所有写操作（在 CORS 之后注册，确保最先进入、最后离开）
app.middleware("http")(operation_log_middleware)

# 鉴权路由：公开（登录无需 token）
app.include_router(auth.router, prefix="/api")

# 业务路由统一挂在 /api 下，注入 enforce_rbac 依赖：
# 内部先做登录校验（依赖 get_current_user），再按角色权限拦截高风险写操作。
app.include_router(dataset.router, prefix="/api", dependencies=[Depends(enforce_rbac)])
app.include_router(task.router, prefix="/api", dependencies=[Depends(enforce_rbac)])
app.include_router(evaluation.router, prefix="/api", dependencies=[Depends(enforce_rbac)])
app.include_router(model.router, prefix="/api", dependencies=[Depends(enforce_rbac)])
app.include_router(config.router, prefix="/api", dependencies=[Depends(enforce_rbac)])
app.include_router(dashboard.router, prefix="/api", dependencies=[Depends(enforce_rbac)])
app.include_router(screen.router, prefix="/api", dependencies=[Depends(enforce_rbac)])
app.include_router(log.router, prefix="/api", dependencies=[Depends(enforce_rbac)])
app.include_router(user.router, prefix="/api", dependencies=[Depends(enforce_rbac)])


@app.get("/api/health")
def health():
    return ok({"status": "up"})


# 统一异常 -> {code,data,message}，返回 HTTP 200 以便前端拦截器按 code 处理
@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=200, content=err(str(exc.detail), code=exc.status_code))


@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=200, content=err("参数校验失败", code=4220))
