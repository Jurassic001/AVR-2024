import sqlite3, pathlib, os

HAZARD_LIST = [
    ((231, 82, 0), 14, (0, 0, 32)), # Fire Rescue Building
    ((310, 125, 0), 9, (0, 0, 40)), # Slope Tower Short 1
    ((310, 45, 0), 9, (0, 0, 40)), # Slope Tower Short 2
    ((356, 117, 0), 12, (0, 0, 64)), # Slope Tower Mid 1
    ((356, 53, 0), 12, (0, 0, 64)), # Slope Tower Mid 2
    ((404, 120, 0), 12, (0, 0, 106)), # Slope Tower Tall 1
    ((404, 50, 0), 12, (0, 0, 106)), # Slope Tower Tall 2
    ((89, 116, 0), 18, (0, 0, 36)),
    ((39, 116, 0), 9, (0, 0, 24)), # School building
    ((54, 48, 0), 16, (0, 0, 48)),
    ((124, 48, 0), 16, (0, 0, 48)),
    ((404, 62, 90), 5, (0, 45, 0)),
    ((71, 51, 44), 4, (34, 0, 0)),
]

os.chdir(pathlib.Path(__file__).parent.resolve())
print(os.getcwd())
def check_db(filename):
    return os.path.exists(filename)
 
db_file = 'database.db'

if not check_db(db_file):
    with sqlite3.connect(db_file) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE hazards (
                              position,
                              radius,
                              height_vec
                              )""")
        c.execute("""CREATE TABLE path_nodes (
                              position,
                              blocked
                              ) """)
        c.execute("""CREATE TABLE log_num (
                            num) """)
        for hazard in HAZARD_LIST:
            c.execute(f"INSERT INTO hazards VALUES ('{hazard[0]}', {hazard[1]}, '{hazard[2]}')")
        c.execute("""INSERT INTO log_num VALUES (171)""")
        conn.commit()
        
