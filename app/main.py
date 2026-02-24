from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.totem import router as totem_router
from app.routes.api import router as api_router
from app.routes.dashboard import router as web_router

app = FastAPI()

# static assets
app.mount("/static", StaticFiles(directory="static"), name="static")

# routers
app.include_router(totem_router)
app.include_router(api_router)
app.include_router(web_router)