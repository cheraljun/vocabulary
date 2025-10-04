import os
import json
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from core.config import BASE_DIR, EXCEL_EXTENSIONS
from core.database import is_data_loaded, start_loading, unload_data
from core.loading import loading_state
from core.app_state import app_state
from core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def list_excel_files() -> List[Dict[str, Any]]:
    """列出 Excel 文件"""
    files: List[Dict[str, Any]] = []
    for name in os.listdir(BASE_DIR):
        path = os.path.join(BASE_DIR, name)
        if os.path.isfile(path):
            _, ext = os.path.splitext(name)
            if ext.lower() in EXCEL_EXTENSIONS:
                stat = os.stat(path)
                files.append({
                    "name": name,
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                })
    files.sort(key=lambda x: x["name"].lower())
    return files


@router.get("/api/excel/files")
async def api_excel_files():
    """获取 Excel 文件列表"""
    return {"files": list_excel_files()}


@router.get("/api/excel/status")
async def api_excel_status():
    """获取 Excel 加载状态"""
    actual_ready = is_data_loaded()
    state = loading_state.snapshot()
    state.update({
        "loaded": bool(actual_ready),
        "current_file": app_state.current_excel_file,
    })
    return state


@router.get("/api/excel/stream")
async def api_excel_stream(duration: float = 10.0, interval: float = 0.5):
    """SSE 流式返回加载状态"""
    max_seconds = max(1.0, min(duration, 60.0))
    interval = max(0.1, min(interval, 2.0))

    async def generate():
        last_sent: Dict[str, Any] = {}
        last_emit_ts = 0.0
        start_time = time.time()

        while True:
            snapshot = loading_state.snapshot()
            state = {
                "loaded": bool(is_data_loaded()),
                **snapshot,
            }

            changed = False
            if not last_sent:
                changed = True
            else:
                if state.get("timestamp") != last_sent.get("timestamp"):
                    changed = True
                elif int(state.get("percent", -1)) != int(last_sent.get("percent", -1)):
                    changed = True
                elif state.get("running") != last_sent.get("running"):
                    changed = True

            now = time.time()
            if changed or (now - last_emit_ts) >= max(2.0, interval * 3):
                last_sent = state
                last_emit_ts = now
                yield f"data: {json.dumps(state, ensure_ascii=False)}\n\n"

            if now - start_time >= max_seconds:
                break

            await asyncio.sleep(interval)

        closing_payload = {"event": "done", "timestamp": datetime.utcnow().isoformat()}
        yield f"data: {json.dumps(closing_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/api/excel/load")
async def api_excel_load(file: str):
    """加载 Excel 文件到数据库"""
    file_name = file.strip()
    files = list_excel_files()
    allowed = {f["name"] for f in files}
    if not file_name or file_name not in allowed:
        raise HTTPException(status_code=400, detail="invalid file")
    if loading_state.snapshot().get("running"):
        raise HTTPException(status_code=409, detail="loading in progress")
    
    logger.info(f"📥 接收Excel加载请求: {file_name}")
    file_path = os.path.join(BASE_DIR, file_name)
    success = start_loading(file_path)
    return {"started": success}


@router.post("/api/excel/unload")
async def api_excel_unload():
    """卸载数据库"""
    logger.info("📤 接收卸载数据库请求")
    unload_data()
    return {"ok": True}

