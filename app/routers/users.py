from typing import Annotated, Union
import cv2
from fastapi import APIRouter, Header, Response, UploadFile, status
import numpy
from pydantic import BaseModel
from app.database import connect
from app.send_email import send_email_otp
from app.common import user_type_to_str, is_email_valid, conv_to_dict, USER_TYPE
import pandas as pd

import random
import uuid
from time import time
from datetime import datetime, timezone

token_validity = 15 # generated tokens valid for days
router = APIRouter(
    prefix="/users",
    tags=["users"]
)

class user(BaseModel):
    email: str
    user_type: int = 0

# create one
@router.post("/create")
def create_user(
    data: user, 
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) != USER_TYPE.ADMIN):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        valid = is_email_valid(data.email) and user_type_to_str(data.user_type) != None
        if valid:
            cur.execute("INSERT INTO user_accounts (email,user_type) VALUES (%s, %s)", 
                        (data.email, data.user_type))
            conn.commit()
            resp_dict = data
            response.status_code = status.HTTP_201_CREATED
        else:
            resp_dict = {"message" : "Invalid data"}
            response.status_code = status.HTTP_400_BAD_REQUEST
    except:
        resp_dict = {"message" : "Given email may already exist"}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict

class student(BaseModel):
    roll_num: str
    name: str

@router.post("/create_student")
def create_student_user(
    data: student,
    response: Response,
):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO user_accounts (email,user_type) VALUES (%s, %s)", 
                (f"{data.roll_num}@iiitr.ac.in", 0))
    cur.execute("INSERT INTO students (roll_num, name) VALUES (%s, %s)", 
                (data.roll_num, data.name))
    conn.commit()
    resp_dict = data
    response.status_code = status.HTTP_201_CREATED
    cur.close()
    conn.close()
    return resp_dict

# retrieve one/all
@router.get("/get/{email}")
def get_users(
    email: str, 
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) != USER_TYPE.ADMIN):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        col_names = ['email', 'user_type']
        if email != 'all':
            cur.execute("SELECT email, user_type FROM user_accounts WHERE email = %s", 
                        (email, ))
        else:
            cur.execute("SELECT email, user_type FROM user_accounts ORDER BY email ASC")
        users = conv_to_dict("user_accounts", cur.fetchall(), col_names)
        if len(users) > 0:
            resp_dict = users
            response.status_code = status.HTTP_200_OK
        else:
            resp_dict = {"message" : "Email not found"}
            response.status_code = status.HTTP_404_NOT_FOUND
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict

# update one
@router.post("/update/{email}")
def update_user(
    data: user, 
    email: str, 
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) != USER_TYPE.ADMIN):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        cur.execute("SELECT email FROM user_accounts WHERE email = %s", 
                    (email, ))
        matches = cur.fetchall()
        if len(matches) > 0:
            valid = is_email_valid(data.email) and user_type_to_str(data.user_type) != None
            if valid:
                cur.execute("UPDATE user_accounts SET email = %s, user_type = %s WHERE email = %s",
                            (data.email, data.user_type, email))
                conn.commit()
                resp_dict = data
                response.status_code = status.HTTP_200_OK
            else:
                resp_dict = {"message" : "Given email is invalid"}
                response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            resp_dict = {"message" : "Given email was not found!"}
            response.status_code = status.HTTP_404_NOT_FOUND
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict


# delete one/all
@router.delete("/delete/{email}")
def delete_user(
    email: str, 
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) != USER_TYPE.ADMIN):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        col_names = ['email', 'user_type']
        if email != 'all':
            valid = is_email_valid(email)
            if valid:
                cur.execute("SELECT email, user_type FROM user_accounts WHERE email = %s",
                            (email, ))
                row = conv_to_dict("users", cur.fetchall(), col_names)
                if len(row) > 0:
                    cur.execute("DELETE FROM user_accounts WHERE email = %s", 
                                (email, ))
                    resp_dict = row
                    response.status_code = status.HTTP_200_OK
                else:
                    resp_dict = {}
                    response.status_code = status.HTTP_404_NOT_FOUND
            else:
                resp_dict = {}
                response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            cur.execute("SELECT email, user_type FROM user_accounts")
            rows = conv_to_dict("user_accounts", cur.fetchall(), col_names)
            cur.execute("DELETE FROM user_accounts")
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

class loginObj(BaseModel):
    email: str
    otp: int

@router.post("/genotp")
def genotp(data: loginObj, response: Response):
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        cur.execute("SELECT * FROM user_accounts WHERE email = %s",
                    (data.email, ))
        if len(cur.fetchall()) > 0:
            random.seed(time())
            otp = random.randint(1111, 9999)
            cur.execute("UPDATE user_accounts SET otp = %s WHERE email = %s",
                        (otp, data.email))
            send_email_otp(otp, data.email)
            conn.commit()
            response.status_code = status.HTTP_200_OK
            resp_dict = {"message" : f"OTP sent to {data.email}!"}
        else:
            response.status_code = status.HTTP_404_NOT_FOUND
            resp_dict = {"message" : "Given email is not registered :("}
    except:
        response.status_code = status.HTTP_400_BAD_REQUEST
        resp_dict = {"message" : "Bad request?"}
    finally:
        cur.close()
        conn.close()
        return resp_dict

