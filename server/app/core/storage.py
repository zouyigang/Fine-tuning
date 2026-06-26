"""本地文件存储服务：统一管理上传 / 导出文件的落盘、计数与下载。

目录结构（位于 settings.STORAGE_DIR 下，默认 server/storage/）：
  datasets/  数据集原始上传文件
  models/    模型导出产物
  reports/   评估报告 / 错误案例导出
存储目录已在 .gitignore 忽略，不入库。
"""
import os
import re
import uuid
from datetime import datetime

from fastapi.responses import FileResponse

from app.core.config import settings

# 子目录白名单，避免任意路径写入
SUBDIRS = ("datasets", "models", "reports")


def _root() -> str:
    return os.path.abspath(settings.STORAGE_DIR)


def ensure_dir(subdir: str) -> str:
    """确保子目录存在并返回其绝对路径。"""
    if subdir not in SUBDIRS:
        raise ValueError(f"非法存储子目录: {subdir}")
    path = os.path.join(_root(), subdir)
    os.makedirs(path, exist_ok=True)
    return path


def _safe_name(name: str) -> str:
    """清洗文件名，去掉路径分隔符等危险字符。"""
    name = os.path.basename(name or "file")
    return re.sub(r"[^\w.\-（）()一-龥]", "_", name) or "file"


def save_bytes(subdir: str, filename: str, data: bytes) -> tuple[str, str, int]:
    """把字节写入存储目录。返回 (磁盘存储名, 绝对路径, 字节数)。"""
    folder = ensure_dir(subdir)
    safe = _safe_name(filename)
    stored = f"{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:8]}_{safe}"
    abspath = os.path.join(folder, stored)
    with open(abspath, "wb") as f:
        f.write(data)
    return stored, abspath, len(data)


def reserve_path(subdir: str, filename: str) -> tuple[str, str]:
    """预留一个存储名+绝对路径（不写内容），供流式写入。返回 (磁盘存储名, 绝对路径)。"""
    folder = ensure_dir(subdir)
    safe = _safe_name(filename)
    stored = f"{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:8]}_{safe}"
    return stored, os.path.join(folder, stored)


def count_rows(abspath: str) -> int:
    """估算样本量：.json 解析条目数；其余按非空行计数。失败返回 0。"""
    try:
        if abspath.lower().endswith(".json"):
            import json
            with open(abspath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return len(data)
            if isinstance(data, dict):
                # 常见包裹结构 {"data": [...]}
                for v in data.values():
                    if isinstance(v, list):
                        return len(v)
                return 1
            return 1
        count = 0
        with open(abspath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
    except Exception:
        return 0


def validate_dataset(abspath: str) -> tuple[bool, str, int]:
    """按后缀校验数据集文件结构是否合法，返回 (是否合法, 提示信息, 样本量)。

    - .json  : 必须是 JSON 数组，或含数组值的对象（如 {"data": [...]}）；
    - .jsonl : 每个非空行必须是合法 JSON 对象；
    - .csv   : 至少含表头 + 1 行数据；
    - .txt   : 至少 1 行非空文本。
    解析失败/结构不符返回 (False, 原因, 0)，便于上传接口如实拒绝。
    """
    import json
    low = abspath.lower()
    try:
        if low.endswith(".json"):
            with open(abspath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                if not data:
                    return False, "JSON 数组为空，无有效样本", 0
                return True, "", len(data)
            if isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        return (True, "", len(v)) if v else (False, "数据数组为空，无有效样本", 0)
                return False, "JSON 对象中未找到样本数组（应为数组或 {\"data\": [...]}）", 0
            return False, "JSON 顶层必须是数组或对象", 0

        if low.endswith(".jsonl"):
            count = 0
            with open(abspath, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        json.loads(s)
                    except Exception:
                        return False, f"第 {i} 行不是合法 JSON", 0
                    count += 1
            return (True, "", count) if count else (False, "文件无有效样本行", 0)

        if low.endswith(".csv"):
            rows = 0
            with open(abspath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip():
                        rows += 1
            if rows < 2:
                return False, "CSV 至少需包含表头 + 1 行数据", 0
            return True, "", rows - 1  # 扣除表头

        # .txt 及其他：按非空行计数
        count = count_rows(abspath)
        return (True, "", count) if count else (False, "文件无有效内容", 0)
    except UnicodeDecodeError:
        return False, "文件编码非 UTF-8，无法解析", 0
    except json.JSONDecodeError as e:
        return False, f"JSON 解析失败：{e.msg}", 0
    except Exception as e:
        return False, f"文件解析失败：{e}", 0


def human_size(n: int) -> str:
    """字节数转可读字符串。"""
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}B"
        size /= 1024


def abspath_of(subdir: str, stored: str) -> str:
    """由子目录 + 存储名拼出绝对路径（带越界校验）。"""
    folder = ensure_dir(subdir)
    abspath = os.path.abspath(os.path.join(folder, os.path.basename(stored)))
    if not abspath.startswith(folder):
        raise ValueError("非法文件路径")
    return abspath


def file_response(abspath: str, download_name: str, media_type: str = "application/octet-stream") -> FileResponse:
    """构造下载响应（Starlette 自动处理中文文件名的 RFC5987 编码）。"""
    return FileResponse(abspath, filename=download_name, media_type=media_type)
