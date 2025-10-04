"""
IP追踪与访问记录模块

功能：
1. 获取用户IP和归属地（带缓存）
2. 记录用户操作到数据库
3. 定时导出CSV文件（每1分钟）
4. 自动清理7天前的旧CSV文件
"""
import os
import csv
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request

from .config import BASE_DIR
from .app_state import app_state
from .logger import get_logger

logger = get_logger(__name__)

# IP归属地查询API
IP_API_URL = "https://api.pearktrue.cn/api/ip/high/"
IP_API_TIMEOUT = 5.0  # 5秒超时

# CSV导出配置
CSV_EXPORT_INTERVAL = 60  # 60秒导出一次
CSV_KEEP_DAYS = 7  # 保留最近7天


async def init_ip_tables():
    """初始化IP追踪相关的数据库表（使用独立的用户行为数据库）"""
    try:
        with app_state.activity_db_pool.get_db() as conn:
            cursor = conn.cursor()
            
            # 启用WAL模式（提升写入性能和并发能力）
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=5000;")
            logger.info("用户行为数据库已启用WAL模式")
            
            # 表1：IP归属地缓存
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_cache (
                    ip TEXT PRIMARY KEY,
                    location TEXT,
                    cached_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 表2：访问操作日志
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    ip TEXT,
                    location TEXT,
                    session_id TEXT,
                    detail_key TEXT,
                    detail_value TEXT,
                    detail_extra TEXT
                )
            """)
            
            # 创建索引（提升查询速度）
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ip_log_timestamp 
                ON ip_access_log(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ip_log_ip 
                ON ip_access_log(ip)
            """)
            
            conn.commit()
            logger.info("IP追踪数据库表初始化完成")
    except Exception as e:
        logger.error(f"IP追踪表初始化失败: {e}", exc_info=True)


async def get_ip_location(ip: str) -> str:
    """
    查询IP归属地（带缓存）
    
    参数：
        ip: IP地址
    
    返回：
        归属地字符串，如"北京市海淀区"，失败返回"未知地区"
    """
    # 本地IP特殊处理
    if ip in ("127.0.0.1", "localhost") or ip.startswith("192.168.") or ip.startswith("10."):
        return "本地网络"
    
    try:
        # 1. 先查缓存
        with app_state.activity_db_pool.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT location FROM ip_cache WHERE ip = ?", (ip,))
            result = cursor.fetchone()
            if result:
                return result[0]
        
        # 2. 缓存没有，调用API
        async with httpx.AsyncClient(timeout=IP_API_TIMEOUT) as client:
            response = await client.get(IP_API_URL, params={"ip": ip})
            response.raise_for_status()
            data = response.json()
            
            # 解析归属地（API返回格式可能不同，做兼容处理）
            location = "未知地区"
            if isinstance(data, dict):
                # 兼容嵌套结构：优先从 data.data 里取（新API格式）
                data_obj = data.get("data", data)  # 如果有 data 字段，就用它；否则用顶层对象
                
                # 优先使用 address 字段（最详细：省+市+区+街道+社区）
                if "address" in data_obj and data_obj["address"]:
                    location = data_obj["address"]
                elif "detail" in data_obj and data_obj["detail"]:
                    # 备选：detail 字段（省+市+区）
                    location = data_obj["detail"]
                else:
                    # 后备方案：拼接 province + city
                    province = data_obj.get("province", data_obj.get("region", ""))
                    city = data_obj.get("city", "")
                    
                    if province and city:
                        location = f"{province}{city}"
                    elif province:
                        location = province
                    elif city:
                        location = city
                    elif "location" in data_obj:
                        location = data_obj["location"]
        
        # 3. 存入缓存
        try:
            with app_state.activity_db_pool.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO ip_cache (ip, location) VALUES (?, ?)",
                    (ip, location)
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"缓存IP归属地失败: {e}")
        
        return location
        
    except httpx.TimeoutException:
        logger.warning(f"IP归属地查询超时: {ip}")
        return "未知地区"
    except Exception as e:
        logger.warning(f"IP归属地查询失败 [{ip}]: {e}")
        return "未知地区"


