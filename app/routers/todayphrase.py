import os
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from core.config import TODAY_PHRASE_DIR, IMAGE_EXTENSIONS

router = APIRouter()


def _maybe_generate_webp_for(src_path: str) -> Optional[str]:
    """尝试生成 WEBP 并返回文件名"""
    try:
        _, src_ext = os.path.splitext(src_path)
        src_ext_lower = src_ext.lower()
        if src_ext_lower == ".webp":
            return os.path.basename(src_path)

        webp_path = os.path.splitext(src_path)[0] + ".webp"
        
        if os.path.exists(webp_path):
            try:
                if os.path.getmtime(webp_path) >= os.path.getmtime(src_path) and os.path.getsize(webp_path) > 0:
                    try:
                        os.remove(src_path)
                    except Exception:
                        pass
                return os.path.basename(webp_path)
            except Exception:
                return os.path.basename(webp_path)

        try:
            from PIL import Image
        except Exception:
            return os.path.basename(src_path)

        try:
            with Image.open(src_path) as im:
                im.save(webp_path, format="WEBP", quality=75, method=6)
            try:
                os.remove(src_path)
            except Exception:
                pass
            return os.path.basename(webp_path)
        except Exception:
            return os.path.basename(src_path)
    except Exception:
        return None


def _find_todayphrase_file() -> Optional[str]:
    """查找今日一签图片文件"""
    try:
        if not os.path.isdir(TODAY_PHRASE_DIR):
            return None
        for name in os.listdir(TODAY_PHRASE_DIR):
            path = os.path.join(TODAY_PHRASE_DIR, name)
            if not os.path.isfile(path):
                continue
            _, ext = os.path.splitext(name)
            if ext.lower() in IMAGE_EXTENSIONS:
                preferred = _maybe_generate_webp_for(path)
                return preferred or name
    except Exception:
        return None
    return None


def preprocess_todayphrase_startup() -> None:
    """启动时预处理：转换为 WEBP 并保留单个文件"""
    try:
        if not os.path.isdir(TODAY_PHRASE_DIR):
            return
        candidate_path: Optional[str] = None
        for name in os.listdir(TODAY_PHRASE_DIR):
            full = os.path.join(TODAY_PHRASE_DIR, name)
            if not os.path.isfile(full):
                continue
            _, ext = os.path.splitext(name)
            if ext.lower() in IMAGE_EXTENSIONS:
                candidate_path = full
                break
        if not candidate_path:
            return
            
        _maybe_generate_webp_for(candidate_path)
        
        try:
            if os.path.exists(candidate_path) and os.path.splitext(candidate_path)[1].lower() != ".webp":
                os.remove(candidate_path)
        except Exception:
            pass
            
        kept = False
        for name in sorted(os.listdir(TODAY_PHRASE_DIR)):
            full = os.path.join(TODAY_PHRASE_DIR, name)
            if not os.path.isfile(full):
                continue
            _, ext = os.path.splitext(name)
            if ext.lower() in IMAGE_EXTENSIONS:
                if not kept and ext.lower() == ".webp" and os.path.getsize(full) > 0:
                    kept = True
                    continue
                try:
                    os.remove(full)
                except Exception:
                    pass
    except Exception:
        pass


@router.get("/api/todayphrase")
async def api_todayphrase():
    """返回今日一签图片信息"""
    name = _find_todayphrase_file()
    if not name:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "name": name,
        "url": f"/todayphrase/{name}",
    }


@router.get("/todayphrase/{filename}")
async def todayphrase_raw(filename: str):
    """提供今日一签图片文件"""
    safe_name = os.path.basename(filename)
    _, ext = os.path.splitext(safe_name)
    if ext.lower() not in IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="invalid file type")
    directory = TODAY_PHRASE_DIR
    if not os.path.isdir(directory) or not os.path.exists(os.path.join(directory, safe_name)):
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(os.path.join(directory, safe_name))

