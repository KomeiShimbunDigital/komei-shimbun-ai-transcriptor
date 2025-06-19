from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
from pathlib import Path
from starlette.staticfiles import StaticFiles

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
static_dir = BASE_DIR / "static"
router.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

"""
HTMLを返す
"""
@router.get("/ui", response_class=HTMLResponse)
def index():
    return FileResponse(static_dir / "index.html")