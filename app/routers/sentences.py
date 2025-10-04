import os
from fastapi import APIRouter, HTTPException, Request

from core.config import DATA_SENTENCE_DIR, TXT_EXTENSIONS
from core.utils import natural_sort_key
from core.logger import get_logger
from core.ip_tracker import track_ip

router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/txt/list")
async def api_txt_list():
    """获取情境句文件列表"""
    files = []
    if not os.path.isdir(DATA_SENTENCE_DIR):
        return {"files": files}
    for name in os.listdir(DATA_SENTENCE_DIR):
        path = os.path.join(DATA_SENTENCE_DIR, name)
        if os.path.isfile(path):
            _, ext = os.path.splitext(name)
            if ext.lower() in TXT_EXTENSIONS:
                files.append(name)
    files.sort(key=natural_sort_key)
    return {"files": files}


@router.get("/api/txt/content")
async def api_txt_content(name: str, request: Request):
    """读取情境句文件内容"""
    if not name:
        raise HTTPException(status_code=400, detail="missing name")
    safe_name = os.path.basename(name)
    _, ext = os.path.splitext(safe_name)
    if ext.lower() not in TXT_EXTENSIONS:
        raise HTTPException(status_code=400, detail="invalid file type")
    base = DATA_SENTENCE_DIR if os.path.isdir(DATA_SENTENCE_DIR) else os.path.dirname(__file__)
    file_path = os.path.join(base, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="file not found")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 记录打开句子
        try:
            await track_ip(request, "打开句子", {"filename": safe_name})
        except Exception as e:
            logger.warning(f"记录打开句子失败: {e}")
        
        return {"name": safe_name, "content": content}
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="gb18030", errors="ignore") as f:
            content = f.read()
        
        # 记录打开句子
        try:
            await track_ip(request, "打开句子", {"filename": safe_name})
        except Exception as e:
            logger.warning(f"记录打开句子失败: {e}")
        
        return {"name": safe_name, "content": content}

