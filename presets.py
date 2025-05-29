from fastapi import APIRouter, Request
from pydantic import BaseModel
from pathlib import Path
import json
import threading

router = APIRouter()
save_lock = threading.Lock()

# === Модели запроса
class LoadPresetRequest(BaseModel):
    presetPath: str
    presetName: str

class SavePresetRequest(BaseModel):
    presetPath: str
    presetName: str
    inputs: dict

class DeletePresetRequest(BaseModel):
    presetPath: str
    presetName: str

class PresetsListRequest(BaseModel):
    presetPath: str


# === Путь до presets.json
def get_preset_path(preset_path: str) -> Path:
    return Path("presets") / preset_path



# === Загрузка всех названий пресетов
@router.post("/api/presets/list")
def list_presets(req: PresetsListRequest):
    presets_path = get_preset_path(req.presetPath)
    if not presets_path.exists():
        return {"presets": []}
    with open(presets_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {"presets": list(data.keys())}



# === Загрузка одного пресета
@router.post("/api/presets/load")
def load_preset(req: LoadPresetRequest):
    presets_path = get_preset_path(req.presetPath)
    if not presets_path.exists():
        return {"success": False, "error": "Presets file not found"}
    with open(presets_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"success": True, "inputs": data.get(req.presetName)}

# === Сохранение/обновление пресета
@router.post("/api/presets/save")
def save_preset(req: SavePresetRequest):
    presets_path = get_preset_path(req.presetPath)

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
    presets_path = get_preset_path(req.presetPath)
    if not presets_path.exists():
        return {"success": False, "error": "Presets file not found"}

    import re
    base_name = re.sub(r"^__\d+__", "", req.presetName)

    with save_lock:
        with open(presets_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 🛠 Новый фильтр: удаляем только временные версии, если req.presetName начинается с "__"
        if req.presetName.startswith("__"):
            to_delete = [k for k in data if re.fullmatch(rf"__\d+__{re.escape(base_name)}", k)]
        else:
            to_delete = [k for k in data if k == base_name or k.endswith(f"__{base_name}")]

        for key in to_delete:
            del data[key]

        with open(presets_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return {"success": True, "deleted": to_delete}


@router.get("/api/presets/tree")
def list_presets_tree():
    base_path = Path("presets")

    def walk(path: Path):
        items = []
        for p in sorted(path.iterdir()):
            if p.name.startswith("."):
                continue

            if p.is_file() and p.suffix == ".json":
                items.append({
                    "name": p.stem,
                    "type": "file",
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

@router.get("/api/presets/load-file")
def load_preset_file(path: str):
    file_path = Path("presets") / path
    if not file_path.exists():
        return {"success": False, "error": "File not found"}

    return {
        "success": True,
        "inputs": json.loads(file_path.read_text(encoding="utf-8"))
    }


class SaveFileRequest(BaseModel):
    path: str
    inputs: dict

@router.post("/api/presets/save-file")
def save_preset_file(req: SaveFileRequest):
    file_path = Path("presets") / req.path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(req.inputs, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"success": True}




@router.delete("/api/presets/delete-file")
def delete_preset_file(path: str):
    file_path = Path("presets") / path
    if not file_path.exists():
        return {"success": False, "error": "File not found"}
    file_path.unlink()
    return {"success": True}
