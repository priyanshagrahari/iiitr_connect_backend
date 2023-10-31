from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from app.database import connect
from app.common import conv_to_dict, USER_TYPE
from typing import Annotated, List, Union
from app.routers.professors import _email_prefix_exists
from app.routers.users import _verify_token

from datetime import datetime, date

conn = connect()
router = APIRouter(
    prefix="/courses",
    tags=["courses"]
)
col_names = ['course_id', 'course_code', 'name',
             'begin_date', 'end_date', 'accepting_reg', 'description']

class course(BaseModel):
    course_code: str
    name: str
    begin_date: date
    end_date: date
    accepting_reg: bool = True
    description: str
    profs: List[str]

# create one
@router.post("/create")
def add_course(
    data: course,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token).value < USER_TYPE.SEPARATOR.value):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        cur.execute("""
                    INSERT INTO courses 
                    (course_code, name, begin_date, end_date, accepting_reg, description) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (data.course_code, data.name, data.begin_date, data.end_date,
                        data.accepting_reg, data.description))
        conn.commit()
        cur.execute("""
                    SELECT course_id FROM courses 
                    WHERE course_code = %s AND begin_date = %s
                    """,
                    (data.course_code, data.begin_date))
        course_id = cur.fetchone()[0]
        for prefix in data.profs:
            cur.execute("""
                        INSERT INTO profs_courses 
                        (prof_prefix, course_id)
                        VALUES (%s, %s)
                        """,
                        (prefix, course_id))
        conn.commit()
        resp_dict = dict(data)
        resp_dict['message'] = "Course added successfully!"
        response.status_code = status.HTTP_201_CREATED
    except:
        resp_dict = {"message" : "Course code and begin date must be a unique tuple"}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict

def _course_id_exists(course_id: str):
    conn = connect()
    cur = conn.cursor()
    exists = False
    try:
        cur.execute("SELECT course_id FROM courses WHERE course_id = %s",
                    (course_id, ))
        if len(cur.fetchall()) > 0:
            exists = True
        else:
            exists = False
    finally:
        cur.close()
        conn.close()
        return exists

# retrieve one/all
@router.get("/get/{course_id}")
def get_course(
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
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if course_id != 'all':
            cur.execute("""
                        SELECT course_id, course_code, name, begin_date, end_date, accepting_reg, description
                        FROM courses WHERE course_id = %s
                        """,
                        (course_id, ))
        else:
            cur.execute("""
                        SELECT course_id, course_code, name, begin_date, end_date, accepting_reg, description
                        FROM courses ORDER BY name ASC
                        """)
        courses = conv_to_dict("courses", cur.fetchall(), col_names)
        for course in courses['courses']:
            cur.execute("SELECT prof_prefix FROM profs_courses WHERE course_id = %s",
                        (course['course_id'], ))
            profs = [i[0] for i in cur.fetchall()]
            course['profs'] = profs
        if len(courses['courses']) > 0:
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

def _get_course_from_id(course_id: str):
    if _course_id_exists(course_id):
        conn = connect()
        cur = conn.cursor()
        cur.execute("""
                    SELECT course_id, course_code, name, begin_date, end_date, accepting_reg, description
                    FROM courses WHERE course_id = %s
                    """,
                    (course_id, ))
        course_dict = conv_to_dict("course", cur.fetchall(), col_names)
        course = course_dict['course'][0]
        cur.close()
        conn.close()
        return course
    else:
        return None

# update one
@router.post("/update/{course_id}")
def update_course(
    data: course,
    course_id: str, response: Response,
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
    cur.execute("SELECT course_id FROM courses WHERE course_id = %s",
                (course_id, ))
    matches = cur.fetchall()
    if len(matches) > 0:
        cur.execute("""
                    UPDATE courses
                    SET course_code = %s, name = %s, begin_date = %s, 
                    end_date = %s, accepting_reg = %s, description = %s
                    WHERE course_id = %s;
                    """,
                    (data.course_code, data.name, data.begin_date,
                        data.end_date, data.accepting_reg, data.description,
                        course_id))
        conn.commit()
        cur.execute("DELETE FROM profs_courses WHERE course_id = %s", (course_id, ))
        for prefix in data.profs:
            cur.execute("""
                        INSERT INTO profs_courses
                        (prof_prefix, course_id)
                        VALUES (%s, %s)
                        """,
                        (prefix, course_id))
        conn.commit()
        resp_dict = dict(data)
        resp_dict['message'] = 'Course modified successfully!'
        response.status_code = status.HTTP_200_OK
    else:
        resp_dict = {"message": "Given course was not found!"}
        response.status_code = status.HTTP_404_NOT_FOUND
    # except:
    #     resp_dict = {"message": "Bad request?"}
    #     response.status_code = status.HTTP_400_BAD_REQUEST
    # finally:
    cur.close()
    conn.close()
    return resp_dict

# delete one/all
@router.delete("/delete/{course_id}")
def delete_course(
    course_id: str,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token).value < USER_TYPE.SEPARATOR.value):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if course_id != 'all':
            cur.execute("""
                        SELECT course_id, course_code, name, begin_date, end_date, accepting_reg, description
                        FROM courses WHERE course_id = %s
                        """,
                        (course_id, ))
            row = conv_to_dict("courses", cur.fetchall(), col_names)
            if len(row['courses']) > 0:
                cur.execute("DELETE FROM courses WHERE course_id = %s",
                            (course_id, ))
                resp_dict = dict(row)
                resp_dict["message"] = "Course deleted successfully!"
                response.status_code = status.HTTP_200_OK
            else:
                resp_dict = {"message": "Course not found"}
                response.status_code = status.HTTP_404_NOT_FOUND
        else:
            cur.execute("""
                        SELECT course_id, course_code, name, begin_date, end_date, accepting_reg, description
                        FROM courses
                        """)
            rows = conv_to_dict("courses", cur.fetchall(), col_names)
            cur.execute("DELETE FROM courses")
            resp_dict = dict(rows)
            resp_dict["message"] = "All courses deleted"
            response.status_code = status.HTTP_200_OK
        conn.commit()
    except:
        resp_dict = {"message": "Bad request?"}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict

# retrieve prof courses
@router.get("/prof/{email_prefix}")
def get_prof_courses(
    email_prefix: str,
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
    if _email_prefix_exists(email_prefix):
        cur.execute("""
                    SELECT course_id FROM profs_courses 
                    WHERE prof_prefix = %s
                    """,
                    (email_prefix, ))
        course_ids = cur.fetchall()
        courses = []
        for course_id in course_ids:
            cur.execute("""
                        SELECT course_id, course_code, name, begin_date, end_date, accepting_reg, description
                        FROM courses WHERE course_id = %s
                        """,
                        (course_id[0], ))
            courses.append(cur.fetchone())
        if len(courses) > 0:
            courses = conv_to_dict("courses", courses, col_names)
            for course in courses['courses']:
                course['is_running'] = (
                    course['end_date'] >= datetime.today().date())
                cur.execute("SELECT prof_prefix FROM profs_courses WHERE course_id = %s",
                            (course['course_id'], ))
                profs = [i[0] for i in cur.fetchall()]
                course['profs'] = profs
            resp_dict = courses
            response.status_code = status.HTTP_200_OK
        else:
            resp_dict = {"message": "No courses found"}
            response.status_code = status.HTTP_404_NOT_FOUND
    else:
        resp_dict = {"message": "Email prefix not found"}
        response.status_code = status.HTTP_404_NOT_FOUND
    # except:
    #     resp_dict = {"message" : "Bad request?"}
    #     response.status_code = status.HTTP_400_BAD_REQUEST
    # finally:
    cur.close()
    conn.close()
    return resp_dict
