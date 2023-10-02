from fastapi import FastAPI

from app.routers import users
from app.routers import students

app = FastAPI()

app.include_router(users.router)
app.include_router(students.router)

@app.get("/")
async def root():
    return {"message" : "Welcome to the IIITR Connect API"}