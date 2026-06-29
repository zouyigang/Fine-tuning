"""推理管理器：在主进程内 spawn / 追踪推理 worker 子进程，对外提供模型列表与对话。

设计要点（与训练引擎 engine.py 同构）：
- 每份模型（base 或 base+adapter）对应一个常驻 worker 子进程，崩溃可单独回收；
- 按需懒加载：首次对某模型对话时才 spawn，加载完（/health 通）后转发请求；
- LRU 上限 MAX_INFER_WORKERS，超额卸载最久未用的 worker 释放显存；
- 模型来源：MODELS_DIR 下的离线基座 + model_version 真实产物（merged 优先，否则 base+adapter）。
"""
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime

from sqlalchemy import select

from app.core.config import settings
from app.models.model_version import ModelVersion
from app.models.task import TrainTask, TaskArtifact
from app.services import engine_config as ec

_WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), "infer_worker.py")


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _Worker:
    def __init__(self, key, label, model_path, adapter_path, proc, port):
        self.key = key
        self.label = label
        self.model_path = model_path
        self.adapter_path = adapter_path
        self.proc = proc
        self.port = port
        self.last_used = time.time()
        self.loaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class InferenceManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._workers: dict[str, _Worker] = {}

    # ---- GPU 设备 ----
    def _gpu_count(self) -> int:
        try:
            from app.services.engine import manager as train_manager
            return train_manager.gpu_count()
        except Exception:
            return 1

    # ---- 模型来源解析 ----
    def list_models(self, db) -> list[dict]:
        """可选模型 = MODELS_DIR 下离线基座 + 有真实产物的微调版本。"""
        out = []
        root = os.path.abspath(settings.MODELS_DIR)
        if os.path.isdir(root):
            for name in sorted(os.listdir(root)):
                p = os.path.join(root, name)
                if os.path.isdir(p) and os.path.exists(os.path.join(p, "config.json")):
                    out.append({"id": f"base:{name}", "label": f"{name}（基座）",
                                "kind": "base", "modelType": "", "base": name})
        # 微调版本：有 task 产物（merged / adapter）才可加载
        for mv in db.scalars(select(ModelVersion).order_by(ModelVersion.id.desc())).all():
            spec = self._resolve_version(db, mv)
            if spec is None:
                continue
            base = spec[2]
            out.append({
                "id": f"mv:{mv.id}", "kind": "finetuned",
                "label": f"{mv.name} {mv.version or ''}".strip() + "（微调）",
                "modelType": mv.modelType or "", "base": base,
                "f1": mv.f1, "status": mv.status,
            })
        return out

    def _resolve_version(self, db, mv: ModelVersion):
        """微调版本 → (model_path, adapter_path, base_name)；无可用权重返回 None。

        merged 产物可直接当完整权重加载；否则 base 权重 + adapter 目录。
        """
        if not mv or not mv.task_id:
            return None
        t = db.get(TrainTask, mv.task_id)
        if not t:
            return None
        arts = db.scalars(select(TaskArtifact).where(TaskArtifact.task_id == t.id)).all()
        merged = next((a for a in arts if a.kind == "merged" and a.path and os.path.isdir(a.path)), None)
        if merged:
            return merged.path, "", (t.baseModel or "")
        adapter = next((a for a in arts if a.kind == "adapter" and a.path and os.path.isdir(a.path)), None)
        if adapter and os.path.exists(os.path.join(adapter.path, "adapter_config.json")):
            base_path = t.baseModelPath or ec.resolve_model_path(t.baseModel)
            if base_path and os.path.isdir(base_path):
                return base_path, adapter.path, (t.baseModel or "")
        return None

    def resolve(self, db, model_id: str):
        """前端 model_id → (key, label, model_path, adapter_path)。"""
        if model_id.startswith("base:"):
            name = model_id[len("base:"):]
            path = ec.resolve_model_path(name)
            if not path:
                raise ValueError(f"未找到基座模型「{name}」的离线权重")
            return f"base:{name}", f"{name}（基座）", path, ""
        if model_id.startswith("mv:"):
            mv = db.get(ModelVersion, int(model_id[len("mv:"):]))
            if not mv:
                raise ValueError("模型版本不存在")
            spec = self._resolve_version(db, mv)
            if spec is None:
                raise ValueError(f"模型版本「{mv.name} {mv.version}」没有可加载的权重产物")
            mp, ap, _base = spec
            return model_id, f"{mv.name} {mv.version or ''}".strip() + "（微调）", mp, ap
        raise ValueError(f"无法识别的模型标识: {model_id}")

    # ---- worker 生命周期 ----
    def _alive(self, w: _Worker) -> bool:
        return w.proc.poll() is None

    def _ensure_worker(self, key, label, model_path, adapter_path) -> _Worker:
        with self._lock:
            w = self._workers.get(key)
            if w and self._alive(w):
                w.last_used = time.time()
                return w
            if w:  # 已死，清理
                self._workers.pop(key, None)
            self._evict_if_needed()
            w = self._spawn(key, label, model_path, adapter_path)
            self._workers[key] = w
        self._wait_ready(w)
        return w

    def _evict_if_needed(self):
        """持锁调用：超过上限时卸载最久未用的 worker。"""
        while len(self._workers) >= max(1, settings.MAX_INFER_WORKERS):
            oldest = min(self._workers.values(), key=lambda x: x.last_used)
            self._kill(oldest)
            self._workers.pop(oldest.key, None)

    def _spawn(self, key, label, model_path, adapter_path) -> _Worker:
        port = _free_port()
        device = (len([w for w in self._workers.values()]) % max(1, self._gpu_count()))
        cmd = [sys.executable, _WORKER_SCRIPT, "--model", model_path, "--port", str(port)]
        if adapter_path:
            cmd += ["--adapter", adapter_path]
        env = dict(os.environ)
        env["CUDA_VISIBLE_DEVICES"] = str(device)
        env["PYTHONUTF8"] = "1"
        proc = subprocess.Popen(
            cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="ignore", bufsize=1,
        )
        w = _Worker(key, label, model_path, adapter_path, proc, port)
        threading.Thread(target=self._pump, args=(w,), daemon=True).start()
        return w

    def _pump(self, w: _Worker):
        """读 worker 输出，留尾部若干行用于诊断加载失败原因。"""
        w.log_tail = []
        try:
            for line in w.proc.stdout:
                line = (line or "").rstrip()
                if line:
                    w.log_tail.append(line)
                    del w.log_tail[:-30]
        except Exception:
            pass

    def _wait_ready(self, w: _Worker):
        deadline = time.time() + settings.INFER_LOAD_TIMEOUT
        url = f"http://127.0.0.1:{w.port}/health"
        while time.time() < deadline:
            if not self._alive(w):
                tail = "\n".join(getattr(w, "log_tail", [])[-8:])
                raise RuntimeError(f"推理进程加载失败：\n{tail}")
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    if r.status == 200:
                        return
            except Exception:
                time.sleep(1)
        raise RuntimeError(f"推理模型加载超时（>{settings.INFER_LOAD_TIMEOUT}s）")

    def _kill(self, w: _Worker):
        try:
            w.proc.terminate()
        except Exception:
            pass

    # ---- 对外 ----
    def chat(self, db, model_id: str, messages: list, params: dict) -> dict:
        key, label, model_path, adapter_path = self.resolve(db, model_id)
        w = self._ensure_worker(key, label, model_path, adapter_path)
        body = {"messages": messages, **params}
        data = json_post(f"http://127.0.0.1:{w.port}/generate", body,
                         timeout=max(60, int(params.get("maxTokens", 512)) // 2 + 120))
        if "error" in data:
            raise RuntimeError(data["error"])
        w.last_used = time.time()
        return {"reply": data.get("reply", ""), "elapsed": data.get("elapsed"), "model": label}

    def loaded(self) -> list[dict]:
        with self._lock:
            return [{"key": w.key, "label": w.label, "port": w.port,
                     "loadedAt": w.loaded_at, "alive": self._alive(w)}
                    for w in self._workers.values()]

    def unload(self, key: str) -> bool:
        with self._lock:
            w = self._workers.pop(key, None)
        if not w:
            return False
        self._kill(w)
        return True

    def shutdown_all(self):
        with self._lock:
            ws = list(self._workers.values())
            self._workers.clear()
        for w in ws:
            self._kill(w)


def json_post(url: str, payload: dict, timeout: int = 300) -> dict:
    import json
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


manager = InferenceManager()
