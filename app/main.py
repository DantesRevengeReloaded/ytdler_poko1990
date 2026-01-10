from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
import logging

from app.api.routes import downloads, spotify, stats
from app.core.config import get_settings
from app.db.session import init_pool
from app.services.db_manager import init_db

settings = get_settings()

# Set up logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '..', 'logs', 'app.log')),
        logging.StreamHandler()
    ]
)

app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def on_startup():
    init_pool()
    init_db()


app.include_router(downloads.router)
app.include_router(spotify.router)
app.include_router(stats.router)

base_dir = os.path.dirname(__file__)
static_dir = os.path.join(base_dir, "web", "static")
images_dir = os.path.abspath(os.path.join(base_dir, "..", "images"))
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/images", StaticFiles(directory=images_dir), name="images")


@app.get("/")
def index():
    return FileResponse(os.path.join(static_dir, "index.html"))
