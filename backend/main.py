from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from routes import categories, chat, dashboard, goals, holdings, loans, transactions, upload, uploads

app = FastAPI(title="Personal Finance AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(uploads.router)
app.include_router(loans.router)
app.include_router(goals.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(holdings.router)
app.include_router(dashboard.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
