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
    # cur.execute("""
    # INSERT INTO user_accounts (email, user_type) VALUES (%s, %s) 
    # ON CONFLICT (email) DO UPDATE SET user_type = %s
    # """, 
    # ('cs20b1014@iiitr.ac.in', USER_TYPE.ADMIN.value, USER_TYPE.ADMIN.value))

    # add ramesh sir
    cur.execute("""
    INSERT INTO user_accounts (email, user_type) VALUES (%s, %s) 
    ON CONFLICT (email) DO UPDATE SET user_type = %s
    """, 
    ('jallu@iiitr.ac.in', USER_TYPE.PROFESSOR.value, USER_TYPE.PROFESSOR.value))

    # create students table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.students
    (
        roll_num character(9) COLLATE pg_catalog."default" NOT NULL,
        name character varying(128) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT student_pkey PRIMARY KEY (roll_num)
    )
    """)

    # add yourself as student
    cur.execute("""
    INSERT INTO students (roll_num, name) VALUES (%s, %s) 
    ON CONFLICT (roll_num) DO UPDATE SET roll_num = %s
    """, 
    ('cs20b1014', 'Priyansh Agrahari', 'cs20b1014'))

    # create professors table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.professors
    (
        email_prefix character varying COLLATE pg_catalog."default" NOT NULL,
        name character varying(128) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT teacher_pkey PRIMARY KEY (email_prefix)
    )
    """)

    # add ramesh sir as prof
    cur.execute("""
    INSERT INTO professors (email_prefix, name) VALUES (%s, %s) 
    ON CONFLICT (email_prefix) DO UPDATE SET email_prefix = %s
    """, 
    ('jallu', 'Ramesh Kumar Jallu', 'jallu'))

    # create courses table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.courses
    (
        course_id uuid NOT NULL DEFAULT uuid_generate_v4(),
        course_code character varying COLLATE pg_catalog."default" NOT NULL,
        name character varying COLLATE pg_catalog."default" NOT NULL,
        begin_date date NOT NULL,
        end_date date,
        accepting_reg boolean NOT NULL DEFAULT true,
        description character varying COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT course_id_key PRIMARY KEY (course_id),
        CONSTRAINT course_pkey UNIQUE (course_code, begin_date)
    )
    """)
    
    # create profs_courses table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.profs_courses
    (
        prof_prefix character varying COLLATE pg_catalog."default" NOT NULL,
        course_id uuid NOT NULL,
        CONSTRAINT profs_courses_pkey PRIMARY KEY (prof_prefix, course_id),
        CONSTRAINT profs_courses_course_id_fkey FOREIGN KEY (course_id)
            REFERENCES public.courses (course_id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE CASCADE,
        CONSTRAINT profs_courses_prof_prefix_fkey FOREIGN KEY (prof_prefix)
            REFERENCES public.professors (email_prefix) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE CASCADE
    )
    """)

    # create lectures table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.lectures
    (
        lecture_id uuid NOT NULL DEFAULT uuid_generate_v4(),
        course_id uuid NOT NULL,
        lecture_date date NOT NULL,
        atten_marked boolean NOT NULL DEFAULT false,
        description character varying COLLATE pg_catalog."default",
        CONSTRAINT lectures_pkey PRIMARY KEY (lecture_id),
        CONSTRAINT lectures_course_id_fkey FOREIGN KEY (course_id)
            REFERENCES public.courses (course_id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE CASCADE
    )
    """)

    # create course_registrations table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.course_registrations
    (
        registration_id uuid NOT NULL DEFAULT uuid_generate_v4(),
        course_id uuid NOT NULL,
        student_roll character(9) COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT course_registrations_pkey PRIMARY KEY (registration_id),
        CONSTRAINT course_registrations_course_id_student_roll_key UNIQUE (course_id, student_roll),
        CONSTRAINT course_registrations_course_id_fkey FOREIGN KEY (course_id)
            REFERENCES public.courses (course_id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE CASCADE,
        CONSTRAINT course_registrations_student_roll_fkey FOREIGN KEY (student_roll)
            REFERENCES public.students (roll_num) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE CASCADE
    )
    """)

    # create attendances table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.attendances
    (
        registration_id uuid NOT NULL,
        lecture_id uuid NOT NULL,
        CONSTRAINT attendances_pkey PRIMARY KEY (lecture_id, registration_id),
        CONSTRAINT attendances_lecture_id_fkey FOREIGN KEY (lecture_id)
            REFERENCES public.lectures (lecture_id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE CASCADE,
        CONSTRAINT attendances_registration_id_fkey FOREIGN KEY (registration_id)
            REFERENCES public.course_registrations (registration_id) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE CASCADE
    )
    """)

    # create face encodings table if not exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS public.face_encodings
    (
        encoding_id uuid NOT NULL DEFAULT uuid_generate_v4(),
        roll_num character(9) COLLATE pg_catalog."default" NOT NULL,
        creation_time timestamp with time zone NOT NULL,
        face_encoding numeric[] NOT NULL,
        CONSTRAINT face_encodings_pkey PRIMARY KEY (encoding_id),
        CONSTRAINT face_encodings_roll_num_fkey FOREIGN KEY (roll_num)
            REFERENCES public.students (roll_num) MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE CASCADE
    )
    """)

    cur.close()
    conn.commit()
    conn.close()

init()