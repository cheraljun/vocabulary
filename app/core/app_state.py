"""
应用全局状态管理
用类统一管理全局变量，避免散落各处
"""
from typing import Optional


class AppState:
    """应用全局状态类（单例模式）"""
    
    _instance = None
    
    def __new__(cls):
        """确保只有一个实例（单例模式）"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化状态变量"""
        if self._initialized:
            return
        
        # 数据加载状态
        self.data_loaded: bool = False
        self.data_loading: bool = False
        
        # 当前Excel文件路径
        self.current_excel_file: Optional[str] = None
        
        # 应用启动时间
        self.start_time: Optional[float] = None
        
        # 数据库连接池（会在main.py中设置）
        self.db_pool = None  # 单词数据库连接池
        self.activity_db_pool = None  # 用户行为数据库连接池（独立）
        
        self._initialized = True
    
    def reset(self):
        """重置状态（用于测试或重载）"""
        self.data_loaded = False
        self.data_loading = False
        self.current_excel_file = None


# 全局应用状态实例
app_state = AppState()

