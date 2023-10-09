import psycopg2
from app.config import DB_HOST, DB_DATABASE, DB_PASSWORD, DB_USER
from app.common import USER_TYPE

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

def init():
    conn = connect()
    cur = conn.cursor()

    # install uuis-ossp if not present
    cur.execute("""
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp"
    """)
    conn.commit()

    # create user_accounts table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.user_accounts
    (
        uid uuid NOT NULL DEFAULT uuid_generate_v4(),
        email character varying COLLATE pg_catalog."default" NOT NULL,
        otp bigint,
        user_type numeric NOT NULL DEFAULT 0,
        token character varying COLLATE pg_catalog."default",
        token_gen_time timestamp with time zone,
        photo character varying COLLATE pg_catalog."default",
        CONSTRAINT user_pkey PRIMARY KEY (uid),
        CONSTRAINT user_email_key UNIQUE (email),
        CONSTRAINT user_otp_key UNIQUE (otp)
    )
    """)

    # add yourself as admin :)
    cur.execute("""
    INSERT INTO user_accounts (email, user_type) VALUES (%s, %s) 
    ON CONFLICT (email) DO UPDATE SET user_type = %s
    """, 
    ('cs20b1014@iiitr.ac.in', USER_TYPE.ADMIN.value, USER_TYPE.ADMIN.value))

    # create students table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.students
    (
        roll_num character(9) COLLATE pg_catalog."default" NOT NULL,
        name character varying(128) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT student_pkey PRIMARY KEY (roll_num)
    )
    """)

    # create professors table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.professors
    (
        email_prefix character varying COLLATE pg_catalog."default" NOT NULL,
        name character varying(128) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT teacher_pkey PRIMARY KEY (email_prefix)
    )
    """)

    # create courses table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.courses
    (
        course_code character varying COLLATE pg_catalog."default" NOT NULL,
        name character varying COLLATE pg_catalog."default" NOT NULL,
        begin_date date,
        end_date date,
        accepting_reg boolean NOT NULL DEFAULT true,
        description character varying COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT course_pkey PRIMARY KEY (course_code, begin_date)
    )
    """)

    # create profs_courses table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.profs_courses
    (
        prof_prefix character varying COLLATE pg_catalog."default" NOT NULL,
        course_code character varying COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT profs_courses_pkey PRIMARY KEY (prof_prefix, course_code),
        CONSTRAINT profs_courses_course_code_fkey FOREIGN KEY (course_code)
            REFERENCES public.courses (course_code) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
        CONSTRAINT profs_courses_prof_prefix_fkey FOREIGN KEY (prof_prefix)
            REFERENCES public.professors (email_prefix) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    )
    """)

    # create lectures table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.lectures
    (
        lecture_id uuid NOT NULL DEFAULT uuid_generate_v4(),
        course_code character varying COLLATE pg_catalog."default" NOT NULL,
        description character varying(255) COLLATE pg_catalog."default",
        CONSTRAINT lecture_pkey PRIMARY KEY (lecture_id),
        CONSTRAINT lecture_course_code_fkey FOREIGN KEY (course_code)
            REFERENCES public.courses (course_code) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    )
    """)

    # create course_registrations table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.course_registrations
    (
        course_code character varying COLLATE pg_catalog."default" NOT NULL,
        student_roll character(9) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT course_registrations_pkey PRIMARY KEY (course_code, student_roll),
        CONSTRAINT course_registrations_course_code_fkey FOREIGN KEY (course_code)
            REFERENCES public.courses (course_code) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
        CONSTRAINT course_registrations_student_roll_fkey FOREIGN KEY (student_roll)
            REFERENCES public.students (roll_num) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    )
    """)

    # create attendances table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.attendances
    (
        lecture_id uuid NOT NULL,
        student_roll character(9) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT attendances_pkey PRIMARY KEY (lecture_id, student_roll),
        CONSTRAINT attendances_lecture_id_fkey FOREIGN KEY (lecture_id)
            REFERENCES public.lectures (lecture_id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
        CONSTRAINT attendances_student_roll_fkey FOREIGN KEY (student_roll)
            REFERENCES public.students (roll_num) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    )
    """)

    # create face encodings table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.face_encodings
    (
        roll_num character(9) COLLATE pg_catalog."default" NOT NULL,
        face_encoding numeric[] NOT NULL,
        creation_time timestamp with time zone NOT NULL,
        CONSTRAINT face_encodings_roll_num_fkey FOREIGN KEY (roll_num)
            REFERENCES public.students (roll_num) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
    )
    """)

    cur.close()
    conn.commit()
    conn.close()

init()