import sqlite3
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from core.config import SQLITE_DB_PATH
from core.database import is_data_loaded
from core.app_state import app_state
from core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/wordbook/batches")
async def api_wordbook_batches():
    """获取单词库批次列表（使用连接池）"""
    if not is_data_loaded():
        logger.warning("批次列表获取失败：数据库未加载")
        raise HTTPException(status_code=400, detail="loading or db not ready")
    
    logger.info("获取单词库批次列表")
    
    try:
        with app_state.db_pool.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM entries")
            (total_count,) = cur.fetchone() or (0,)
            
            total_count = int(total_count or 0)
            batch_size = 100
            batches = []
            if total_count > 0:
                start = 1
                while start <= total_count:
                    end = min(start + batch_size - 1, total_count)
                    label = f"V{start}-{end}"
                    batches.append({"label": label, "start": start, "end": end})
                    start = end + 1
            
            logger.info(f"批次列表生成成功: 总计 {total_count} 个单词, {len(batches)} 个批次")
            return {"total": total_count, "batch_size": batch_size, "batches": batches}
    except Exception as exc:
        logger.error(f"批次列表获取异常: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"db error: {exc}")


@router.get("/api/wordbook/range")
async def api_wordbook_range(start: int = 1, end: int = 0):
    """获取单词库指定范围（使用连接池）"""
    if not is_data_loaded():
        logger.warning("范围查询失败：数据库未加载")
        raise HTTPException(status_code=400, detail="loading or db not ready")
    if start <= 0 or end < start or (end - start) > 1000:
        raise HTTPException(status_code=400, detail="invalid range")
    
    logger.info(f"获取单词范围: {start}-{end}")
    
    try:
        with app_state.db_pool.get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, word, phonetic, meaning FROM entries WHERE id BETWEEN ? AND ? ORDER BY id ASC",
                (start, end),
            )
            rows = cur.fetchall()
            
            items = []
            for rid, w, phon, mean in rows:
                items.append({
                    "id": int(rid or 0),
                    "word": w or "",
                    "phonetic": phon or "",
                    "meaning": mean or "",
                })
            
            logger.info(f"范围查询成功: 返回 {len(items)} 个单词")
            return {"start": start, "end": end, "count": len(items), "items": items}
    except Exception as exc:
        logger.error(f"范围查询异常 [{start}-{end}]: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"db error: {exc}")

