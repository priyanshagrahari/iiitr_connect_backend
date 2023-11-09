import base64
import numpy as np
from fastapi import APIRouter, Response, status, UploadFile, Header
from typing import Annotated, Union
from app.database import connect
from app.routers.users import _verify_token, _get_email_from_token
from app.routers.students import _roll_num_exists
import face_recognition
import cv2
from io import BytesIO
from app.config import IMG_CACHE_LOCATION
from app.common import conv_to_dict, USER_TYPE
from app.send_email import send_encoding_reminder_email

from time import time
from datetime import datetime, timezone

encoding_validity = 7 # generated encodings valid for days
router = APIRouter(
    prefix="/encodings",
    tags=["encodings"]
)

# upload image and save encoding if valid
@router.post("/student/{roll_num}")
async def upload_image(
    file: UploadFile,
    roll_num: str,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    _trim_encodings(send_reminder = False)
    user_type = _verify_token(token)
    if (token is None or user_type == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message" : "Invalid token, please login again"}
        return resp_dict
    elif (user_type == USER_TYPE.STUDENT):
        if _get_email_from_token(token).removesuffix('@iiitr.ac.in') != roll_num:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            resp_dict = {"message" : "You can only upload encodings for yourself"}
    conn = connect()
    cur = conn.cursor()
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    valid = len(roll_num) == 9
    exists = False
    if valid: 
        exists = _roll_num_exists(roll_num)
    if valid and exists:
        face = cv2.imdecode(np.fromstring(file.file.read(), np.uint8), cv2.IMREAD_UNCHANGED)
        face_locations = face_recognition.face_locations(face)
        path = IMG_CACHE_LOCATION + f"/{datetime.utcnow().timestamp()}_{roll_num}.jpg"
        # print("will save to ", path)
        cv2.imwrite(path, face)
        resp_dict = {}
        if len(face_locations) == 1:
            face_enc = face_recognition.face_encodings(face)[0]
            cur.execute("SELECT encoding_id, face_encoding FROM face_encodings WHERE roll_num = %s",
                        (roll_num, ))
            encs = cur.fetchall()
            if len(encs) > 0:
                matches = []
                unmatches = []
                for enc in encs:
                    enc = list(enc)
                    enc[1] = [float(x) for x in enc[1]]
                    result = face_recognition.compare_faces([enc[1]], face_enc)
                    if result[0]:
                        matches.append(enc)
                    else:
                        unmatches.append(enc)
                if len(matches) > len(unmatches):
                    cur.execute("""
                                INSERT INTO face_encodings
                                (roll_num, face_encoding, creation_time)
                                VALUES (%s, %s, %s)
                                """,
                                (roll_num, face_enc.tolist(), datetime.utcnow()))
                    conn.commit()
                    for un in unmatches:
                        cur.execute("DELETE FROM face_encodings WHERE encoding_id = %s",
                                    (un[0], ))
                        conn.commit()
                    response.status_code = status.HTTP_200_OK
                    resp_dict = {
                        "message" : f"Encoding saved, deleted {len(unmatches)} conflicting encodings",
                        "count" : (len(matches) + 1)
                    }
                else:
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    resp_dict = {
                        "message" : "Given face does not match previous encodings, please delete all encodings and try again",
                        "count" : len(encs)
                    }
            else:
                cur.execute("""
                            INSERT INTO face_encodings
                            (roll_num, face_encoding, creation_time)
                            VALUES (%s, %s, %s)
                            """,
                            (roll_num, face_enc.tolist(), datetime.utcnow()))
                conn.commit()
                response.status_code = status.HTTP_200_OK
                resp_dict = {
                    "message" : "Face encoding saved successfully!",
                    "count" : 1
                }
            y1, x2, y2, x1 = face_locations[0][0], face_locations[0][1], face_locations[0][2], face_locations[0][3]
            height, width = face.shape[:2]
            resp_dict['face'] = [
                {
                    "x" : x1,
                    "y" : y1
                },
                {
                    "x" : x2,
                    "y" : y2
                },
            ]
            resp_dict["dimensions"] = {
                "height" : height,
                "width" : width
            }
        else:
            response.status_code = status.HTTP_400_BAD_REQUEST
            resp_dict = {"message" : "None or more than one faces found, please try again with a different photo"}
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

# get number of face encodings for student
@router.get("/student/{roll_num}")
def get_num_enc(
    roll_num: str,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    _trim_encodings(send_reminder = False)
    if (token is None or _verify_token(token) == USER_TYPE.INVALID):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT encoding_id FROM face_encodings WHERE roll_num = %s",
                (roll_num, ))
    rows = cur.fetchall()
    resp_dict = {'count' : len(rows)}
    return resp_dict

@router.patch("/trim")
def _trim_encodings(send_reminder : bool = True):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT encoding_id, creation_time FROM face_encodings")
    rows = cur.fetchall()
    for row in rows:
        enc_id = row[0]
        cr_time = row[1]
        diff = (datetime.now(timezone.utc) - cr_time).days
        if diff >= encoding_validity:
            cur.execute("DELETE FROM face_encodings WHERE encoding_id = %s",
                        (enc_id, ))
            conn.commit()
    if send_reminder:
        cur.execute("SELECT roll_num, COUNT(encoding_id) FROM face_encodings GROUP BY roll_num")
        rows = cur.fetchall()
        for row in rows:
            roll_num = row[0]
            count = row[1]
            if count < 3:
                send_encoding_reminder_email(roll_num)
    cur.close()
    conn.close()

@router.delete("/student/{roll_num}")
def delete_encodings(
    roll_num: str, 
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    _trim_encodings(send_reminder = False)
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
                    conn.commit()
                    resp_dict = row
                    resp_dict['message'] = "Encodings deleted successfully!";
                    response.status_code = status.HTTP_200_OK
                else:
                    resp_dict = {'message' : 'No encodings found to delete'};
                    response.status_code = status.HTTP_404_NOT_FOUND
            else:
                resp_dict = {}
                response.status_code = status.HTTP_400_BAD_REQUEST
        else:
            cur.execute("SELECT roll_num, creation_time FROM face_encodings")
            rows = conv_to_dict("encodings", cur.fetchall(), col_names)
            cur.execute("DELETE FROM face_encodings")
            conn.commit()
            resp_dict = rows
            response.status_code = status.HTTP_200_OK
    except:
        resp_dict = {"message" : "Bad request?"}
        response.status_code = status.HTTP_400_BAD_REQUEST
    finally:
        cur.close()
        conn.close()
        return resp_dict

@router.post("/lecture/{lecture_id}")
async def upload_lecture_image(
    file: UploadFile,
    lecture_id: str,
    response: Response,
    token: Annotated[Union[str, None], Header()] = None
):
    _trim_encodings()
    if (token is None or _verify_token(token).value < USER_TYPE.SEPARATOR.value):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        resp_dict = {"message": "Invalid token, please login again"}
        return resp_dict
    conn = connect()
    cur = conn.cursor()    
    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    cur.execute("SELECT course_id FROM lectures WHERE lecture_id = %s",
                (lecture_id, ))
    course_id = cur.fetchone()[0]
    cur.execute("SELECT student_roll FROM course_registrations WHERE course_id = %s",
                (course_id, ))
    rows = cur.fetchall()
    encodings = []
    missing_enc = []
    for row in rows:
        roll_num = row[0]
        cur.execute("SELECT roll_num, face_encoding FROM face_encodings WHERE roll_num = %s",
                    (roll_num, ))
        stud_rows = cur.fetchall()
        if len(stud_rows) > 0:
            for row in stud_rows:
                row = list(row)
                row[1] = [float(x) for x in row[1]]
                encodings.append(row)
        else:
            missing_enc.append(roll_num)
    cur.close()
    conn.close()
    if len(encodings) == 0:
        response.status_code = status.HTTP_404_NOT_FOUND
        resp_dict = {
            "message" : "No encodings found for registered students"
        }
        return resp_dict

    img = cv2.imdecode(np.fromstring(file.file.read(), np.uint8), cv2.IMREAD_UNCHANGED)
    path = IMG_CACHE_LOCATION + f"/{datetime.utcnow().timestamp()}_{course_id}.jpg"
    print("will save to ", path)
    cv2.imwrite(path, img)
    face_locations = face_recognition.face_locations(img)
    height, width = img.shape[:2]
    resp_dict = {
        "found_faces" : [],
        "not_found_faces" : [],
        "encodings_missing" : missing_enc,
        "dimensions" : {
            "height" : height,
            "width" : width
        },
    }
    for face in face_locations:
        face_enc = face_recognition.face_encodings(img, known_face_locations=[face])[0]
        cmp = face_recognition.compare_faces([e[1] for e in encodings], face_enc, tolerance=0.5)
        matches = 0
        for r in cmp:
            if r:
                matches += 1
        y1, x2, y2, x1 = face[0], face[1], face[2], face[3]
        if matches > 0:
            match_dict = {}
            for i in range(0, len(cmp)):
                if cmp[i]:
                    roll_num = encodings[i][0]
                    if roll_num in match_dict.keys():
                        match_dict[roll_num] += 1
                    else:
                        match_dict[roll_num] = 1
            resp_dict["found_faces"].append({
                "matches" : match_dict,
                "face" : [
                    {
                        "x" : x1,
                        "y" : y1
                    },
                    {
                        "x" : x2,
                        "y" : y2
                    },
                ],
            })
        else:
            resp_dict["not_found_faces"].append({
                "face" : [
                    {
                        "x" : x1,
                        "y" : y1
                    },
                    {
                        "x" : x2,
                        "y" : y2
                    },
                ],
            })
    if len(resp_dict["found_faces"]) > 0:
        response.status_code = status.HTTP_200_OK
        resp_dict['message'] = "Matches found!"
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        if len(resp_dict['not_found_faces']) > 0:
            resp_dict["message"] = "No matches found"
        else:
            resp_dict["message"] = "No faces found"
    return resp_dict
