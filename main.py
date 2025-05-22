from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path

app = FastAPI()

# Разрешаем доступ с фронта (localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Backend is working"}

@app.get("/equity")
def get_equity():
    file_path = Path("data/equity.json")
    if file_path.exists():
        return json.loads(file_path.read_text(encoding="utf-8"))
    return {"data": []}

@app.get("/trades")
def get_trades():
    file_path = Path("data/trades.json")
    if file_path.exists():
        return json.loads(file_path.read_text(encoding="utf-8"))
    return {"data": []}

# укпвукп
