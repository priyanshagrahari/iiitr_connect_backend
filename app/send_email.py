import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import MAIL_PORT, MAIL_HOST, MAIL_USERNAME, MAIL_PASSWORD

def send_email_otp( otp = 0, send_to = "cs20b1014@iiitr.ac.in" ):
  port = MAIL_PORT
  smtp_server = MAIL_HOST
  sender_email = MAIL_USERNAME
  password = MAIL_PASSWORD
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

#send_email_otp(652987, "bemanuela3@gmail.com")