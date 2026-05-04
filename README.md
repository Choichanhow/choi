# QUART API

A FastAPI-based REST API project.

## Setup

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your real API key:

```bash
cp .env.example .env
```

## Run

```bash
python -m uvicorn main:app --reload --port 8000
```

Then open http://127.0.0.1:8000/docs to view the API documentation.
