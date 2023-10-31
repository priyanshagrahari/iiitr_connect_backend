from datetime import datetime
from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from app.database import connect
from app.common import conv_to_dict, USER_TYPE
from typing import Annotated, List, Union
from app.routers.courses import _get_course_from_id, col_names as courses_cols
from app.routers.professors import _email_prefix_exists
from app.routers.students import _get_student_from_roll_num, _roll_num_exists, student
from app.routers.users import _verify_token

conn = connect()
router = APIRouter(
    prefix="/registrations",
    tags=["registrations"]
)
col_names = ['registration_id', 'course_id', 'student_roll']

class registration(BaseModel):
    course_id: str
    student_roll: str

# toggle registration for a course/student pair
@router.post("/reg")
def toggle_course_reg(
    data : registration,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    # try:
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    cur.execute("SELECT course_id FROM courses WHERE course_id = %s",
                (data.course_id, ))
    matches = cur.fetchall()
    if len(matches) > 0 and _roll_num_exists(data.student_roll):
        # try to find given pair
        cur.execute("""
                    SELECT registration_id FROM course_registrations
                    WHERE course_id = %s AND student_roll = %s
                    """,
                    (data.course_id, data.student_roll))
        reg_id = cur.fetchone()
        if reg_id != None: # entry exists, remove it
            cur.execute("""
                        DELETE FROM course_registrations
                        WHERE registration_id = %s
                        """,
                        (reg_id[0], ))
            conn.commit()
            resp_dict = {'message' : 'Course dropped successfully!'}
        else:
            cur.execute("""
                        INSERT INTO course_registrations
                        (course_id, student_roll)
                        VALUES (%s, %s)
                        """,
                        (data.course_id, data.student_roll))
            conn.commit()
            resp_dict = {'message' : 'Registration successful!'}
        response.status_code = status.HTTP_200_OK
    else:
        resp_dict = {"message": "Given course or student was not found!"}
        response.status_code = status.HTTP_404_NOT_FOUND
    # except:
    #     resp_dict = {"message": "Bad request?"}
    #     response.status_code = status.HTTP_400_BAD_REQUEST
    # finally:
    cur.close()
    conn.close()
    return resp_dict

# get number of registered students
@router.get("/numreg/{course_id}")
def get_num_reg_students(
    course_id: str,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM course_registrations WHERE course_id = %s",
                (course_id, ))
    resp_dict = {'count' : len(cur.fetchall())}
    return resp_dict

# retrieve student courses
@router.get("/stud/{roll_num}")
def get_stud_courses(
    roll_num: str,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    # try:
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if _roll_num_exists(roll_num):
        cur.execute("""
                    SELECT course_id FROM course_registrations 
                    WHERE student_roll = %s
                    """,
                    (roll_num, ))
        course_ids = cur.fetchall()
        if len(course_ids) > 0:
            courses = []
            for course_id in course_ids:
                courses.append(_get_course_from_id(course_id[0]))
            for course in courses:
                course['is_running'] = (
                    course['end_date'] >= datetime.today().date())
            resp_dict = {'courses' : courses}
            response.status_code = status.HTTP_200_OK
        else:
            resp_dict = {"message": "No courses found"}
            response.status_code = status.HTTP_404_NOT_FOUND
    else:
        resp_dict = {"message": "Roll num not found"}
        response.status_code = status.HTTP_404_NOT_FOUND
    # except:
    #     resp_dict = {"message" : "Bad request?"}
    #     response.status_code = status.HTTP_400_BAD_REQUEST
    # finally:
    cur.close()
    conn.close()
    return resp_dict

# get courses available for registration for a student
@router.get("/avareg/{student_roll}")
def get_ava_courses(
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
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        cur.execute("""
                    SELECT course_id, course_code, name, begin_date, end_date, accepting_reg, description
                    FROM courses WHERE accepting_reg = true AND end_date >= current_date
                    ORDER BY name ASC
                    """)
        courses = conv_to_dict("courses", cur.fetchall(), courses_cols)
        cur.execute("SELECT course_id FROM course_registrations WHERE student_roll = %s",
                    (student_roll, ))
        course_ids = [cid[0] for cid in cur.fetchall()]
        print(course_ids)
        courses['courses'] = [course for course in courses['courses'] if course['course_id'] not in course_ids]
        if courses['courses'] != None and len(courses['courses']) > 0:
            resp_dict = courses
            response.status_code = status.HTTP_200_OK
        else:
            resp_dict = {"message": "Course not found"}
            response.status_code = status.HTTP_404_NOT_FOUND
    except:
        resp_dict = {"message" : "Bad request?"}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict

# get students registered for a course
@router.get("/cour/{course_id}")
def get_reg_students(
    course_id: str,
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
    cur.execute("SELECT registration_id, student_roll FROM course_registrations WHERE course_id = %s",
                (course_id, ))
    rows = cur.fetchall()
    resp_dict = {'registrations' : []}
    for row in rows:
        obj = {}
        obj['student'] = _get_student_from_roll_num(row[1])
        obj['registration_id'] = row[0]
        resp_dict['registrations'].append(obj)
    response.status_code = status.HTTP_200_OK
    return resp_dict
