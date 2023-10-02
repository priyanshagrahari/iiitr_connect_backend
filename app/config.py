import os
import dotenv

dotenv.load_dotenv()

MAIL_HOST       = os.environ.get("MAIL_HOST")
MAIL_PORT       = os.environ.get("MAIL_PORT")
MAIL_USERNAME   = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD   = os.environ.get("MAIL_PASSWORD")

DB_URL          = os.environ.get("DB_URL")
DB_USER         = os.environ.get("DB_USER")
DB_HOST         = os.environ.get("DB_HOST")
DB_DATABASE     = os.environ.get("DB_DATABASE")
DB_PASSWORD     = os.environ.get("DB_PASSWORD")