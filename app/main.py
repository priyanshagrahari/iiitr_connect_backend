from fastapi import FastAPI

from app.routers import users, students, encodings, professors, courses


app = FastAPI()

app.include_router(users.router)
app.include_router(students.router)
app.include_router(encodings.router)
app.include_router(professors.router)
app.include_router(courses.router)

@app.get("/")
async def root():
    return {"message" : "Welcome to the IIITR Connect API"}