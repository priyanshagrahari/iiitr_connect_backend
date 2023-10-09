import base64
import aiofiles
from fastapi import APIRouter, Response, status, UploadFile, File, Form, Header
from fastapi.responses import FileResponse
from typing import Annotated, Union
from app.database import connect
from app.routers.users import _verify_token, _get_email_from_token
from app.routers.students import _roll_num_exists
import face_recognition
import cv2
from io import BytesIO
from app.config import IMG_CACHE_LOCATION
from pathlib import Path
from app.common import conv_to_dict, USER_TYPE

from time import time
from datetime import datetime, timezone

conn = connect()
router = APIRouter(
    prefix="/encodings",
    tags=["encodings"]
)

@router.post("/upload/{roll_num}")
async def upload_image(
    file: UploadFile,
    roll_num: str,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    if (token is None or _verify_token(token) == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    #try:
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    valid = len(roll_num) == 9
    exists = False
    if valid: 
        exists = _roll_num_exists(roll_num)
    if valid and exists:
        face = face_recognition.load_image_file(file.file)
        face_locations = face_recognition.face_locations(face)
        if len(face_locations) == 1:
            face_enc = face_recognition.face_encodings(face)[0]
            cur.execute("""
                        INSERT INTO face_encodings
                        (roll_num, face_encoding, creation_time)
                        VALUES (%s, %s, %s)
                        """,
                        (roll_num, face_enc.tolist(), datetime.utcnow()))
            conn.commit()
            # mark face bounding box in image and return base64 encoding
            y1, x2, y2, x1 = face_locations[0][0], face_locations[0][1], face_locations[0][2], face_locations[0][3]
            cv2.rectangle(face, (x1, y1), (x2, y2), (0, 0, 255), 4)
            response.status_code = status.HTTP_200_OK
            resp_dict = {
                "message" : "Face encoding saved successfully!",
                "image" : _img_to_base64(face)
                }
        else:
            response.status_code = status.HTTP_400_BAD_REQUEST
            resp_dict = {"message" : "Please try again with a different photo"}
    elif not valid:
        response.status_code = status.HTTP_400_BAD_REQUEST
        resp_dict = {"message" : "Invalid roll number"}
    elif not exists:
        response.status_code = status.HTTP_404_NOT_FOUND
        resp_dict = {"message" : "Roll number not found"}
    # except:
    #     resp_dict = {}
    #     response.status_code = status.HTTP_400_BAD_REQUEST
    # finally:
    cur.close()
    conn.close()
    return resp_dict

def _img_to_base64(img, cvt_code = cv2.COLOR_RGB2BGR, compression = 50, return_str = True):
    is_success, img_jpg = False, None
    if not cvt_code:
        is_success, img_jpg = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), compression])
    else:
        is_success, img_jpg = cv2.imencode('.jpg', cv2.cvtColor(img, cvt_code), [int(cv2.IMWRITE_JPEG_QUALITY), compression])
    if is_success:
        io_buf = BytesIO(img_jpg)
        img_64 = base64.b64encode(io_buf.read())
        if return_str:
            img_64 = "data:image/jpg;base64," + img_64.decode()
        return img_64
    return None

@router.delete("/{roll_num}")
def delete_encodings(
    roll_num: str, 
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    user_type = _verify_token(token)
    if (token is None or user_type == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    elif (user_type == USER_TYPE.STUDENT):
        if _get_email_from_token(token).removesuffix('@iiitr.ac.in') != roll_num:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            resp_dict = {"message" : "You can only delete your own encodings"}
            return resp_dict
    conn = connect()
    cur = conn.cursor()
    try:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        col_names = ['roll_num', 'creation_time']
        if roll_num != 'all':
            valid = len(roll_num) == 9 and _roll_num_exists(roll_num)
            if valid:
                cur.execute("SELECT roll_num, creation_time FROM face_encodings WHERE roll_num = %s",
                            (roll_num, ))
                row = conv_to_dict("encodings", cur.fetchall(), col_names)
                if len(row) > 0:
                    cur.execute("DELETE FROM face_encodings WHERE roll_num = %s",
                                (roll_num, ))
                    resp_dict = row
                    response.status_code = status.HTTP_200_OK
                else:
                    resp_dict = {}
                    response.status_code = status.HTTP_404_NOT_FOUND
            else:
                resp_dict = {}
                response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            cur.execute("SELECT roll_num, creation_time FROM face_encodings")
            rows = conv_to_dict("encodings", cur.fetchall(), col_names)
            cur.execute("DELETE FROM face_encodings")
            resp_dict = rows
            response.status_code = status.HTTP_200_OK
    except:
        resp_dict = {}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.commit()
        conn.close()
        return resp_dict