import sqlite3
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Request

from core.config import SQLITE_DB_PATH
from core.database import is_data_loaded
from core.utils import normalize_word
from core.app_state import app_state
from core.logger import get_logger
from core.ip_tracker import track_ip

router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/lookup")
async def api_lookup(word: str, request: Request):
    """查询单词释义（使用连接池）"""
    if not is_data_loaded():
        logger.warning("查询失败：数据库未加载")
        raise HTTPException(status_code=400, detail="loading or db not ready")
    if not word:
        raise HTTPException(status_code=400, detail="missing word")
    
    norm = normalize_word(word)
    logger.info(f"查询单词: {word} (规范化: {norm})")
    
    try:
        # 使用连接池（自动获取和归还连接）
        with app_state.db_pool.get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT word, phonetic, meaning FROM entries WHERE word_norm = ? LIMIT 1",
                (norm,),
            )
            result = cur.fetchone()
            
            if not result:
                logger.info(f"单词未找到: {word}")
                raise HTTPException(status_code=404, detail="not found")
            
            w, phonetic, meaning = result
            row_obj = {
                "1": w or "",
                "2": phonetic or "",
                "3": meaning or "",
            }
            logger.info(f"查询成功: {word}")
            
            # 记录查询单词
            try:
                await track_ip(request, "查询单词", {"word": word})
            except Exception as e:
                logger.warning(f"记录查询失败: {e}")
            
            return {"word": word, "row": row_obj}
            
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"查询异常 [{word}]: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"db error: {exc}")


@router.get("/api/excel/search")
async def api_excel_search(word: str):
    """搜索单词位置（使用连接池）"""
    if not is_data_loaded():
        logger.warning("搜索失败：数据库未加载")
        raise HTTPException(status_code=400, detail="loading or db not ready")
    if not word:
        raise HTTPException(status_code=400, detail="missing word")
    
    norm = normalize_word(word)
    logger.info(f"搜索单词位置: {word}")
    
    try:
        with app_state.db_pool.get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT sheet, row_index FROM entries WHERE word_norm = ? LIMIT 1",
                (norm,),
            )
            rows = cur.fetchall()
            matches: List[Dict[str, Any]] = []
            for s, r in rows:
                matches.append({"sheet": s, "row_index": int(r) if r is not None else 0})
            
            logger.info(f"搜索成功: {word}, 找到 {len(matches)} 个结果")
            return {"word": word, "normalized": norm, "count": len(matches), "matches": matches}
    except Exception as exc:
        logger.error(f"搜索异常 [{word}]: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"db error: {exc}")


@router.get("/api/excel/row")
async def api_excel_row(sheet: str, row_index: int):
    """根据位置查询单词（使用连接池）"""
    if not is_data_loaded():
        logger.warning("位置查询失败：数据库未加载")
        raise HTTPException(status_code=400, detail="loading or db not ready")
    if not sheet or row_index < 0:
        raise HTTPException(status_code=400, detail="missing sheet or row_index")
    
    logger.info(f"按位置查询: sheet={sheet}, row={row_index}")
    
    try:
        with app_state.db_pool.get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT word, phonetic, meaning FROM entries WHERE sheet = ? AND row_index = ?",
                (sheet, row_index),
            )
            result = cur.fetchone()
            
            if not result:
                logger.info(f"位置未找到: sheet={sheet}, row={row_index}")
                raise HTTPException(status_code=404, detail="not found")
            
            word_text, phonetic, meaning = result
            row_obj = {
                "1": word_text or "",
                "2": phonetic or "",
                "3": meaning or "",
            }
            logger.info(f"位置查询成功: {word_text}")
            return {
                "sheet": sheet,
                "row_index": row_index,
                "row": row_obj,
            }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"位置查询异常 [sheet={sheet}, row={row_index}]: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"db error: {exc}")

