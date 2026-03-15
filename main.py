from fastapi import FastAPI, HTTPException
from app.routes import user_routes, auth_routes, pair_routes, appointment_routes, couple_note_routes
from app.database.database import engine, Base, apply_lightweight_migrations
from app.routes import memory_routes
from app.models import user, memory, couple, invitation, appointment, couple_note, memory_like, couple_note_like
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.core.settings import settings


import app.models.user

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
PLACEHOLDER_IMAGE_PATH = Path(settings.upload_dir) / "_placeholder.svg"

if not PLACEHOLDER_IMAGE_PATH.exists():
        PLACEHOLDER_IMAGE_PATH.write_text(
                """
<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='800' viewBox='0 0 1200 800'>
    <defs>
        <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
            <stop offset='0%' stop-color='#F8E8EE'/>
            <stop offset='100%' stop-color='#F3EDF8'/>
        </linearGradient>
    </defs>
    <rect width='1200' height='800' fill='url(#g)'/>
    <circle cx='600' cy='340' r='110' fill='#E0D2DE'/>
    <rect x='360' y='500' width='480' height='36' rx='18' fill='#C9A4B7'/>
    <rect x='450' y='560' width='300' height='20' rx='10' fill='#D9BED0'/>
</svg>
                """.strip(),
                encoding="utf-8",
        )

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


@app.get(f"/{settings.upload_dir}/{{file_name:path}}")
def serve_upload(file_name: str):
    # Prevent path traversal and serve a graceful placeholder if file is missing.
    root = Path(settings.upload_dir).resolve()
    target = (root / file_name).resolve()

    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Ruta de archivo invalida")

    if target.exists() and target.is_file():
        return FileResponse(path=target)

    return FileResponse(path=PLACEHOLDER_IMAGE_PATH, media_type="image/svg+xml")

app.include_router(user_routes.router)
app.include_router(auth_routes.router)
app.include_router(pair_routes.router)
app.include_router(memory_routes.router)
app.include_router(appointment_routes.router)
app.include_router(couple_note_routes.router)

@app.get("/")
def root():
    return {"message": "API RECUER2 funcionando"}
