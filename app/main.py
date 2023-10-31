from fastapi import FastAPI

from app.routers import users, students, encodings, professors, courses, lectures, registrations


app = FastAPI()

app.include_router(users.router)
app.include_router(students.router)
app.include_router(encodings.router)
app.include_router(professors.router)
app.include_router(courses.router)
app.include_router(lectures.router)
app.include_router(registrations.router)

@app.get("/")
async def root():
    return {"message" : "Welcome to the IIITR Connect API"}