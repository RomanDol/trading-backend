from fastapi import APIRouter, Request
from pydantic import BaseModel
from pathlib import Path
import json
import threading

router = APIRouter()
save_lock = threading.Lock()

# === Модели запроса
class LoadPresetRequest(BaseModel):
    strategyPath: str
    presetName: str

class SavePresetRequest(BaseModel):
    strategyPath: str
    presetName: str
    inputs: dict

class DeletePresetRequest(BaseModel):
    strategyPath: str
    presetName: str

class PresetsListRequest(BaseModel):
    strategyPath: str

# === Путь до presets.json
def get_presets_path(strategy_path: str) -> Path:
    return Path("strategies") / strategy_path / "presets.json"

# === Загрузка всех названий пресетов
@router.post("/api/presets/list")
def list_presets(req: PresetsListRequest):
    presets_path = get_presets_path(req.strategyPath)
    if not presets_path.exists():
        return {"presets": []}
    with open(presets_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {"presets": list(data.keys())}

# === Загрузка одного пресета
@router.post("/api/presets/load")
def load_preset(req: LoadPresetRequest):
    presets_path = get_presets_path(req.strategyPath)
    if not presets_path.exists():
        return {"success": False, "error": "Presets file not found"}
    with open(presets_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"success": True, "inputs": data.get(req.presetName)}

# === Сохранение/обновление пресета
@router.post("/api/presets/save")
def save_preset(req: SavePresetRequest):
    presets_path = get_presets_path(req.strategyPath)

    with save_lock:
        # создаём директорию, если нет
        presets_path.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        if presets_path.exists():
            with open(presets_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    return {"success": False, "error": "Invalid presets.json format"}

        # Сбросить флаг активности у всех
        for preset in data.values():
            preset["isActive"] = False

        # Установить флаг активности текущему
        req.inputs["isActive"] = True
        data[req.presetName] = req.inputs

        with open(presets_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"success": True}

# === Удаление пресета
@router.post("/api/presets/delete")
def delete_preset(req: DeletePresetRequest):
    presets_path = get_presets_path(req.strategyPath)
    if not presets_path.exists():
        return {"success": False, "error": "Presets file not found"}
    with save_lock:
        with open(presets_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if req.presetName in data:
            del data[req.presetName]
            with open(presets_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return {"success": True}
    return {"success": False, "error": "Preset not found"}

