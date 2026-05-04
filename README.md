# A-Share Market Dashboard

A-Share Market Dashboard: 核心设计宣言 (Vibe Coding Manifesto)

## 架构原则：三权分立

```
config/   — 统一配置层（颜色常量、指数代码、刷新频率）
data/     — 数据获取层（只负责"拿"，不负责"算"）
logic/    — 业务逻辑层（指标计算，与视图无关）
view/     — 视图渲染层（FastAPI 入口，无业务逻辑）
```

## 快速开始

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn view.app:app --reload --port 8000
```

访问 http://127.0.0.1:8000/docs 查看 API 文档。

## 环境变量

复制 `.env.example` 到 `.env` 并填入真实配置值。

## 开发准则

遵循 [MANIFESTO.md](file:///h:/QUART/MANIFESTO.md) — 项目宪法。
