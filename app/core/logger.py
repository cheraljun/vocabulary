"""
日志系统配置
记录应用运行日志、错误日志、访问日志
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logging(log_dir: str = "logs", level: int = logging.INFO):
    """
    配置应用日志系统
    
    参数：
    - log_dir: 日志文件夹路径
    - level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    
    生成的日志文件：
    - app.log: 所有日志（自动轮转，每个10MB）
    - error.log: 只记录错误日志
    """
    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 获取根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除已有的handlers（避免重复）
    root_logger.handlers.clear()
    
    # 🔇 静默这些框架的INFO日志（只记录WARNING及以上）
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)  # 禁用文件监控日志
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    
    # 1. 控制台处理器（输出到终端）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 2. 应用日志文件（所有日志，自动轮转）
    app_log_file = os.path.join(log_dir, "app.log")
    app_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,  # 保留5个备份
        encoding='utf-8'
    )
    app_handler.setLevel(level)
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)
    
    # 3. 错误日志文件（只记录ERROR及以上）
    error_log_file = os.path.join(log_dir, "error.log")
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # 记录日志系统启动信息
    logging.info("=" * 60)
    logging.info(f"日志系统已启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"日志目录: {os.path.abspath(log_dir)}")
    logging.info(f"日志级别: {logging.getLevelName(level)}")
    logging.info("=" * 60)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的logger
    
    参数：
    - name: logger名称（通常使用 __name__）
    
    返回：
    - Logger对象
    
    用法：
    ```python
    from core.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("这是一条信息")
    logger.error("这是一个错误", exc_info=True)
    ```
    """
    return logging.getLogger(name)

