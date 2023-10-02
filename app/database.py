import psycopg2
from app.config import DB_HOST, DB_DATABASE, DB_PASSWORD, DB_USER

def connect():
    conn = None
    try:
        conn = psycopg2.connect(
            database = DB_DATABASE,
            user = DB_USER,
            password = DB_PASSWORD,
            host = DB_HOST
        )
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            return conn

conn = connect()
cur = conn.cursor()
cur.execute("""
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
""")
conn.commit()
cur.execute("""
CREATE TABLE IF NOT EXISTS public.user_account
(
    uid uuid NOT NULL DEFAULT uuid_generate_v4(),
    email character varying COLLATE pg_catalog."default" NOT NULL,
    otp bigint,
    user_type numeric NOT NULL DEFAULT 0,
    token character varying COLLATE pg_catalog."default",
    token_gen_time timestamp with time zone,
    CONSTRAINT user_pkey PRIMARY KEY (uid),
    CONSTRAINT user_email_key UNIQUE (email),
    CONSTRAINT user_otp_key UNIQUE (otp)
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS public.student
(
    roll_num character(9) COLLATE pg_catalog."default" NOT NULL,
    name character varying(128) COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT student_pkey PRIMARY KEY (roll_num)
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS public.teacher
(
    email_prefix character varying COLLATE pg_catalog."default" NOT NULL,
    name character varying(128) COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT teacher_pkey PRIMARY KEY (email_prefix)
);
""")
cur.close()
conn.commit()
conn.close()