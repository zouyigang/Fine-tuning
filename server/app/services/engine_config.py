"""真实微调引擎：LLaMA-Factory 训练配置（YAML）与数据集注册（M1）。

纯函数为主，便于单测：
- resolve_model_path：把任务的 baseModel 解析为 MODELS_DIR 下的离线权重目录；
- register_dataset：把上传的数据集文件以标准格式注册进 LF 的 data/dataset_info.json，
  返回可在 YAML `dataset:` 引用的名字；M1 仅支持 alpaca / sharegpt / {prompt,response}；
- build_train_yaml：依据任务超参生成 LF 训练 YAML，落盘到 run 目录并返回 (yaml路径, 输出目录)。
"""
import json
import os
import re

import yaml

from app.core.config import settings

# 模型名 → LF 对话模板。M1 主用 Qwen3；其余给常见映射，未知回退 default。
_TEMPLATE_MAP = [
    (r"qwen3", "qwen3"),
    (r"qwen2", "qwen"),
    (r"qwen", "qwen"),
    (r"llama-?3", "llama3"),
    (r"llama", "llama2"),
    (r"glm|chatglm", "glm4"),
    (r"baichuan", "baichuan2"),
    (r"mistral", "mistral"),
]


def template_for(model_name: str) -> str:
    name = (model_name or "").lower()
    for pat, tpl in _TEMPLATE_MAP:
        if re.search(pat, name):
            return tpl
    return "default"


def resolve_model_path(base_model: str) -> str | None:
    """把 baseModel（展示名/目录名）解析为 MODELS_DIR 下的离线权重绝对路径。

    依次尝试：原名 / 规整名（空格→-）/ 去厂商前缀；命中含 config.json 的目录即返回。
    """
    root = os.path.abspath(settings.MODELS_DIR)
    if not base_model:
        return None
    # 剥掉展示后缀（如「Qwen3-0.6B（开源）」→「Qwen3-0.6B」），兼容全角/半角括号
    stripped = re.sub(r"[（(].*?[)）]\s*$", "", base_model).strip()
    bases = [base_model, stripped]
    candidates = []
    for b in bases:
        candidates += [b, b.replace(" ", "-"), b.replace(" ", "")]
    seen = []
    for c in candidates:
        if c and c not in seen:
            seen.append(c)
    for c in seen:
        p = os.path.join(root, c)
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "config.json")):
            return os.path.abspath(p)
    return None


def _detect_format(rows: list) -> str:
    """识别标准格式：alpaca / sharegpt / prompt_response。"""
    if not rows or not isinstance(rows[0], dict):
        return "unknown"
    keys = set(rows[0].keys())
    if {"conversations"} & keys or {"messages"} & keys:
        return "sharegpt"
    if {"instruction"} & keys or {"output"} & keys:
        return "alpaca"
    if {"prompt"} & keys and ({"response"} & keys or {"completion"} & keys):
        return "prompt_response"
    return "unknown"


