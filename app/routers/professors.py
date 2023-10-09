from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from app.database import connect
from app.common import conv_to_dict, USER_TYPE
from typing import Annotated, Union
from app.routers.users import _verify_token

conn = connect()
router = APIRouter(
    prefix="/professors",
    tags=["professors"]
)

class professor(BaseModel):
    email_prefix: str
    name: str

# create one
@router.post("/")
def add_professor(
    data: professor, 
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
        cur.execute("INSERT INTO professors (email_prefix, name) VALUES (%s, %s)", 
                    (data.email_prefix, data.name))
        conn.commit()
        resp_dict = data
        response.status_code = status.HTTP_201_CREATED
    except:
        resp_dict = {"message" : "Email prefix may already exist"}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict

def _email_prefix_exists(email_prefix: str):
    conn = connect()
    cur = conn.cursor()
    exists = False
    try:
        cur.execute("SELECT email_prefix FROM professors WHERE email_prefix = %s",
                    (email_prefix, ))
        if len(cur.fetchall()) > 0:
            exists = True
        else:
            exists = False
    finally:
        cur.close()
        conn.close()
        return exists

# retrieve one/all
@router.get("/{email_prefix}")
def get_professor(
    email_prefix: str, 
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
        col_names = ['email_prefix', 'name']
        if email_prefix != 'all':
            cur.execute("SELECT email_prefix, name FROM professors WHERE email_prefix = %s",
                        (email_prefix, ))
        else:
            cur.execute("SELECT email_prefix, name FROM professors ORDER BY email_prefix ASC")
        professors = conv_to_dict("professors", cur.fetchall(), col_names)
        if len(professors) > 0:
            resp_dict = professors
            response.status_code = status.HTTP_200_OK
        else:
            resp_dict = {"message" : "Email prefix not found"}
            response.status_code = status.HTTP_404_NOT_FOUND
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict

# update one
@router.post("/{email_prefix}")
def update_professor(
    data: professor, 
    email_prefix: str, response: Response,
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
        cur.execute("SELECT email_prefix FROM professors WHERE email_prefix = %s",
                    (email_prefix, ))
        matches = cur.fetchall()
        if len(matches) > 0:
            cur.execute("""
                        UPDATE professors
                        SET email_prefix = %s, name = %s
                        WHERE email_prefix = %s;
                        """,
                        (data.email_prefix, data.name, email_prefix))
            conn.commit()
            resp_dict = data
            response.status_code = status.HTTP_200_OK
        else:
            resp_dict = {"message" : "Given email prefix was not found!"}
            response.status_code = status.HTTP_404_NOT_FOUND
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict


# delete one/all
@router.delete("/{email_prefix}")
def delete_professor(
    email_prefix: str, 
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
        col_names = ['email_prefix', 'name']
        if email_prefix != 'all':
            cur.execute("SELECT email_prefix, name FROM professors WHERE email_prefix = %s",
                        (email_prefix, ))
            row = conv_to_dict("professors", cur.fetchall(), col_names)
            if len(row) > 0:
                cur.execute("DELETE FROM professors WHERE email_prefix = %s",
                            (email_prefix, ))
                resp_dict = row
                response.status_code = status.HTTP_200_OK
            else:
                resp_dict = {}
                response.status_code = status.HTTP_404_NOT_FOUND
        else:
            cur.execute("SELECT email_prefix, name FROM professors")
            rows = conv_to_dict("professors", cur.fetchall(), col_names)
            cur.execute("DELETE FROM professors")
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