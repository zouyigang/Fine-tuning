"""应用配置：从 .env 读取，pydantic-settings 校验。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "sqlite:///./finetune.db"
    JWT_SECRET: str = "dev-secret"
    JWT_EXPIRE_MINUTES: int = 720
    CORS_ORIGINS: str = "http://localhost:5180"
    AUTO_SEED: bool = True
    # 文件存储根目录（数据集上传 / 模型导出 / 报告导出落盘）
    STORAGE_DIR: str = "./storage"

    # ---- 真实微调引擎（M1）----
    # sim=模拟训练(造假曲线, 演示任务常驻)；real=调 LLaMA-Factory 真实训练
    ENGINE_MODE: str = "sim"
    # 离线基础模型根目录（HF 权重），model_name_or_path = MODELS_DIR/<模型名>
    MODELS_DIR: str = "./models"
    # 每个训练任务的运行目录根（生成 YAML / LF 输出 / trainer_log.jsonl）
    RUNS_DIR: str = "./storage/runs"
    # llamafactory-cli 调用方式：默认用当前解释器 -m llamafactory.cli
    LLAMAFACTORY_BIN: str = ""
    # 最大并发训练数（一般 = 可用 GPU 数）
    MAX_CONCURRENT_TRAINS: int = 1

    # ---- 推理 / 对话对比（评估模块）----
    # 同时常驻的推理 worker 上限（每个占一份模型显存），超出按 LRU 卸载
    MAX_INFER_WORKERS: int = 2
    # 等待 worker 加载完模型（连得上 /health）的超时秒数
    INFER_LOAD_TIMEOUT: int = 600

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
