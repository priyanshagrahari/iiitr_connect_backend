from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from app.db_connect import connect
from app.send_email import send_email_otp
from app.common import user_type_to_str

import random
from time import time
import uuid
from datetime import datetime, timezone

token_validity = 15 # generated tokens valid for days
conn = connect()
router = APIRouter(
    prefix="/users",
    tags=["users"]
)

class loginObj(BaseModel):
    email: str
    otp: int | None = None

@router.post("/genotp")
def genotp(data: loginObj, response: Response):
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        cur.execute(f"SELECT * FROM user_account WHERE email = '{data.email}'")
        if len(cur.fetchall()) > 0:
            random.seed(time())
            otp = random.randint(111111, 999999)
            cur.execute(f"UPDATE user_account SET otp = {otp} WHERE email = '{data.email}'")
            send_email_otp(otp, data.email)
            response.status_code = status.HTTP_200_OK
            resp_dict = {"message" : f"OTP sent to {data.email}!"}
        else:
            response.status_code = status.HTTP_400_BAD_REQUEST
            resp_dict = {"message" : "Given email is not registered :("}
    except:
        response.status_code = status.HTTP_400_BAD_REQUEST
        resp_dict = {}
    finally:
        cur.close()
        conn.commit()
        return resp_dict

@router.post("/login")
def login(data: loginObj, response: Response):
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        cur.execute(f"SELECT otp, user_type FROM user_account WHERE email = '{data.email}'")
        row = cur.fetchall()
        if len(row) > 0:
            saved_otp = row[0][0]
            user_type = row[0][1]
            if saved_otp != None and saved_otp == data.otp:
                token = ''.join(str(uuid.uuid4()).split('-'))
                cur.execute(f"""
                            UPDATE user_account 
                            SET otp = NULL, token = '{token}', token_gen_time = '{datetime.utcnow()}' 
                            WHERE email = '{data.email}'
                            """)
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
        conn.commit()
        return resp_dict

def _verify(token):
    cur = conn.cursor()
    try:
        verified = False
        cur.execute(f"SELECT token_gen_time FROM user_account WHERE token = '{token}'")
        row = cur.fetchall()
        if len(row) > 0:
            timestp = row[0][0]
            if (timestp - datetime.now(timezone.utc)).days < token_validity:
                verified = True
            else:
                cur.execute(f"""
                            UPDATE user_account 
                            SET token = NULL, token_gen_time = NULL 
                            WHERE token = '{token}'
                            """)
    finally:
        cur.close()
        conn.commit()
        return verified

class verifyObj(BaseModel):
    token: str

@router.post("/verify")
def verify(data: verifyObj, response: Response):
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if _verify(data.token):
            cur = conn.cursor()
            cur.execute(f"SELECT email, user_type FROM user_account WHERE token = '{data.token}'")
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
        return resp_dict