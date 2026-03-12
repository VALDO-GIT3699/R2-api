from fastapi import FastAPI
from app.routes import user_routes, auth_routes
from app.database.database import engine, Base
from app.routes import memory_routes
from app.models import user, memory
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


import app.models.user

Base.metadata.create_all(bind=engine)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(user_routes.router)
app.include_router(auth_routes.router)
app.include_router(memory_routes.router)

@app.get("/")
def root():
    return {"message": "API RECUER2 funcionando"}
