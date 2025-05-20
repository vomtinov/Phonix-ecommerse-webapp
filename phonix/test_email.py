import smtplib
from email.mime.text import MIMEText

sender = "thomasbaby273@gmail.com"
receiver = "thomasbaby273@gmail.com"  # Replace with a real email
password = "rpvr xsou konm lfph"  # Replace with your actual App Password

msg = MIMEText("This is a test email.")
msg['Subject'] = 'Test Email'
msg['From'] = sender
msg['To'] = receiver

try:
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
    print("Email sent successfully!")
except Exception as e:
    print(f"Failed: {e}")