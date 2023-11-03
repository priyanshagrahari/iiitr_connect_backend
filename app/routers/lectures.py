from datetime import date
from typing import Annotated, List, Union
from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from app.common import USER_TYPE, conv_to_dict
from app.database import connect
from app.routers.students import _get_student_from_roll_num
from app.routers.users import _verify_token


conn = connect()
router = APIRouter(
    prefix="/lectures",
    tags=['lectures']
)
col_names = ['lecture_id', 'course_id', 'lecture_date', 'atten_marked', 'description']


class lecture(BaseModel):
    course_id: str
    lecture_date: date
    atten_marked: Annotated[Union[bool, None], bool] = False
    description: str

# create one
@router.post("/create")
def add_lecture(
    data: lecture,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
): 
    if (token is None or _verify_token(token).value < USER_TYPE.SEPARATOR.value):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    cur.execute("""
                INSERT INTO lectures
                (course_id, lecture_date, atten_marked, description)
                VALUES (%s, %s, false, %s) RETURNING lecture_id
                """,
                (data.course_id, data.lecture_date, data.description))
    lecture_id = cur.fetchone()[0]
    conn.commit()
    resp_dict = dict(data)
    resp_dict['lecture_id'] = lecture_id
    resp_dict['message'] = "Lecture added successfully!"
    response.status_code = status.HTTP_201_CREATED
    cur.close()
    conn.close()
    return resp_dict

# get first n from course
# 0 for all
@router.get("/course/{course_id}/{n}")
def get_course_lectures(
    course_id: str,
    n: int,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if n == 0:
        cur.execute("""
                    SELECT lecture_id, course_id, lecture_date, atten_marked, description
                    FROM lectures WHERE course_id = %s ORDER BY lecture_date DESC
                    """,
                    (course_id, ))
    else:
        cur.execute("""
                    SELECT lecture_id, course_id, lecture_date, atten_marked, description
                    FROM lectures WHERE course_id = %s ORDER BY lecture_date DESC
                    LIMIT %s
                    """,
                    (course_id, n))
    lectures = conv_to_dict("lectures", cur.fetchall(), col_names)
    if len(lectures) > 0:
        resp_dict = lectures
        response.status_code = status.HTTP_200_OK
    else:
        resp_dict = {"message" : "No lectures found for the given course"}
        response.status_code = status.HTTP_404_NOT_FOUND
    cur.close()
    conn.close()
    return resp_dict

# get one/all lecture(s) by lecture_id
@router.get("/get/{lecture_id}")
def get_lectures(
    lecture_id: str,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if lecture_id == 'all':
        cur.execute("""
                    SELECT lecture_id, course_id, lecture_date, atten_marked, description
                    FROM lectures ORDER BY lecture_date DESC
                    """)
    else:
        cur.execute("""
                    SELECT lecture_id, course_id, lecture_date, atten_marked, description
                    FROM lectures WHERE lecture_id = %s ORDER BY lecture_date DESC
                    """,
                    (lecture_id, ))
    lectures = conv_to_dict("lectures", cur.fetchall(), col_names)
    if len(lectures) > 0:
        resp_dict = lectures
        response.status_code = status.HTTP_200_OK
    else:
        resp_dict = {"message" : "Lecture(s) not found"}
        response.status_code = status.HTTP_404_NOT_FOUND
    cur.close()
    conn.close()
    return resp_dict

def _lecture_id_exists(lecture_id: str):
    conn = connect()
    cur = conn.cursor()
    exists = False
    try:
        cur.execute("SELECT lecture_id FROM lectures WHERE lecture_id = %s",
                    (lecture_id, ))
        if len(cur.fetchall()) > 0:
            exists = True
        else:
            exists = False
    finally:
        cur.close()
        conn.close()
        return exists

# update one
@router.post("/update/{lecture_id}")
def update_lecture(
    data: lecture,
    lecture_id: str, response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token).value < USER_TYPE.SEPARATOR.value):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    # try:
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    cur.execute("SELECT lecture_id FROM lectures WHERE lecture_id = %s",
                (lecture_id, ))
    matches = cur.fetchall()
    if len(matches) > 0:
        cur.execute("""
                    UPDATE lectures
                    SET course_id = %s, lecture_date = %s, atten_marked = %s, description = %s
                    WHERE lecture_id = %s;
                    """,
                    (data.course_id, data.lecture_date, data.atten_marked, data.description,
                    lecture_id))
        if (not data.atten_marked):
            cur.execute("DELETE FROM attendances WHERE lecture_id = %s",
                        (lecture_id, ))
        conn.commit()
        resp_dict = dict(data)
        resp_dict['message'] = 'Lecture modified successfully!'
        response.status_code = status.HTTP_200_OK
    else:
        resp_dict = {"message": "Given lecture was not found!"}
        response.status_code = status.HTTP_404_NOT_FOUND
    # except:
    #     resp_dict = {"message": "Bad request?"}
    #     response.status_code = status.HTTP_400_BAD_REQUEST
    # finally:
    cur.close()
    conn.close()
    return resp_dict

# delete one/all
@router.delete("/delete/{lecture_id}")
def delete_lecture(
    lecture_id: str,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token).value < USER_TYPE.SEPARATOR.value):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    # try:
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if lecture_id != 'all':
        cur.execute("""
                    SELECT lecture_id, course_id, lecture_date, atten_marked, description
                    FROM lectures WHERE lecture_id = %s
                    """,
                    (lecture_id, ))
        row = conv_to_dict("lectures", cur.fetchall(), col_names)
        if len(row['lectures']) > 0:
            cur.execute("DELETE FROM lectures WHERE lecture_id = %s",
                        (lecture_id, ))
            resp_dict = dict(row)
            resp_dict["message"] = "Lecture deleted successfully!"
            response.status_code = status.HTTP_200_OK
        else:
            resp_dict = {"message": "Lecture not found"}
            response.status_code = status.HTTP_404_NOT_FOUND
    else:
        cur.execute("""
                    SELECT lecture_id, course_id, lecture_date, atten_marked, description
                    FROM lectures
                    """)
        rows = conv_to_dict("lectures", cur.fetchall(), col_names)
        cur.execute("DELETE FROM lectures")
        resp_dict = dict(rows)
        resp_dict["message"] = "All lectures deleted"
        response.status_code = status.HTTP_200_OK
    conn.commit()
    # except:
    #     resp_dict = {"message": "Bad request?"}
    #     response.status_code = status.HTTP_400_BAD_REQUEST
    # finally:
    cur.close()
    conn.close()
    return resp_dict
