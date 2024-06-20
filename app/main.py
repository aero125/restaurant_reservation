from fastapi import FastAPI
from app.api import users, promocodes, tables, reservations, test_data
from app.init_db import init_db

app = FastAPI()

init_db()

app.include_router(users.router)
app.include_router(promocodes.router)
app.include_router(tables.router)
app.include_router(reservations.router)
app.include_router(test_data.router)
