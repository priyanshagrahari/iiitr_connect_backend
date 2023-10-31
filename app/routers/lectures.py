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

class attendanceObj(BaseModel):
    lecture_id : str
    registration_ids : List[str]

# mark attendance for lecture
@router.post("/attend")
def mark_attendance(
    data: attendanceObj,
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
    if (_lecture_id_exists(data.lecture_id)):
        cur.execute("DELETE FROM attendances WHERE lecture_id = %s",
                    (data.lecture_id, ))
        for registration_id in data.registration_ids:
            cur.execute("""
                        INSERT INTO attendances 
                        (registration_id, lecture_id)
                        VALUES (%s, %s)
                        """,
                        (registration_id, data.lecture_id))
        cur.execute("""
                    UPDATE lectures
                    SET atten_marked = true
                    WHERE lecture_id = %s;
                    """,
                    (data.lecture_id, ))
        conn.commit()
        response.status_code = status.HTTP_200_OK
        resp_dict = {"message" : "Attendance recorded successfully!"}
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        resp_dict = {"message" : "Lecture not found"}
    cur.close()
    conn.close()
    return resp_dict

# get students present on a particular lecture
@router.get("/attend/{lecture_id}")
def get_attendance(
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
    cur.execute("SELECT atten_marked FROM lectures WHERE lecture_id = %s",
                (lecture_id, ))
    row = cur.fetchone()
    if (row != None and row[0]): # if attendance marked
        cur.execute("SELECT registration_id FROM attendances WHERE lecture_id = %s",
                    (lecture_id, ))
        students = []
        for reg_id in [r[0] for r in cur.fetchall()]:
            cur.execute("""
                        SELECT student_roll FROM course_registrations 
                        WHERE registration_id = %s
                        """,
                        (reg_id, ))
            students.append(_get_student_from_roll_num(cur.fetchone()[0]))
        resp_dict = {"students" : students}
        response.status_code = status.HTTP_200_OK
    else:
        resp_dict = {'message' : 'Attendance not marked yet'}
        response.status_code = status.HTTP_404_NOT_FOUND
    cur.close()
    conn.close()
    return resp_dict

# check if student was present on a certain lecture
@router.get("/present/{lecture_id}/{student_roll}")
def get_stud_present(
    lecture_id: str,
    student_roll: str,
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
    cur.execute("SELECT atten_marked, course_id FROM lectures WHERE lecture_id = %s",
                (lecture_id, ))
    row = cur.fetchone()
    marked, course_id = row[0], row[1]
    if (marked): # if attendance marked
        cur.execute("""
                    SELECT registration_id FROM course_registrations
                    WHERE course_id = %s AND student_roll = %s
                    """,
                    (course_id, student_roll, ))
        registration_id = cur.fetchone()
        if (registration_id == None):
            resp_dict = {'message' : 'Student not registered'}
            response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            cur.execute("""
                        SELECT * FROM attendances 
                        WHERE lecture_id = %s AND registration_id = %s
                        """,
                        (lecture_id, registration_id[0]))
            row = cur.fetchone()
            resp_dict = {'present' : row != None, 'message' : 'Record found'}
            response.status_code = status.HTTP_200_OK
    else:
        resp_dict = {'present' : None, 'message' : 'Record not found'}
        response.status_code = status.HTTP_404_NOT_FOUND
    cur.close()
    conn.close()
    return resp_dict

# get student attendance for course
@router.get("/attend/{course_id}/{student_roll}")
def get_stud_attendance(
    course_id: str,
    student_roll: str,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT lecture_id, atten_marked FROM lectures WHERE course_id = %s",
                (course_id, ))
    lectures = cur.fetchall()
    if len(lectures) > 0:
        cur.execute("""
                    SELECT registration_id FROM course_registrations 
                    WHERE student_roll = %s AND course_id = %s
                    """,
                    (student_roll, course_id))
        registration_id = cur.fetchone()[0]
        present_count = 0
        absent_count = 0
        not_marked_count = 0
        for lecture in lectures:
            lecture_id = lecture[0]
            atten_marked = lecture[1]
            if atten_marked:
                cur.execute("""
                        SELECT * FROM attendances 
                        WHERE lecture_id = %s AND registration_id = %s
                        """,
                        (lecture_id, registration_id))
                row = cur.fetchone()
                if row != None:
                    present_count += 1
                else:
                    absent_count += 1
            else:
                not_marked_count += 1
        resp_dict = {
            "present" : present_count,
            "absent" : absent_count,
            "not_marked" : not_marked_count,
            "total" : len(lectures),
            "course_id" : course_id,
            "registration_id" : registration_id,
            "student_roll" : student_roll,
        }
        response.status_code = status.HTTP_200_OK
    else:
        resp_dict = {
            "total" : 0,
            "message" : "No lectures have occured yet"
        }
        response.status_code = status.HTTP_404_NOT_FOUND
    cur.close()
    conn.close()
    return resp_dict
