from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI(title="DataPress API POC")

# 👉 Autoriser les appels depuis le front (localhost:8081)
origins = [
    "http://localhost:8081",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # tu peux mettre ["*"] en dev si tu veux
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "api",
        "ts": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}
