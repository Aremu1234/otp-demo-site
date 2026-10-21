"""
Mini demo site that copies your real login flow:
  "Sign in with Google" button -> emails an OTP from "ARP Digital"
  (subject "OTP Verification Code") -> OTP page -> long dashboard page.

Run:  python app.py        then open http://localhost:5000

Env vars (to send real emails):
  GMAIL_ADDRESS       the Gmail that sends AND receives the test OTP
  GMAIL_APP_PASSWORD  16-character Google App Password
If they are missing, the OTP is printed in the terminal instead.
"""
import hashlib
import os
import random
import smtplib
import time
from email.message import EmailMessage
from email.utils import formataddr

from flask import Flask, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "demo-only-secret-change-me")

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
SENDER_NAME = "ARP Digital"
SUBJECT = "OTP Verification Code"
OTP_TTL = 300  # seconds

def hash_code(code):
    """Stateless OTP check: only a hash of the code lives in the signed cookie."""
    return hashlib.sha256(f"{app.secret_key}:{code}".encode()).hexdigest()

PAGE = """
<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title>
<style>
  body{font-family:system-ui,sans-serif;margin:0;background:#f4f6fa;color:#1c2430}
  .wrap{max-width:900px;margin:40px auto;padding:0 20px}
  .card{background:#fff;border-radius:12px;padding:28px;box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:20px}
  button,.btn{background:#1a73e8;color:#fff;border:0;border-radius:8px;padding:12px 20px;font-size:16px;cursor:pointer;text-decoration:none;display:inline-block}
  input{padding:12px;font-size:18px;border:1px solid #c5ccd6;border-radius:8px;width:200px;letter-spacing:4px}
  .err{color:#c0392b}
  table{width:100%;border-collapse:collapse}
  td,th{padding:10px;border-bottom:1px solid #e3e7ee;text-align:left}
</style></head><body><div class="wrap">{{ body|safe }}</div></body></html>
"""


def render(title, body):
    return render_template_string(PAGE, title=title, body=body)


def send_otp_email(code):
    if not (GMAIL_ADDRESS and GMAIL_APP_PASSWORD):
        print(f"[demo] No Gmail creds set. OTP is: {code}")
        return
    msg = EmailMessage()
    msg["From"] = formataddr((SENDER_NAME, GMAIL_ADDRESS))
    msg["To"] = GMAIL_ADDRESS
    msg["Subject"] = SUBJECT
    msg.set_content(f"Your verification code is {code}. It expires in 5 minutes.")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        s.send_message(msg)


@app.route("/")
def home():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    return render(
        "Demo Sign in",
        '<div class="card"><h1>Welcome to the Demo Portal</h1>'
        "<p>Please sign in to continue.</p>"
        '<a class="btn" href="/send-otp">Sign in with Google</a></div>',
    )


@app.route("/send-otp")
def send_otp():
    code = f"{random.randint(0, 999999):06d}"
    session["otp_hash"] = hash_code(code)
    session["otp_exp"] = time.time() + OTP_TTL
    send_otp_email(code)
    return redirect(url_for("verify"))


@app.route("/verify", methods=["GET", "POST"])
def verify():
    error = ""
    if request.method == "POST":
        submitted = request.form.get("otp", "").strip()
        stored = session.get("otp_hash")
        expires = session.get("otp_exp", 0)
        if stored and time.time() < expires and hash_code(submitted) == stored:
            session.pop("otp_hash", None)
            session.pop("otp_exp", None)
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        error = '<p class="err">Invalid or expired code.</p>'
    return render(
        "Verify OTP",
        '<div class="card"><h1>Enter your verification code</h1>'
        "<p>We emailed a 6-digit code.</p>"
        f'{error}<form method="post"><input type="text" name="otp" maxlength="6" '
        'placeholder="000000" autofocus> <button type="submit">Verify</button></form></div>',
    )


@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("home"))
    rows = "".join(
        f"<tr><td>2026-10-{d:02d}</td><td>Order #{1000 + d}</td><td>${d * 37 % 500 + 20}.00</td></tr>"
        for d in range(1, 31)
    )
    body = (
        '<div class="card"><h1>Dashboard (logged in)</h1>'
        f"<p>Page generated at {time.strftime('%Y-%m-%d %H:%M:%S')}</p></div>"
        '<div class="card"><h2>Recent orders</h2><table><tr><th>Date</th><th>Order</th><th>Amount</th></tr>'
        f"{rows}</table></div>"
        '<div class="card"><h2>Footer section</h2><p>If your screenshot shows this, the full page was captured.</p></div>'
    )
    return render("Dashboard", body)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
