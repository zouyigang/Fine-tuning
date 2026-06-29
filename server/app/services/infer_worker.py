"""推理 worker 子进程：独立加载一份模型权重，HTTP 暴露生成接口。

由 inference.py 管理器 spawn，一个 worker 常驻一份模型（base 或 base+LoRA adapter）：
- 加载完成后才开始监听端口 → 管理器轮询 /health 连得上即视为就绪；
- POST /generate {messages,maxTokens,temperature,topP,enableThinking} → {reply,elapsed}；
- 进程隔离：崩溃/OOM 不拖垮主 API，可被管理器单独 kill 回收显存。

刻意只用标准库 http.server，避免再起一套 uvicorn；单卡 dev 串行生成足够。
"""
import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _log(msg: str):
    print(f"[infer_worker] {msg}", flush=True)


def load_model(model_path: str, adapter_path: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    _log(f"加载分词器: {model_path}")
    tok = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tok.pad_token is None and tok.eos_token is not None:
        tok.pad_token = tok.eos_token
    _log(f"加载模型权重(dtype={dtype}) ...")
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=dtype, device_map="auto", trust_remote_code=True,
    )
    if adapter_path:
        from peft import PeftModel
        _log(f"挂载 LoRA adapter: {adapter_path}")
        model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()
    _log("模型就绪")
    return tok, model


def build_inputs(tok, messages, enable_thinking):
    """优先用 chat 模板；模型无模板时回退简单拼接。"""
    try:
        kwargs = dict(tokenize=False, add_generation_prompt=True)
        try:
            return tok.apply_chat_template(messages, enable_thinking=enable_thinking, **kwargs)
        except TypeError:
            # 老分词器不认 enable_thinking 参数
            return tok.apply_chat_template(messages, **kwargs)
    except Exception:
        parts = []
        for m in messages:
            role = {"user": "用户", "assistant": "助手", "system": "系统"}.get(m.get("role"), m.get("role"))
            parts.append(f"{role}：{m.get('content', '')}")
        parts.append("助手：")
        return "\n".join(parts)


def make_handler(tok, model):
    import torch

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # 静默默认访问日志
            pass

        def _send(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self._send(200, {"ok": True})
            else:
                self._send(404, {"ok": False})

        def do_POST(self):
            if self.path != "/generate":
                self._send(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            except Exception as e:
                self._send(400, {"error": f"bad request: {e}"})
                return
            try:
                reply, elapsed = self._generate(req)
                self._send(200, {"reply": reply, "elapsed": elapsed})
            except Exception as e:
                self._send(500, {"error": str(e)})

        def _generate(self, req):
            messages = req.get("messages") or []
            max_new = int(req.get("maxTokens") or 512)
            temperature = float(req.get("temperature", 0.7))
            top_p = float(req.get("topP", 0.9))
            enable_thinking = bool(req.get("enableThinking", False))

            text = build_inputs(tok, messages, enable_thinking)
            inputs = tok(text, return_tensors="pt").to(model.device)
            gen_kwargs = dict(max_new_tokens=max_new, pad_token_id=tok.pad_token_id)
            if temperature and temperature > 0:
                gen_kwargs.update(do_sample=True, temperature=temperature, top_p=top_p)
            else:
                gen_kwargs.update(do_sample=False)
            t0 = time.time()
            with torch.no_grad():
                out = model.generate(**inputs, **gen_kwargs)
            gen_ids = out[0][inputs["input_ids"].shape[1]:]
            reply = tok.decode(gen_ids, skip_special_tokens=True).strip()
            return reply, round(time.time() - t0, 2)

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default="")
    ap.add_argument("--port", type=int, required=True)
    args = ap.parse_args()
    try:
        tok, model = load_model(args.model, args.adapter)
    except Exception as e:
        _log(f"加载失败: {e}")
        sys.exit(2)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(tok, model))
    _log(f"开始监听 127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
