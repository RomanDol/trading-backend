from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path
from fastapi import Request
import subprocess
from fastapi import Query
from presets import router as presets_router


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

@app.get("/list-strategies")
def list_strategies():
    base_path = Path("strategies")

    def walk(path: Path):
        items = []
        for p in sorted(path.iterdir()):
            if p.name.startswith(".") or p.name.startswith("_"):
                continue

            if (p / "strategy.py").exists():
                items.append({
                    "name": p.name,
                    "type": "strategy",
                    "path": str(p.relative_to(base_path)).replace("\\", "/")
                })
            elif p.is_dir():
                items.append({
                    "name": p.name,
                    "type": "folder",
                    "children": walk(p)
                })

        return items

    if not base_path.exists():
        return []
    return walk(base_path)






@app.post("/run-strategy")
async def run_strategy(request: Request):
    body = await request.json()
    path = Path("strategies") / body["path"]
    if not path.exists():
        return {"error": "strategy folder not found"}

    inputs = body.get("inputs", {})

    script = path / "strategy.py"
    if not script.exists():
        return {"error": "strategy.py not found"}

    result = subprocess.run(
        ["python", str(script)],
        input=json.dumps(inputs),
        text=True,
        capture_output=True
    )

    if result.returncode != 0:
        return {
            "status": "error",
            "stderr": result.stderr
        }

    return {"status": "ok"}





@app.get("/load-inputs")
def load_inputs(path: str = Query(..., description="Relative path to strategy folder")):
    folder = Path("strategies") / path
    file = folder / "presets.json"
    if not file.exists():
        return []
    
    raw = json.loads(file.read_text(encoding="utf-8"))

    # Преобразуем словарь в список и добавляем ключ preset
    result = []
    for name, content in raw.items():
        preset = dict(content)
        preset["preset"] = name
        result.append(preset)

    return result


@app.get("/load-strategy-meta")
def load_strategy_meta(path: str = Query(...)):
    folder = Path("strategies") / path
    file = folder / "strategy.py"
    if not file.exists():
        return {}

    contents = file.read_text(encoding="utf-8")
    result = {}

    for var in ["symbol", "timeframe", "file_name"]:
        line = next((l for l in contents.splitlines() if l.startswith(var)), None)
        if line:
            try:
                result[var] = eval(line.split("=", 1)[1].strip(), {}, {})
            except:
                result[var] = None

    return result


@app.post("/run-strategy")
async def run_strategy(request: Request):
    body = await request.json()
    path = Path("strategies") / body["path"]
    if not path.exists():
        return {"error": "strategy not found"}

    inputs = body.get("inputs", {})

    result = subprocess.run(
        ["python", str(path / "strategy.py")],
        input=json.dumps(inputs),
        text=True,
        capture_output=True
    )

    if result.returncode != 0:
        return {
            "status": "error",
            "stderr": result.stderr
        }

    return {"status": "ok"}




app.include_router(presets_router)

