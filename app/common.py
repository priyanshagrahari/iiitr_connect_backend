def conv_to_dict(key, data, columns):
    if len(data) == 0:
        return []
    if len(data[0]) != len(columns):
        raise Exception('number of columns mismatched')
    data_dict_list = []
    for row in data:
        data_dict_list.append(dict(zip(columns, row)))
    return {key : data_dict_list}

def user_type_to_str(user_type):
    if user_type == 0:
        return "student"
    elif user_type == 1:
        return "professor"
    elif user_type == 2:
        return "parent"
    elif user_type == 10:
        return "admin"
