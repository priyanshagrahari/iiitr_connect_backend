import os
import dotenv

dotenv.load_dotenv()

MAIL_HOST       = os.environ.get("MAIL_HOST")
MAIL_PORT       = os.environ.get("MAIL_PORT")
MAIL_USERNAME   = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD   = os.environ.get("MAIL_PASSWORD")

DB_HOST         = os.environ.get("DB_HOST")
DB_PORT         = os.environ.get("DB_PORT")
DB_NAME         = os.environ.get("DB_NAME")
DB_USERNAME     = os.environ.get("DB_USER")
DB_PASSWORD     = os.environ.get("DB_PASSWORD")