def _load_rows(abspath: str) -> list:
    low = abspath.lower()
    if low.endswith(".jsonl"):
        rows = []
        with open(abspath, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s:
                    rows.append(json.loads(s))
        return rows
    with open(abspath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def register_dataset(name: str, abspath: str) -> str:
    """把标准格式数据集文件注册进 LF data/dataset_info.json，返回数据集名。

    M1 仅支持标准格式：
    - alpaca: {instruction,input,output}
    - sharegpt: {conversations:[...]}
    - prompt_response: {prompt,response} → 映射为 alpaca(instruction/output)
    非标准格式抛 ValueError（由调用方转成失败原因）。
    """
    rows = _load_rows(abspath)
    fmt = _detect_format(rows)
    if fmt == "unknown":
        raise ValueError("数据集非标准格式（仅支持 alpaca / sharegpt / {prompt,response}）")

    data_dir = _lf_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    info_path = os.path.join(data_dir, "dataset_info.json")
    info = {}
    if os.path.exists(info_path):
        with open(info_path, "r", encoding="utf-8") as f:
            info = json.load(f) or {}

    ds_key = re.sub(r"[^\w]", "_", name) or "ds"
    if fmt == "prompt_response":
        # 现转成 alpaca 落一个新文件，避免改写用户原文件
        conv_path = os.path.join(data_dir, f"{ds_key}_alpaca.jsonl")
        with open(conv_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({
                    "instruction": r.get("prompt", ""),
                    "input": "",
                    "output": r.get("response") or r.get("completion") or "",
                }, ensure_ascii=False) + "\n")
        info[ds_key] = {"file_name": os.path.abspath(conv_path), "formatting": "alpaca"}
    elif fmt == "sharegpt":
        info[ds_key] = {"file_name": os.path.abspath(abspath), "formatting": "sharegpt"}
    else:  # alpaca
        info[ds_key] = {"file_name": os.path.abspath(abspath), "formatting": "alpaca"}

    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    return ds_key


def ensure_demo_dataset() -> str:
    """生成并注册一个极小 alpaca demo（数据集缺失时回退用），返回数据集名。

    自管在 _lf_data 下，不依赖 LLaMA-Factory 自带数据，保证 M1 链路随时可跑通。
    """
    data_dir = _lf_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    demo_path = os.path.join(data_dir, "demo_alpaca.jsonl")
    if not os.path.exists(demo_path):
        samples = [
            {"instruction": "用一句话介绍人民警察的职责。", "input": "", "output": "人民警察依法维护社会治安秩序，保护公民合法权益。"},
            {"instruction": "什么是电信诈骗？", "input": "", "output": "电信诈骗是指通过电话、网络等手段虚构事实骗取财物的违法犯罪行为。"},
            {"instruction": "遇到诈骗应如何处理？", "input": "", "output": "应立即停止转账并拨打 110 或 96110 报警。"},
        ] * 8  # 复制到约 24 条，够小模型跑几十步
        with open(demo_path, "w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return register_dataset("demo", demo_path)


def _lf_data_dir() -> str:
    """LF 数据目录（dataset_info.json 所在）。放在 RUNS_DIR/_lf_data 下，自管。"""
    return os.path.abspath(os.path.join(settings.RUNS_DIR, "_lf_data"))


def build_train_yaml(*, task_id: int, model_path: str, dataset_key: str,
                     template: str, method: str, hp: dict) -> tuple[str, str]:
    """生成 LF 训练 YAML，落盘到 RUNS_DIR/{task_id}/，返回 (yaml路径, 输出目录)。"""
    hp = hp or {}
    run_dir = os.path.abspath(os.path.join(settings.RUNS_DIR, str(task_id)))
    output_dir = os.path.join(run_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    finetuning_type = "full" if method == "full" else "lora"
    batch = int(hp.get("batchSize") or 1)
    # 单卡小显存：每设备 batch 固定小，靠梯度累积凑有效 batch
    per_device = 1 if batch > 4 else batch
    grad_accum = max(1, batch // per_device)

    cfg = {
        "model_name_or_path": model_path,
        "trust_remote_code": True,
        "stage": "sft",
        "do_train": True,
        "finetuning_type": finetuning_type,
        "dataset": dataset_key,
        "dataset_dir": _lf_data_dir(),
        "template": template,
        "cutoff_len": int(hp.get("maxLen") or 1024),
        "overwrite_cache": True,
        "preprocessing_num_workers": 4,
        "output_dir": output_dir,
        "logging_steps": int(hp.get("loggingSteps") or 5),
        "save_steps": int(hp.get("saveSteps") or 1000),
        "plot_loss": True,
        "overwrite_output_dir": True,
        "per_device_train_batch_size": per_device,
        "gradient_accumulation_steps": grad_accum,
        "learning_rate": float(hp.get("lr") or 2e-5),
        "num_train_epochs": float(hp.get("epochs") or 3),
        "lr_scheduler_type": "cosine",
        "warmup_ratio": float(hp.get("warmup") or 0.1),
        "bf16": True,
        "report_to": "none",
    }
    if finetuning_type == "lora":
        cfg["lora_rank"] = int(hp.get("loraRank") or 8)
        cfg["lora_target"] = hp.get("loraTarget") or "all"
    if method == "qlora":
        cfg["quantization_bit"] = 4

    yaml_path = os.path.join(run_dir, "train.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    return yaml_path, output_dir
