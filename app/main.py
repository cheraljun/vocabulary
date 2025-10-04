import os
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.config import (
    TEMPLATES_DIR, STATIC_DIR, SQLITE_DB_PATH, USER_ACTIVITY_DB_PATH, BASE_DIR,
    EXCEL_EXTENSIONS
)
from core.database import start_loading
from core.db_pool import DatabasePool
from core.logger import setup_logging, get_logger
from core.app_state import app_state
from core.ip_tracker import init_ip_tables, export_csv_task
from routers import todayphrase, sentences, excel, lookup, wordbook, ai
from routers.todayphrase import preprocess_todayphrase_startup

# 设置日志系统
setup_logging(log_dir="logs", level=20)  # 20 = INFO
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理（启动和关闭时的操作）- 顺序执行，避免冲突"""
    # 启动时执行（按顺序一个一个来）
    logger.info("应用启动中...")
    app_state.start_time = time.time()
    
    # 初始化用户行为数据库连接池
    logger.info("正在初始化用户行为数据库...")
    try:
        activity_pool = DatabasePool(USER_ACTIVITY_DB_PATH, pool_size=3)
        activity_pool.initialize()
        app_state.activity_db_pool = activity_pool
        logger.info("用户行为数据库初始化完成")
    except Exception as e:
        logger.error(f"用户行为数据库初始化失败: {e}", exc_info=True)
    
    # 初始化IP追踪表
    logger.info("正在初始化IP追踪表...")
    try:
        await init_ip_tables()
        logger.info("IP追踪表初始化完成")
    except Exception as e:
        logger.error(f"IP追踪表初始化失败: {e}", exc_info=True)
    
    # 预处理今日一签
    logger.info("正在预处理今日一签...")
    try:
        preprocess_todayphrase_startup()
        logger.info("今日一签预处理完成")
    except Exception as e:
        logger.warning(f"今日一签预处理失败: {e}")
    
    # 删除旧数据库文件（总是重新加载，保证数据最新且干净）
    logger.info("正在清理旧数据库...")
    try:
        # 删除主数据库文件
        if os.path.exists(SQLITE_DB_PATH):
            os.remove(SQLITE_DB_PATH)
            logger.info("已删除旧数据库文件")
        
        # 删除WAL文件（如果存在）
        wal_file = SQLITE_DB_PATH + "-wal"
        if os.path.exists(wal_file):
            os.remove(wal_file)
            logger.info("已删除WAL文件")
        
        # 删除SHM文件（如果存在）
        shm_file = SQLITE_DB_PATH + "-shm"
        if os.path.exists(shm_file):
            os.remove(shm_file)
            logger.info("已删除SHM文件")
    except Exception as e:
        logger.error(f"清理旧数据库失败: {e}", exc_info=True)
    
    # 查找Excel文件
    logger.info("正在查找Excel文件...")
    excel_to_load = None
    try:
        excel_candidates = [
            name for name in os.listdir(BASE_DIR)
            if os.path.isfile(os.path.join(BASE_DIR, name))
            and os.path.splitext(name)[1].lower() in EXCEL_EXTENSIONS
        ]
        excel_candidates.sort()
        if excel_candidates:
            excel_to_load = os.path.join(BASE_DIR, excel_candidates[0])
            logger.info(f"找到Excel文件: {excel_candidates[0]}")
        else:
            logger.error("未找到Excel文件，无法启动")
    except Exception as e:
        logger.error(f"查找Excel文件失败: {e}", exc_info=True)
    
    # 加载Excel（总是加载）
    if excel_to_load:
        logger.info(f"正在加载Excel文件: {os.path.basename(excel_to_load)}")
        try:
            start_loading(excel_to_load)
            
            # 等待加载完成（最多等120秒）
            from core.loading import loading_state
            for i in range(120):
                await asyncio.sleep(1)
                snap = loading_state.snapshot()
                if not snap.get("running"):
                    if snap.get("error"):
                        logger.error(f"Excel加载失败: {snap.get('error')}")
                    else:
                        logger.info("Excel加载完成")
                        # 设置当前Excel文件
                        app_state.current_excel_file = excel_to_load
                    break
                if i % 10 == 0 and i > 0:
                    logger.info(f"加载进度: {snap.get('processed', 0)}/{snap.get('total_rows', 0)}")
            else:
                logger.warning("Excel加载超时")
        except Exception as e:
            logger.error(f"Excel加载失败: {e}", exc_info=True)
    
    # 初始化单词数据库连接池
    logger.info("正在初始化单词数据库连接池...")
    try:
        import core.db_pool as pool_module
        pool_module.db_pool = DatabasePool(SQLITE_DB_PATH, pool_size=2)
        pool_module.db_pool.initialize()
        app_state.db_pool = pool_module.db_pool
        app_state.data_loaded = True
        logger.info("单词数据库连接池初始化完成")
    except Exception as e:
        logger.error(f"单词数据库连接池初始化失败: {e}", exc_info=True)
    
    # 启动CSV导出后台任务
    logger.info("正在启动CSV导出任务...")
    try:
        asyncio.create_task(export_csv_task())
        logger.info("CSV导出任务启动完成")
    except Exception as e:
        logger.error(f"CSV导出任务启动失败: {e}", exc_info=True)
    
    logger.info("应用启动完成")
    
    yield  # 应用运行期间
    
    # ========== 关闭时执行 ==========
    logger.info("应用关闭中...")
    
    # 关闭单词数据库连接池
    if app_state.db_pool:
        try:
            app_state.db_pool.close_all()
            logger.info("单词数据库连接池已关闭")
        except Exception as e:
            logger.error(f"关闭单词数据库连接池失败: {e}")
    
    # 关闭用户行为数据库连接池
    if app_state.activity_db_pool:
        try:
            app_state.activity_db_pool.close_all()
            logger.info("用户行为数据库连接池已关闭")
        except Exception as e:
            logger.error(f"关闭用户行为数据库连接池失败: {e}")
    
    logger.info("应用已关闭")


app = FastAPI(title="连词成句 - FastAPI 版", lifespan=lifespan)

# 挂载静态文件与模板
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 注册所有路由
app.include_router(todayphrase.router, tags=["todayphrase"])
app.include_router(sentences.router, tags=["sentences"])
app.include_router(excel.router, tags=["excel"])
app.include_router(lookup.router, tags=["lookup"])
app.include_router(wordbook.router, tags=["wordbook"])
app.include_router(ai.router, tags=["ai"])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """
    健康检查接口
    用于监控服务状态
    """
    try:
        # 计算运行时间
        uptime_seconds = int(time.time() - app_state.start_time) if app_state.start_time else 0
        uptime_hours = uptime_seconds // 3600
        uptime_minutes = (uptime_seconds % 3600) // 60
        
        # 检查数据库连接
        db_status = "未初始化"
        if app_state.db_pool:
            try:
                with app_state.db_pool.get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM entries")
                    word_count = cursor.fetchone()[0]
                    db_status = f"正常 ({word_count}个单词)"
            except Exception as e:
                db_status = f"异常: {str(e)}"
        
        return JSONResponse({
            "status": "healthy",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": f"{uptime_hours}小时 {uptime_minutes}分钟",
            "database": {
                "status": db_status,
                "loaded": app_state.data_loaded,
                "current_file": os.path.basename(app_state.current_excel_file) if app_state.current_excel_file else None
            },
            "connection_pool": {
                "initialized": app_state.db_pool is not None,
                "pool_size": app_state.db_pool.pool_size if app_state.db_pool else 0
            }
        })
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e)
        }, status_code=500)


if __name__ == "__main__":
    import uvicorn
    
    # 生产模式：单进程，稳定可靠（2核2G服务器推荐配置）
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        log_level="info",           # 保留重要日志
        limit_concurrency=300,      # 最大并发连接数
        timeout_keep_alive=120      # Keep-Alive 超时时间
    )
    
