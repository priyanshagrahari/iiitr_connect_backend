from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from app.database import connect
from app.send_email import send_email_otp
from app.common import user_type_to_str, is_email_valid, conv_to_dict

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

class user(BaseModel):
    email: str
    user_type: int = 0

# create one
@router.post("/create")
def create_user(data: user, response: Response):
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        valid = is_email_valid(data.email) and user_type_to_str(data.user_type) != None
        if valid:
            cur.execute(f"INSERT INTO user_account (email,user_type) VALUES ('{data.email}','{data.user_type}')")
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
        conn.commit()
        return resp_dict

# retrieve one/all
@router.get("/get/{email}")
def get_users(email: str, response: Response):
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        col_names = ['email', 'user_type']
        if email != 'all':
            cur.execute(f"SELECT email, user_type FROM user_account WHERE user_account.email = '{email}'")
        else:
            cur.execute("SELECT email, user_type FROM user_account ORDER BY email ASC")
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
        return resp_dict

# update one
@router.post("/update/{email}")
def update_user(data: user, email: str, response: Response):
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        cur.execute(f"SELECT email FROM user_account WHERE user_account.email = '{email}'")
        matches = cur.fetchall()
        if len(matches) == 1:
            valid = is_email_valid(data.email) and user_type_to_str(data.user_type) != None
            if valid:
                cur.execute(f"DELETE FROM user_account WHERE email = '{email}'")
                cur.execute(f"INSERT INTO user_account (email, user_type) VALUES ('{data.email}', '{data.user_type}')")
                resp_dict = data
                response.status_code = status.HTTP_200_OK
            else:
                resp_dict = {"message" : "Given email may already exist"}
                response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            resp_dict = {"message" : "Given email was not found!"}
            response.status_code = status.HTTP_404_NOT_FOUND
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.commit()
        return resp_dict


# delete one/all
@router.delete("/delete/{email}")
def delete_user(email: str, response: Response):
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        col_names = ['email', 'user_type']
        if email != 'all':
            valid = is_email_valid(email)
            if valid:
                cur.execute(f"SELECT email, user_type FROM user_account WHERE email = '{email}'")
                row = conv_to_dict("users", cur.fetchall(), col_names)
                if len(row) > 0:
                    cur.execute(f"DELETE FROM user_account WHERE email = '{email}'")
                    resp_dict = row
                    response.status_code = status.HTTP_200_OK
                else:
                    resp_dict = {}
                    response.status_code = status.HTTP_404_NOT_FOUND
            else:
                resp_dict = {}
                response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            cur.execute("SELECT email, user_type FROM user_account")
            rows = conv_to_dict("user_accounts", cur.fetchall(), col_names)
            cur.execute("DELETE FROM user_account")
            resp_dict = rows
            response.status_code = status.HTTP_200_OK
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.commit()
        return resp_dict

class loginObj(BaseModel):
    email: str
    otp: int

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
            response.status_code = status.HTTP_404_NOT_FOUND
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