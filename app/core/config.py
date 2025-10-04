import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_SENTENCE_DIR = os.path.join(BASE_DIR, "data_sentence")
DATA_VOCAB_DIR = os.path.join(BASE_DIR, "data_vocabulary")
TODAY_PHRASE_DIR = os.path.join(BASE_DIR, "TodayPhrase")
SQLITE_DIR = os.path.join(BASE_DIR, "sqlite")
SQLITE_DB_PATH = os.path.join(SQLITE_DIR, "paraphrase.sqlite")  # 单词数据库
USER_ACTIVITY_DB_PATH = os.path.join(SQLITE_DIR, "user_activity.sqlite")  # 用户行为数据库（独立）
APIKEY_PATH = os.path.join(BASE_DIR, "apikey.json")

TXT_EXTENSIONS = {".txt"}
EXCEL_EXTENSIONS = {".xlsx", ".xls"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

# 确保必要目录存在
os.makedirs(SQLITE_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

