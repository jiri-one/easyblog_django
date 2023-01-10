from datetime import datetime

def jiri_one_db_file_name():
    return datetime.now().strftime(f"db_jiri_one_%y-%m-%d_%H:%M.json")
