import psycopg2
from app.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USERNAME

def connect():
    conn = None
    try:
        print("Connecting to the PostgreSQL database...")
        conn = psycopg2.connect(
            database = DB_NAME,
            user = DB_USERNAME,
            password = DB_PASSWORD,
            host = DB_HOST,
            port = DB_PORT
        )
        cur = conn.cursor()
        print("PostgreSQL database version:")
        cur.execute("SELECT version()")
        db_version = cur.fetchone()
        print(db_version)
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            return conn