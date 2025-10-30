from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from api.routers import analysis as analysis_router
from api.routers import backtest as backtest_router
from api.routers import ml as ml_router
from api.routers import auth as auth_router
from api.security import get_current_user
from api.db import create_db_and_tables
from config.settings import CORS_ALLOW_ORIGINS

app = FastAPI(title="Trading SaaS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(backtest_router.router, prefix="/backtest", tags=["backtest"], dependencies=[Depends(get_current_user)])
app.include_router(analysis_router.router, prefix="/analysis", tags=["analysis"], dependencies=[Depends(get_current_user)])
app.include_router(ml_router.router, prefix="/ml", tags=["ml"], dependencies=[Depends(get_current_user)])


@app.get("/")
def read_root():
    return {"message": "Welcome to the Trading SaaS API"}