@router.post("/login")
def login(data: loginObj, response: Response):
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        cur.execute("SELECT otp, user_type FROM user_accounts WHERE email = %s",
                    (data.email, ))
        row = cur.fetchall()
        if len(row) > 0:
            saved_otp = row[0][0]
            user_type = row[0][1]
            if saved_otp != None and saved_otp == data.otp:
                token = ''.join(str(uuid.uuid4()).split('-'))
                cur.execute("""
                            UPDATE user_accounts 
                            SET otp = NULL, token = %s, token_gen_time = %s 
                            WHERE email = %s
                            """,
                            (token, datetime.utcnow(), data.email))
                conn.commit()
                resp_dict = { 
                    "email" : data.email, 
                    "user_type" : user_type, 
                    "user_str" : user_type_to_str(user_type), 
                    "token" : token,
                    "message" : "Login successful!" 
                }
                response.status_code = status.HTTP_200_OK
            else:
                resp_dict = {"message" : "Invalid OTP"}
                response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            resp_dict = {"message" : "Given email is not registered :("}
            response.status_code = status.HTTP_404_NOT_FOUND
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict

def _verify_token(token):
    conn = connect()
    cur = conn.cursor()
    try:
        verified_type = USER_TYPE(-1)
        cur.execute("SELECT token_gen_time, user_type FROM user_accounts WHERE token = %s",
                    (token, ))
        row = cur.fetchall()
        if len(row) > 0:
            gen_time = row[0][0]
            user_type = int(row[0][1])
            if (datetime.now(timezone.utc) - gen_time).days < token_validity:
                verified_type = USER_TYPE(user_type)
            else:
                cur.execute("""
                            UPDATE user_accounts 
                            SET token = NULL, token_gen_time = NULL 
                            WHERE token = %s
                            """,
                            (token, ))
                conn.commit()
    finally:
        cur.close()
        conn.close()
        return verified_type

class verifyObj(BaseModel):
    token: str

@router.post("/verify")
def verify(data: verifyObj, response: Response):
    try:
        resp_dict = {"message" : "Temporary server error :/"}
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        conn = connect()
        cur = conn.cursor()
        if _verify_token(data.token) != USER_TYPE.INVALID:
            cur.execute("SELECT email, user_type FROM user_accounts WHERE token = %s",
                        (data.token, ))
            row = cur.fetchall()
            email = row[0][0]
            user_type = row[0][1]
            resp_dict = { 
                "email" : email,
                "user_type" : user_type, 
                "user_str" : user_type_to_str(user_type), 
                "token" : data.token,
                "message" : "Login successful!" 
            }
            response.status_code = status.HTTP_200_OK
        else:
            resp_dict = {"message" : "Token invalid, please login again"}
            response.status_code = status.HTTP_401_UNAUTHORIZED
    finally:
        cur.close()
        conn.close()
        return resp_dict

def _get_email_from_token(token: str):
    conn = connect()
    cur = conn.cursor()
    try:
        email = None
        if _verify_token(token) != USER_TYPE.INVALID:
            cur.execute("SELECT email FROM user_accounts WHERE token = %s",
                        (token, ))
            row = cur.fetchall()
            if len(row) > 0:
                email = str(row[0][0])
    finally:
        cur.close()
        conn.close()
        return email

@router.post("/photo/{email}")
def post_photo(
    email: str,
    file: UploadFile,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    if _get_email_from_token(token) != email:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "You can only upload photo for your own account"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    # try:
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    img = cv2.imdecode(numpy.fromstring(file.file.read(), numpy.uint8), cv2.IMREAD_UNCHANGED)
    from app.routers.encodings import _img_to_base64
    cur.execute("""
                UPDATE user_accounts 
                SET photo = %s 
                WHERE email = %s
                """,
                (_img_to_base64(img, cvt_code=None, compression=20), email))
    conn.commit()
    response.status_code = status.HTTP_200_OK
    resp_dict = {"message" : "Image saved successfully!"}
    # except:
    #    response.status_code = status.HTTP_400_BAD_REQUEST
    #    resp_dict = {}
    # finally:
    cur.close()
    conn.close()
    return resp_dict

@router.get("/photo/{email}")
def get_photo(
    email: str, 
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT photo from user_accounts WHERE email = %s",
                (email, ))
    resp_dict = {
        "photo" : cur.fetchone()[0]
    }
    cur.close()
    conn.close()
    return resp_dict

# add students from excel spreadsheet
@router.post("/excel/add_students")
def add_students_from_xlsx(
    file: UploadFile,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) != USER_TYPE.ADMIN):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    df = pd.read_excel(file.file)
    rollnum_colname = df.columns.to_list()[0]
    name_colname = df.columns.to_list()[1]
    conn = connect()
    cur = conn.cursor()
    isvalid = False
    for index, row in df.iterrows():
        roll_num = row[rollnum_colname].lower()
        name = row[name_colname].title().replace('.', '')
        isvalid = len(roll_num) == 9 and ''.join(name.split()).isalpha()
        if isvalid:
            cur.execute("INSERT INTO user_accounts (email,user_type) VALUES (%s, %s)", 
                        (f"{roll_num}@iiitr.ac.in", 0))
            cur.execute("INSERT INTO students (roll_num, name) VALUES (%s, %s)", 
                        (roll_num, name))
        else:
            break
    if isvalid:
        conn.commit()
        response.status_code = status.HTTP_201_CREATED
        resp_dict = {'message' : 'Students added successfully!'}
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        resp_dict = {'message' : '''Invalid data provided. 
                     Please make sure that the first column contains the roll numbers and the second column contains the name only'''}
    cur.close()
    conn.close()
    return resp_dict
