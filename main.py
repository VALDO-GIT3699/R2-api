from fastapi import FastAPI
from app.routes import user_routes, auth_routes, pair_routes, appointment_routes, couple_note_routes
from app.database.database import engine, Base, apply_lightweight_migrations
from app.routes import memory_routes
from app.models import user, memory, couple, invitation, appointment, couple_note
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.core.settings import settings


import app.models.user

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)
apply_lightweight_migrations()

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins or ["*"],
    allow_credentials=settings.allowed_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(f"/{settings.upload_dir}", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(user_routes.router)
app.include_router(auth_routes.router)
app.include_router(pair_routes.router)
app.include_router(memory_routes.router)
app.include_router(appointment_routes.router)
app.include_router(couple_note_routes.router)

@app.get("/")
def root():
    return {"message": "API RECUER2 funcionando"}
