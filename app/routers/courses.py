from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from app.database import connect
from app.common import conv_to_dict, USER_TYPE
from typing import Annotated, List, Union
from app.routers.users import _verify_token

from datetime import date

conn = connect()
router = APIRouter(
    prefix="/courses",
    tags=["courses"]
)
col_names = ['course_code', 'name', 'begin_date', 'end_date', 'accepting_reg', 'description']

class course(BaseModel):
    course_code: str
    name: str
    begin_date: date
    end_date: date
    accepting_reg: bool = True
    desc: str
    profs: List[str]

# create one
@router.post("/")
def add_course(
    data: course, 
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
        cur.execute("""
                    INSERT INTO courses 
                    (course_code, name, begin_date, end_date, accepting_reg, desc) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """, 
                    (data.course_code, data.name, data.begin_date, data.end_date, 
                     data.accepting_reg, data.desc))
        for prefix in data.profs:
            cur.execute("""
                        INSERT INTO profs_courses 
                        (prof_prefix, course_code)
                        VALUES (%s, %s)
                        """,
                        (prefix, data.course_code))            
        conn.commit()
        resp_dict = data
        response.status_code = status.HTTP_201_CREATED
    except:
        resp_dict = {"message" : "Course code may already exist or prof prefix may be invalid"}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict

def _course_code_exists(course_code: str):
    conn = connect()
    cur = conn.cursor()
    exists = False
    try:
        cur.execute("SELECT course_code FROM courses WHERE course_code = %s",
                    (course_code, ))
        if len(cur.fetchall()) > 0:
            exists = True
        else:
            exists = False
    finally:
        cur.close()
        conn.close()
        return exists

# retrieve one/all
@router.get("/{course_code}")
def get_course(
    course_code: str,
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
        if course_code != 'all':
            cur.execute("""
                        SELECT course_code, name, begin_date, end_date, accepting_reg, desc
                        FROM courses WHERE course_code = %s
                        """,
                        (course_code, ))
        else:
            cur.execute("""
                        SELECT course_code, name, begin_date, end_date, accepting_reg, desc 
                        FROM courses ORDER BY name ASC
                        """)
        courses = conv_to_dict("courses", cur.fetchall(), col_names)
        if len(courses) > 0:
            resp_dict = courses
            response.status_code = status.HTTP_200_OK
        else:
            resp_dict = {"message" : "Course code not found"}
            response.status_code = status.HTTP_404_NOT_FOUND
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict

# update one
@router.post("/{course_code}")
def update_course(
    data: course, 
    course_code: str, response: Response,
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
        cur.execute("SELECT course_code FROM courses WHERE course_code = %s",
                    (course_code, ))
        matches = cur.fetchall()
        if len(matches) > 0:
                cur.execute("""
                            UPDATE courses
                            SET course_code = %s, name = %s, begin_date = %s, 
                            end_date = %s, accepting_reg = %s, desc = %s
                            WHERE course_code = %s;
                            """,
                            (data.course_code, data.name, data.begin_date,
                             data.end_date, data.accepting_reg, data.desc,
                             course_code))
                conn.commit()
                resp_dict = data
                response.status_code = status.HTTP_200_OK
        else:
            resp_dict = {"message" : "Given course code was not found!"}
            response.status_code = status.HTTP_404_NOT_FOUND
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict


# delete one/all
@router.delete("/{course_code}")
def delete_course(
    course_code: str, 
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
        if course_code != 'all':
            cur.execute("""
                        SELECT course_code, name, begin_date, end_date, accepting_reg, desc 
                        FROM courses WHERE course_code = %s
                        """,
                        (course_code, ))
            row = conv_to_dict("courses", cur.fetchall(), col_names)
            if len(row) > 0:
                cur.execute("DELETE FROM courses WHERE course_code = %s",
                            (course_code, ))
                resp_dict = row
                response.status_code = status.HTTP_200_OK
            else:
                resp_dict = {}
                response.status_code = status.HTTP_404_NOT_FOUND
        else:
            cur.execute("""
                        SELECT course_code, name, begin_date, end_date, accepting_reg, desc 
                        FROM courses
                        """)
            rows = conv_to_dict("courses", cur.fetchall(), col_names)
            cur.execute("DELETE FROM courses")
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