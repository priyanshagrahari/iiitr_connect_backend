from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from app.database import connect
from app.common import conv_to_dict, USER_TYPE
from typing import Annotated, Union
from app.routers.users import _verify_token

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
def add_student(
    data: student, 
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token).value < USER_TYPE.SEPARATOR.value):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        valid = len(data.roll_num) == 9
        if valid:
            cur.execute("INSERT INTO students (roll_num, name) VALUES (%s, %s)", 
                        (data.roll_num, data.name))
            conn.commit()
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
        conn.close()
        return resp_dict

def _roll_num_exists(roll_num: str):
    conn = connect()
    cur = conn.cursor()
    exists = False
    try:
        cur.execute("SELECT roll_num FROM students WHERE roll_num = %s",
                    (roll_num, ))
        if len(cur.fetchall()) > 0:
            exists = True
        else:
            exists = False
    finally:
        cur.close()
        conn.close()
        return exists

# retrieve one/all
@router.get("/{roll_num}")
def get_student(
    roll_num: str, 
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    user_type = _verify_token(token)
    if ((token is None or _verify_token(token) == USER_TYPE.INVALID) or
        (roll_num == 'all' and user_type.value < USER_TYPE.SEPARATOR)):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        col_names = ['roll_num', 'name']
        if roll_num != 'all':
            cur.execute("SELECT roll_num, name FROM students WHERE roll_num = %s",
                        (roll_num, ))
        else:
            cur.execute("SELECT roll_num, name FROM students ORDER BY roll_num ASC")
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
        conn.close()
        return resp_dict

# update one
@router.post("/{roll_num}")
def update_student(
    data: student, 
    roll_num: str, response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token).value < USER_TYPE.SEPARATOR.value):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        cur.execute("SELECT roll_num FROM students WHERE students.roll_num = %s",
                    (roll_num, ))
        matches = cur.fetchall()
        if len(matches) > 0:
            valid = len(data.roll_num) == 9
            if valid:
                cur.execute("""
                            UPDATE students
                            SET roll_num = %s, name = %s
                            WHERE roll_num = %s
                            """,
                            (data.roll_num, data.name, roll_num))
                conn.commit()
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
        conn.close()
        return resp_dict


# delete one/all
@router.delete("/{roll_num}")
def delete_student(
    roll_num: str, 
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token).value < USER_TYPE.SEPARATOR.value):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        col_names = ['roll_num', 'name']
        if roll_num != 'all':
            valid = len(roll_num) == 9
            if valid:
                cur.execute("SELECT roll_num, name FROM students WHERE roll_num = %s",
                            (roll_num, ))
                row = conv_to_dict("students", cur.fetchall(), col_names)
                if len(row) > 0:
                    cur.execute("DELETE FROM students WHERE roll_num = %s",
                                (roll_num, ))
                    resp_dict = row
                    response.status_code = status.HTTP_200_OK
                else:
                    resp_dict = {}
                    response.status_code = status.HTTP_404_NOT_FOUND
            else:
                resp_dict = {}
                response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            cur.execute("SELECT roll_num, name FROM students")
            rows = conv_to_dict("students", cur.fetchall(), col_names)
            cur.execute("DELETE FROM students")
            resp_dict = rows
            response.status_code = status.HTTP_200_OK
        conn.commit()
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict