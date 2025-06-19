from fastapi import FastAPI
from api.routers import okoshi
from api.routers import ui

app = FastAPI()

app.include_router(okoshi.router)
app.include_router(ui.router)