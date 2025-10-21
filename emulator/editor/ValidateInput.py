import re
import datetime

# 定义数据类型及其对应的验证函数
def get_integer(value):
    try:
        return int(value)
    except ValueError:
        return None

def get_float(value):
    try:
        return float(value)
    except ValueError:
        return None

def get_string(value):
    return value.strip("'")

def get_wstring(value):
    return value.strip('"')

def get_bool(value):
    if isinstance(value, int):
        return {0: False, 1: True}.get(value, None)
    if isinstance(value, str):
        return {"true": True, "false": False, "0": False, "1": True}.get(value.lower(), None)
    return None

# 时间相关常量
SECOND = 1000000
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR

# 正则表达式模型
IEC_TIME_MODEL = re.compile(r"(?:(?:T|TIME)#)?(-)?(?:(\d+(\.\d+)?)D_?)?(?:(\d+(\.\d+)?)H_?)?(?:(\d+(\.\d+)?)M(?!S)_?)?(?:(\d+(\.\d+)?)S_?)?(?:(\d+(\.\d+)?)MS)?$")
IEC_DATE_MODEL = re.compile(r"(?:(?:D|DATE)#)?([0-9]{4})-([0-9]{2})-([0-9]{2})$")
IEC_DATETIME_MODEL = re.compile(r"(?:(?:DT|DATE_AND_TIME)#)?([0-9]{4})-([0-9]{2})-([0-9]{2})-([0-9]{2}):([0-9]{2}):([0-9]{2}(?:\.[0-9]+)?)$")
IEC_TIMEOFDAY_MODEL = re.compile(r"(?:(?:TOD|TIME_OF_DAY)#)?([0-9]{2}):([0-9]{2}):([0-9]{2}(?:\.[0-9]+)?)$")

def get_time(value):
    result = IEC_TIME_MODEL.match(value.upper())
    if result is not None:
        negative, days, _, hours, _, minutes, _, seconds, _, milliseconds, _ = result.groups()
        microseconds = 0
        not_null = False
        for v, factor in [(days, DAY), (hours, HOUR), (minutes, MINUTE), (seconds, SECOND), (milliseconds, 1000)]:
            if v is not None:
                microseconds += float(v) * factor
                not_null = True
        if not not_null:
            return None
        if negative is not None:
            microseconds = -microseconds
        return datetime.timedelta(microseconds=microseconds)
    return None

def get_date(value):
    result = IEC_DATE_MODEL.match(value.upper())
    if result is not None:
        year, month, day = map(int, result.groups())
        try:
            date = datetime.datetime(year, month, day)
        except ValueError:
            return None
        base_date = datetime.datetime(1970, 1, 1)
        return date - base_date
    return None

def get_datetime(value):
    result = IEC_DATETIME_MODEL.match(value.upper())
    if result is not None:
        year, month, day, hours, minutes, seconds = result.groups()
        try:
            date = datetime.datetime(int(year), int(month), int(day), int(hours), int(minutes), int(float(seconds)), int((float(seconds) * SECOND) % SECOND))
        except ValueError:
            return None
        base_date = datetime.datetime(1970, 1, 1)
        return date - base_date
    return None

def get_timeofday(value):
    result = IEC_TIMEOFDAY_MODEL.match(value.upper())
    if result is not None:
        hours, minutes, seconds = result.groups()
        microseconds = 0
        for v, factor in [(hours, HOUR), (minutes, MINUTE), (seconds, SECOND)]:
            microseconds += float(v) * factor
        return datetime.timedelta(microseconds=microseconds)
    return None

# 定义一个简单的验证函数字典
GetTypeValue = {
    "BOOL": get_bool,
    "SINT": get_integer,
    "INT": get_integer,
    "DINT": get_integer,
    "LINT": get_integer,
    "USINT": get_integer,
    "UINT": get_integer,
    "UDINT": get_integer,
    "ULINT": get_integer,
    "BYTE": get_integer,
    "WORD": get_integer,
    "DWORD": get_integer,
    "LWORD": get_integer,
    "REAL": get_float,
    "LREAL": get_float,
    "STRING": get_string,
    "WSTRING": get_wstring,
    "TIME": get_time,
    "DATE": get_date,
    "DT": get_datetime,
    "TOD": get_timeofday
}
examples = {
    "BOOL": ("TRUE", "FALSE", "1", "0"),
    "SINT": ("-128 ~ 127"),
    "INT": ("-32768 ~ 32767"),
    "DINT": ("-2147483648 ~ 2147483647"),
    "LINT": ("-9223372036854775808 ~ 9223372036854775807"),
    "USINT": ("0 ~ 255"),
    "UINT": ("0 ~ 65535"),
    "UDINT": ("0 ~ 4294967295"),
    "ULINT": ("0 ~ 18446744073709551615"),
    "BYTE": ("0 ~ 255"),
    "WORD": ("0 ~ 65535"),
    "DWORD": ("0 ~ 4294967295"),
    "LWORD": ("0 ~ 18446744073709551615"),
    "REAL": ("-3.4e38 ~ 3.4e38"),
    "LREAL": ("-1.7e308 ~ 1.7e308"),
    "STRING": ("'Hello'", "'World'"),
    "WSTRING": ('"Hello"', '"World"'),
    "TIME": ("T#5D12H30M45.5S100MS", "TIME#1H30M"),
    "DATE": ("D#2023-06-25", "DATE#1999-12-31","2024-01-01"),
    "DT": ("DT#2023-06-25-14:30:45.5", "DATE_AND_TIME#1999-12-31-23:59:59","2024-01-01-00:00:00"),
    "TOD": ("TOD#14:30:45.5", "TIME_OF_DAY#23:59:59","12:00:00")
}



# 从命令行获取输入
def get_user_input():
    iec_type = input("Enter the IEC type (e.g., BOOL, INT, STRING): ")
    value = input("Enter the value: ")
    return iec_type, value

# 验证输入值
def validate_input(iec_type, value):
    if iec_type not in GetTypeValue:
        return False, "Invalid IEC type."

    validator = GetTypeValue[iec_type]
    result = validator(value)
    if result is None:
        return False, f"Invalid value '{value}' for IEC type '{iec_type}'."
    return True, result

# 主程序
def main():
    iec_type, value = get_user_input()
    is_valid, result = validate_input(iec_type, value)
    if is_valid:
        print(f"Valid value: {result}")
    else:
        print(f"Error: {result}")

if __name__ == "__main__":
    main()
