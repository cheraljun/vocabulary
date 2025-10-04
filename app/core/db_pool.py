"""
数据库连接池管理
用于复用数据库连接，提升性能
"""
import sqlite3
from contextlib import contextmanager
from typing import Optional
from queue import Queue, Empty
import threading


class DatabasePool:
    """SQLite数据库连接池（线程安全）"""
    
    def __init__(self, db_path: str, pool_size: int = 5):
        """
        初始化连接池
        
        参数：
        - db_path: 数据库文件路径
        - pool_size: 连接池大小（默认5个连接）
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: Queue = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._initialized = False
    
    def initialize(self):
        """初始化连接池（创建连接）"""
        with self._lock:
            if self._initialized:
                return
            
            for _ in range(self.pool_size):
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row  # 返回字典格式
                self._pool.put(conn)
            
            self._initialized = True
    
    def get_connection(self, timeout: float = 5.0) -> Optional[sqlite3.Connection]:
        """
        从连接池获取一个连接
        
        参数：
        - timeout: 等待超时时间（秒）
        
        返回：
        - 数据库连接对象，如果超时则返回None
        """
        try:
            return self._pool.get(timeout=timeout)
        except Empty:
            return None
    
    def return_connection(self, conn: sqlite3.Connection):
        """
        归还连接到连接池
        
        参数：
        - conn: 数据库连接对象
        """
        if conn:
            self._pool.put(conn)
    
    @contextmanager
    def get_db(self):
        """
        上下文管理器，自动获取和归还连接
        
        用法：
        ```python
        with db_pool.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entries LIMIT 1")
            result = cursor.fetchone()
        # 连接自动归还到池中
        ```
        """
        conn = self.get_connection()
        if not conn:
            raise Exception("无法从连接池获取数据库连接")
        try:
            yield conn
        finally:
            self.return_connection(conn)
    
    def close_all(self):
        """关闭所有连接（应用关闭时调用）"""
        with self._lock:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except Empty:
                    break
            self._initialized = False


# 全局连接池实例（会在main.py中初始化）
db_pool: Optional[DatabasePool] = None

