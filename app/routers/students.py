from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from app.database import connect
from app.common import conv_to_dict
from typing import List

conn = connect()
router = APIRouter(
    prefix="/students",
    tags=["students"]
)

class student(BaseModel):
    roll_num: str
    name: str

# create one
@router.post("/")
def add_student(data: student, response: Response):
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        valid = len(data.roll_num) == 9
        if valid:
            cur.execute(f"INSERT INTO student (roll_num, name) VALUES ('{data.roll_num}', '{data.name}')")
            resp_dict = data
            response.status_code = status.HTTP_201_CREATED
        else:
            resp_dict = {"message" : "Invalid data"}
            response.status_code = status.HTTP_400_BAD_REQUEST
    except:
        resp_dict = {"message" : "Roll number may already exist"}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.commit()
        return resp_dict

# retrieve one/all
@router.get("/{roll_num}")
def get_students(roll_num: str, response: Response):
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        col_names = ['roll_num', 'name']
        if roll_num != 'all':
            cur.execute(f"SELECT roll_num, name FROM student WHERE roll_num = '{roll_num}'")
        else:
            cur.execute("SELECT roll_num, name FROM student ORDER BY roll_num ASC")
        students = conv_to_dict("students", cur.fetchall(), col_names)
        if len(students) > 0:
            resp_dict = students
            response.status_code = status.HTTP_200_OK
        else:
            resp_dict = {"message" : "Roll number not found"}
            response.status_code = status.HTTP_404_NOT_FOUND
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        return resp_dict

# update one
@router.post("/{roll_num}")
def update_student(data: student, roll_num: str, response: Response):
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        cur.execute(f"SELECT * FROM student WHERE student.roll_num = '{roll_num}'")
        matches = cur.fetchall()
        if len(matches) == 1:
            valid = len(data.roll_num) == 9
            if valid:
                cur.execute(f"DELETE FROM student WHERE roll_num = '{roll_num}'")
                cur.execute(f"INSERT INTO student (roll_num, name) VALUES ('{data.roll_num}', '{data.name}')")
                resp_dict = data
                response.status_code = status.HTTP_200_OK
            else:
                resp_dict = {}
                response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            resp_dict = {"message" : "Given roll number was not found!"}
            response.status_code = status.HTTP_404_NOT_FOUND
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.commit()
        return resp_dict


# delete one/all
@router.delete("/{roll_num}")
def delete_student(roll_num: str, response: Response):
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        col_names = ['roll_num', 'name']
        if roll_num != 'all':
            valid = len(roll_num) == 9
            if valid:
                cur.execute(f"SELECT roll_num, name FROM student WHERE roll_num = '{roll_num}'")
                row = conv_to_dict("students", cur.fetchall(), col_names)
                if len(row) > 0:
                    cur.execute(f"DELETE FROM student WHERE roll_num = '{roll_num}'")
                    resp_dict = row
                    response.status_code = status.HTTP_200_OK
                else:
                    resp_dict = {}
                    response.status_code = status.HTTP_404_NOT_FOUND
            else:
                resp_dict = {}
                response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            cur.execute("SELECT roll_num, name FROM student")
            rows = conv_to_dict("students", cur.fetchall(), col_names)
            cur.execute("DELETE FROM student")
            resp_dict = rows
            response.status_code = status.HTTP_200_OK
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.commit()
        return resp_dict