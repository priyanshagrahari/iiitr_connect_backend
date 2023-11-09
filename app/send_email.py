from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from posixpath import basename
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import MAIL_PORT, MAIL_HOST, MAIL_USERNAME, MAIL_PASSWORD

port = MAIL_PORT
smtp_server = MAIL_HOST
sender_email = MAIL_USERNAME
password = MAIL_PASSWORD

def send_email_otp( otp = 0, send_to = "cs20b1014@iiitr.ac.in" ):
    otp_text = f'{otp:04}'

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Your OTP is {otp_text} | IIITR Connect"
    message["From"] = sender_email
    message["To"] = send_to

    text = f"""\
    Your OTP for logging in is:
    {otp_text}
    Please enter it on the login page to access your account.
    Have a nice day :)"""
    html = f"""\
    <html>
        <body>
        <h3>IIITR Connect Login OTP</h3>
        <p>Your OTP for logging in is</p> 
        <h1>{otp_text}</h1>
        <p>Please enter it on the login page to access your account.
        <br>Have a nice day :)</p>
        </body>
    </html>
    """
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login(sender_email, password)
        server.sendmail(sender_email, send_to, message.as_string())

def send_encoding_reminder_email( roll_num : str ):
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Face recognition data expired | IIITR Connect"
    message["From"] = sender_email
    message["To"] = f"{roll_num}@iiitr.ac.in"

    text = f"""\
    The face encodings associated with you have expired.
    Please open the IIITR Connect app and provide updated data.
    This helps professors easily mark your attendance through face recognition.
    Have a nice day :)"""
    html = f"""\
    <html>
        <body>
        <h3>IIITR Connect Reminder</h3>
        <p>The face encodings associated with you have expired. <br>
        Please open the IIITR Connect app and provide updated data.</p>
        <p>This helps professors easily mark your attendance through face recognition.
        <br>Have a nice day :)</p>
        </body>
    </html>
    """
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login(sender_email, password)
        server.sendmail(sender_email, f"{roll_num}@iiitr.ac.in", message.as_string())

def send_attendance_sheet_email( email : str, course_name : str, path : str ):
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Attendance Sheet for {course_name} | IIITR Connect"
    message["From"] = sender_email
    message["To"] = email

    text = f"""\
    Please find the requested attedance sheet for {course_name} attached.
    Have a nice day :)"""
    html = f"""\
    <html>
        <body>
        <h3>IIITR Connect Attendance Sheet</h3>
        <p>Please find the requested attedance sheet for {course_name} attached. <br>
        <p>Have a nice day :)</p>
        </body>
    </html>
    """
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)

    with open(path, "rb") as fil:
        part3 = MIMEApplication(
            fil.read(),
            Name=basename(path)
        )
    part3['Content-Disposition'] = 'attachment; filename="%s"' % basename(path)
    message.attach(part3)

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login(sender_email, password)
        server.sendmail(sender_email, email, message.as_string())
