from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import json

email_address = ""
email_password = ""
email_smtp_server = "smtp-mail.outlook.com"
email_smtp_port = 587


def send_email(address, content):
    print("The meail sending function")
    reciever = address
    msg = MIMEMultipart("alternative")
    msg['From'] = "Amamzon Price Tracker"
    msg['To'] = reciever
    msg['Subject'] = "Price Dropped!"

    data = ""
    print("THE CONTENT IS", content)
    print("the type of content is", type(content))
    s = smtplib.SMTP(email_smtp_server, email_smtp_port)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(email_address, email_password)
    s.sendmail(email_address, "prawjeenkhadka@gmail.com", "hi")
    s.quit()
    print('Email Sent to '+address)
    print("Here is the changed email address") 

    topic_arn = 'your_sns_topic_arn'
    print("Sent to SNS")

send_email(address = "a", content = "b")
