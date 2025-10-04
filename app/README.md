# 连词成句 - FastAPI 版本

从 Flask 重构为 FastAPI 的版本，保持所有原有功能。

## 项目结构

```
fastapi版本/
├── main.py              # 入口文件
├── requirements.txt     # 依赖清单
├── core/               # 核心模块
│   ├── config.py       # 配置与路径
│   ├── database.py     # SQLite 数据库操作
│   ├── loading.py      # 加载状态管理
│   └── utils.py        # 工具函数
├── routers/            # 路由模块
│   ├── site.py         # 站点统计
│   ├── todayphrase.py  # 今日一签
│   ├── sentences.py    # 情境句
│   ├── excel.py        # Excel 管理
│   ├── lookup.py       # 单词查询
│   ├── wordbook.py     # 单词库
│   └── ai.py          # AI 聊天
├── templates/          # 前端模板
├── static/            # 静态资源
├── data_sentence/     # 情境句数据
├── data_vocabulary/   # 词汇数据
├── TodayPhrase/       # 今日一签图片
└── data.xlsx          # 词库 Excel

## 启动方式

1. 安装依赖：
```bash
cd "C:\Users\Administrator\Desktop\新建文件夹\fastapi版本"
pip install -r requirements.txt
```

2. 启动服务：
```bash
uvicorn main:app --reload
```

3. 访问：
- 主页：http://127.0.0.1:8000/
- API 文档：http://127.0.0.1:8000/docs

## 功能特性

- ✅ 在线人数统计（会话跟踪）
- ✅ 今日一签（自动 WEBP 转换）
- ✅ 情境句列表与阅读（自然排序、编码兜底）
- ✅ Excel 词库加载（后台线程、SQLite 存储）
- ✅ 单词查询与释义
- ✅ 单词库批次浏览
- ✅ AI 聊天（硅基流动 API）

## 与 Flask 版本的对比

- **架构**：模块化拆分，更易维护
- **性能**：异步支持，更高并发
- **文档**：自动生成 API 文档（/docs）
- **类型**：完整类型提示
- **部署**：支持 uvicorn/gunicorn

## 生产部署

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

或使用 gunicorn：
```bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

