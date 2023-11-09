from datetime import datetime
from typing import Annotated, List, Union
from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from app.common import USER_TYPE
from app.config import SHEET_CACHE_LOCATION
from app.database import connect
from app.routers.lectures import _lecture_id_exists
from app.routers.registrations import _get_reg_students_from_course_id
from app.routers.students import _get_student_from_roll_num
from app.routers.users import _verify_token
from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.comments import Comment

from app.send_email import send_attendance_sheet_email

conn = connect()
router = APIRouter(
    prefix="/attendances",
    tags=['attendances']
)
col_names = ['registration_id', 'lecture_id']

class attendanceObj(BaseModel):
    lecture_id : str
    registration_ids : List[str]

# mark attendance for lecture
@router.post("/")
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
@router.get("/students/{lecture_id}")
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
@router.get("/students/{lecture_id}/{student_roll}")
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

# get attendance stats for course
@router.get("/course/{course_id}")
def get_course_attendance(
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
    cur.execute("""
                SELECT lecture_id, lecture_date, atten_marked FROM lectures WHERE course_id = %s
                ORDER BY lecture_date DESC
                """,
                (course_id, ))
    lectures = cur.fetchall()
    cur.execute("""
                SELECT registration_id FROM course_registrations
                WHERE course_id = %s
                """,
                (course_id, ))
    regs = cur.fetchall()
    if len(lectures) == 0:
        resp_dict = {
            'reg_students': len(regs),
            'total_lectures': len(lectures),
            'message' : 'No lectures yet'
        }
        response.status_code = status.HTTP_404_NOT_FOUND
    elif len(regs) == 0:
        resp_dict = {
            'reg_students': len(regs),
            'total_lectures': len(lectures),
            'message' : 'No registered students'
        }
        response.status_code = status.HTTP_404_NOT_FOUND
    else:
        resp_dict = {
            'reg_students': len(regs),
            'total_lectures': len(lectures),
            'lectures': []
        }
        for lecture in lectures:
            cur.execute('SELECT * FROM attendances WHERE lecture_id = %s',
                        (lecture[0], ))
            present_count = len(cur.fetchall())
            resp_dict['lectures'].append({
                'lecture_id': lecture[0],
                'lecture_date': lecture[1],
                'marked': lecture[2],
                'present': present_count,
                'absent': len(regs) - present_count,
            })
        response.status_code = status.HTTP_200_OK
    cur.close()
    conn.close()
    return resp_dict

# get student attendance for course
@router.get("/course/{course_id}/{student_roll}")
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

# send filtered spreadsheet to email address
@router.get("/sheet/{course_id}")
def send_attendance_to_email(
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
    cur.execute('SELECT name, course_code FROM courses WHERE course_id = %s',
                (course_id, ))
    course = cur.fetchone()
    filename = f"/{course[0]}_{course[1]}__{datetime.now().date()}.xlsx"
    save_path = SHEET_CACHE_LOCATION + filename
    workbook = Workbook()
    sheet = workbook.active
    sheet['A1'] = "Roll Num"
    sheet.column_dimensions['A'].width = 15
    sheet['B1'] = "Student Name"
    sheet.column_dimensions['B'].width = 35
    sheet['C1'] = "%"
    sheet.column_dimensions['C'].width = 10
    sheet.freeze_panes = "B2"
    colorRule = ColorScaleRule(
        start_type='num', start_value=0, start_color='FFFF0000', # AARRGGBB
        end_type='num', end_value=1, end_color='0000FF00')
    sheet.conditional_formatting.add("D2:AZ9999", colorRule)
    cur.execute("""
                SELECT lecture_id, lecture_date, atten_marked, description FROM lectures WHERE course_id = %s
                ORDER BY lecture_date
                """,
                (course_id, ))
    lectures = cur.fetchall()
    lecture_col_dict = {}
    for idx in range(0, len(lectures)):
        if lectures[idx][2]:
            letter = chr(ord('D') + idx)
            sheet[f"{letter}1"] = lectures[idx][1]
            sheet[f"{letter}1"].comment = Comment(lectures[idx][3], 'Lecture Description')
            sheet.column_dimensions[letter].width = 13
            lecture_col_dict[lectures[idx][0]] = letter
    students = _get_reg_students_from_course_id(course_id)
    for idx in range(0, len(students)):
        row_num = idx + 2
        sheet[f'A{row_num}'] = students[idx][1]
        sheet[f'B{row_num}'] = students[idx][2]
        sheet[f'C{row_num}'] = f'=SUM(D{row_num}:AZ{row_num})/COUNT(D{row_num}:AZ{row_num})*100'
        cur.execute("""
                    SELECT lectures.lecture_id, COUNT(attendances.registration_id)
                    FROM lectures
                    INNER JOIN attendances 
                    ON lectures.lecture_id = attendances.lecture_id
                    AND attendances.registration_id = %s
                    AND lectures.course_id = %s
                    GROUP BY lectures.lecture_id
                    """,
                    (students[idx][0], course_id))
        present_lectures = cur.fetchall()
        present_lecture_dict = {}
        for row in present_lectures:
            lec_id = row[0]
            if row[1] != 0:
                present_lecture_dict[lec_id] = 1
        for lec_id in lecture_col_dict.keys():
            if lec_id in present_lecture_dict.keys():
                sheet[f'{lecture_col_dict[lec_id]}{row_num}'] = 1
            else:
                sheet[f'{lecture_col_dict[lec_id]}{row_num}'] = 0
    workbook.save(filename=save_path)
    cur.execute('SELECT email FROM user_accounts WHERE token = %s',
                (token, ))
    email = cur.fetchone()[0]
    cur.close()
    conn.close()
    send_attendance_sheet_email(email, course[0], save_path)
    import os
    os.remove(save_path)
    return {'message' : f'Attendance sheet sent to {email}!'}