async def track_ip(
    request: Request,
    event_type: str,
    details: Optional[Dict[str, Any]] = None
):
    """
    记录用户操作
    
    参数：
        request: FastAPI请求对象
        event_type: 事件类型（AI对话、查询单词、打开句子）
        details: 详细信息字典
    """
    try:
        # 1. 获取IP
        ip = request.client.host
        if "x-forwarded-for" in request.headers:
            ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # 2. Session ID（已移除在线统计功能，保留字段为空）
        session_id = ""
        
        # 3. 查询归属地（异步，带缓存）
        location = await get_ip_location(ip)
        
        # 4. 解析详情
        detail_key = ""
        detail_value = ""
        detail_extra = ""
        
        if details:
            if event_type == "AI对话":
                # 为了用户隐私，不记录AI对话的具体内容
                detail_key = ""
                detail_value = ""
                detail_extra = ""
            elif event_type == "查询单词":
                detail_key = "word"
                detail_value = details.get("word", "")
            elif event_type == "打开句子":
                detail_key = "filename"
                detail_value = details.get("filename", "")
        
        # 5. 记录到数据库
        with app_state.activity_db_pool.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ip_access_log 
                (event_type, ip, location, session_id, detail_key, detail_value, detail_extra)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (event_type, ip, location, session_id, detail_key, detail_value, detail_extra))
            conn.commit()
        
        # 6. 输出详细日志
        log_detail = ""
        if event_type == "AI对话":
            # 为了用户隐私，不显示AI对话的具体内容
            log_detail = ""
        elif event_type == "查询单词" and detail_value:
            log_detail = f" | 单词: {detail_value}"
        elif event_type == "打开句子" and detail_value:
            log_detail = f" | 文件: {detail_value}"
        
        logger.info(f"记录操作: {event_type} | IP: {ip} | {location}{log_detail}")
        
    except Exception as e:
        # 记录失败不影响正常功能
        logger.warning(f"IP追踪记录失败: {e}")


async def export_csv_task():
    """
    后台任务：定时导出CSV
    每60秒运行一次
    """
    logger.info("CSV导出任务已启动")
    
    while True:
        try:
            await asyncio.sleep(CSV_EXPORT_INTERVAL)
            await export_today_csv()
            await cleanup_old_csv()
        except Exception as e:
            logger.error(f"CSV导出任务异常: {e}", exc_info=True)


async def export_today_csv():
    """导出今天的访问记录为CSV"""
    try:
        # 1. 获取今天的日期
        today = datetime.now().strftime("%Y%m%d")
        csv_dir = os.path.join(BASE_DIR, "logs", "ip")
        os.makedirs(csv_dir, exist_ok=True)
        
        csv_file = os.path.join(csv_dir, f"ip_access_{today}.csv")
        
        # 2. 从数据库读取今天的记录（只要详情1，不要详情2）
        with app_state.activity_db_pool.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m-%d %H:%M:%S', timestamp) as time,
                    event_type,
                    ip,
                    location,
                    session_id,
                    detail_value
                FROM ip_access_log
                WHERE DATE(timestamp) = DATE('now', 'localtime')
                ORDER BY timestamp ASC
            """)
            records = cursor.fetchall()
        
        # 3. 写入CSV（UTF-8-BOM编码，Windows Excel完美打开）
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            # 表头（去掉"详情2"列）
            writer.writerow(['时间', '事件类型', 'IP地址', '归属地', '会话ID', '详情'])
            # 数据行
            writer.writerows(records)
        
        logger.info(f"CSV导出成功: {csv_file} ({len(records)}条记录)")
        
    except Exception as e:
        logger.error(f"CSV导出失败: {e}", exc_info=True)


async def cleanup_old_csv():
    """清理7天前的旧CSV文件"""
    try:
        csv_dir = os.path.join(BASE_DIR, "logs", "ip")
        if not os.path.exists(csv_dir):
            return
        
        # 计算7天前的日期
        cutoff_date = datetime.now() - timedelta(days=CSV_KEEP_DAYS)
        cutoff_str = cutoff_date.strftime("%Y%m%d")
        
        # 遍历CSV文件
        deleted_count = 0
        for filename in os.listdir(csv_dir):
            if filename.startswith("ip_access_") and filename.endswith(".csv"):
                # 提取日期：ip_access_20251003.csv → 20251003
                try:
                    date_str = filename[10:18]  # 截取日期部分
                    if date_str < cutoff_str:
                        file_path = os.path.join(csv_dir, filename)
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"删除旧CSV: {filename}")
                except Exception as e:
                    logger.warning(f"清理文件失败 [{filename}]: {e}")
        
        if deleted_count > 0:
            logger.info(f"清理完成，删除了 {deleted_count} 个旧CSV文件")
            
    except Exception as e:
        logger.error(f"CSV清理失败: {e}", exc_info=True)

