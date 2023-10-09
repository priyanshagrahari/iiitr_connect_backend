import re
from enum import Enum
email_regex = re.compile(r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\"([]!#-[^-~ \t]|(\\[\t -~]))+\")@([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\[[\t -Z^-~]*])")

def conv_to_dict(key, data, columns):
    if len(data) == 0:
        return {}
    if len(data[0]) != len(columns):
        raise Exception('number of columns mismatched')
    data_dict_list = []
    for row in data:
        data_dict_list.append(dict(zip(columns, row)))
    return {key : data_dict_list}

class USER_TYPE(Enum):
    INVALID = -1
    STUDENT = 0
    PARENT = 1
    SEPARATOR = 5
    PROFESSOR = 9
    ADMIN = 10

def user_type_to_str(user_type):
    if user_type == 0:
        return "student"
    elif user_type == 1:
        return "parent"
    elif user_type == 9:
        return "professor"
    elif user_type == 10:
        return "admin"
    else:
        return None

def is_email_valid(email):
    if re.fullmatch(email_regex, email):
        return True
    else:
        return False 