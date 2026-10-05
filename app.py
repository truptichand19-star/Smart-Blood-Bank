from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
import smtplib
import json

try:
    import requests
except ImportError:
    requests = None

app = Flask(__name__)
app.secret_key = "smartbloodbank"

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

# ---------------- NOTIFICATION HELPERS ---------------- #

def send_email(to_email, subject, body):
    mode = os.getenv("NOTIFICATION_MODE", "auto").lower()
    if mode in ("fake", "test", "dryrun", "none"):
        print(f"[EMAIL SIMULATION] to={to_email}, subject={subject}")
        return True, "Email simulated (non-paid mode)"

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL", smtp_user)

    if not smtp_user or not smtp_password or not from_email or not to_email:
        print("[EMAIL] live mode: missing config, switching to simulation")
        return True, "Email simulated (missing SMTP config)"

    message = f"Subject: {subject}\nFrom: {from_email}\nTo: {to_email}\n\n{body}"
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [to_email], message)
        return True, "Email sent"
    except Exception as e:
        print(f"[EMAIL] Exception: {e}")
        return False, str(e)


def send_sms(to_phone, message):
    mode = os.getenv("NOTIFICATION_MODE", "auto").lower()
    if mode in ("fake", "test", "dryrun", "none"):
        print(f"[SMS SIMULATION] to={to_phone}, msg={message}")
        return True, "SMS simulated (non-paid mode)"

    provider = os.getenv("SMS_PROVIDER", "auto").lower()
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_FROM")

    if provider == "auto":
        if all([twilio_sid, twilio_token, twilio_from]):
            provider = "twilio"
        else:
            provider = "textbelt"

    if provider == "twilio":
        try:
            from twilio.rest import Client
        except ImportError:
            print("[SMS] Twilio package not installed; install twilio via pip")
            return False, "Twilio package not installed"

        if not all([twilio_sid, twilio_token, twilio_from]):
            print("[SMS] Missing Twilio config")
            return False, "Missing Twilio configuration"

        try:
            client = Client(twilio_sid, twilio_token)
            sent = client.messages.create(body=message, from_=twilio_from, to=to_phone)
            print(f"[SMS] Twilio SID {sent.sid}")
            return True, "SMS sent via Twilio"
        except Exception as e:
            print(f"[SMS] Twilio error: {e}")
            return False, str(e)

    # Textbelt fallback
    if not requests:
        print("[SMS] requests module not installed; switching to simulation")
        return True, "SMS simulated (requests missing)"

    textbelt_api_key = os.getenv("TEXTBELT_API_KEY", "textbelt")
    data = {
        "phone": to_phone,
        "message": message,
        "key": textbelt_api_key,
    }

    try:
        resp = requests.post("https://textbelt.com/text", data=data, timeout=15)
        result = resp.json()
        if result.get("success"):
            return True, "SMS sent via Textbelt"
        print(f"[SMS] Textbelt error: {result.get('error')}")
        # fallback to simulated for blocked countries
        return True, f"SMS simulated (Textbelt: {result.get('error')})"
    except Exception as e:
        print(f"[SMS] Exception: {e}")
        return True, f"SMS simulated (exception: {e})"


# ---------------- DATABASE ---------------- #
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS admin(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS donor(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    age INTEGER,
                    blood_group TEXT,
                    phone TEXT,
                    city TEXT,
                    email TEXT)''')

    # add email column to existing donor table if missing
    c.execute("PRAGMA table_info(donor)")
    cols = [row[1] for row in c.fetchall()]
    if "email" not in cols:
        c.execute("ALTER TABLE donor ADD COLUMN email TEXT")

    c.execute('''CREATE TABLE IF NOT EXISTS request(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT,
                    blood_group TEXT,
                    units INTEGER,
                    hospital TEXT)''')

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ---------------- #
@app.route("/")
def index():
    return render_template("index.html")

# ---------------- ADMIN REGISTER ---------------- #
@app.route("/admin_register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO admin(username,password) VALUES (?,?)",
                      (username, password))
            conn.commit()
            flash("Admin Registered Successfully")
            return redirect("/admin_login")
        except:
            flash("Username already exists")
        conn.close()
    return render_template("admin_register.html")

# ---------------- ADMIN LOGIN ---------------- #
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM admin WHERE username=? AND password=?",
                  (username, password))
        admin = c.fetchone()
        conn.close()

        if admin:
            session["admin"] = username
            return redirect("/dashboard")
        else:
            flash("Invalid Credentials")

    return render_template("admin_login.html")

# ---------------- DASHBOARD ---------------- #
@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect("/admin_login")
    return render_template("dashboard.html")

# ---------------- ADD DONOR ---------------- #
@app.route("/add_donor", methods=["GET", "POST"])
def add_donor():
    if request.method == "POST":
        donor_name = request.form["name"]
        donor_age = request.form["age"]
        donor_blood_group = request.form["blood_group"]
        donor_phone = request.form["phone"]
        donor_city = request.form["city"]
        donor_email = request.form.get("email", "")

        data = (
            donor_name,
            donor_age,
            donor_blood_group,
            donor_phone,
            donor_city,
            donor_email,
        )

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO donor(name,age,blood_group,phone,city,email) VALUES (?,?,?,?,?,?)", data)
        conn.commit()
        conn.close()

        sms_body = f"Hi {donor_name}, thank you for registering as a {donor_blood_group} blood donor at Smart Blood Bank."
        email_subject = "Blood Donor Registration Confirmed"
        email_body = f"Dear {donor_name},\n\nThank you for registering as a blood donor (group: {donor_blood_group}) with Smart Blood Bank. We may contact you when a match is needed.\n\nStay safe.\n"

        sms_status, sms_msg = send_sms(donor_phone, sms_body)
        email_status, email_msg = (False, "Email not configured")
        if donor_email:
            email_status, email_msg = send_email(donor_email, email_subject, email_body)

        flash("Donor Added Successfully")
        if sms_status:
            flash("SMS notification sent to donor")
        else:
            flash(f"SMS notification failed: {sms_msg}")

        if donor_email:
            if email_status:
                flash("Registration confirmation email sent")
            else:
                flash(f"Email notification failed: {email_msg}")
        else:
            flash("Donor email missing; email not sent")

        return redirect("/view_donor")

    return render_template("add_donor.html")

# ---------------- VIEW DONOR ---------------- #
@app.route("/view_donor")
def view_donor():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM donor")
    donors = c.fetchall()
    conn.close()
    return render_template("view_donor.html", donors=donors)

# ---------------- SEARCH DONOR ---------------- #
@app.route("/search_donor", methods=["GET", "POST"])
def search_donor():
    donors = []
    if request.method == "POST":
        blood_group = request.form["blood_group"]
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM donor WHERE blood_group=?", (blood_group,))
        donors = c.fetchall()
        conn.close()
    return render_template("search_donor.html", donors=donors)

# ---------------- ADD REQUEST ---------------- #
@app.route("/add_request", methods=["GET", "POST"])
def add_request():
    if request.method == "POST":
        patient_name = request.form["patient_name"]
        requested_blood_group = request.form["blood_group"]
        units = request.form["units"]
        hospital = request.form["hospital"]

        data = (patient_name, requested_blood_group, units, hospital)

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO request(patient_name,blood_group,units,hospital) VALUES (?,?,?,?)", data)
        conn.commit()

        # Notify donors of matching blood group
        c.execute("SELECT name, phone, email FROM donor WHERE blood_group=?", (requested_blood_group,))
        matched_donors = c.fetchall()
        conn.close()

        notified_count = 0
        for donor in matched_donors:
            d_name, d_phone, d_email = donor
            message = (f"Urgent: Patient {patient_name} requires {units} unit(s) of {requested_blood_group} blood "
                       f"at {hospital}. Please respond if you are available to donate.")

            sms_status, sms_msg = send_sms(d_phone, message)
            email_status, email_msg = (False, "Email not configured")
            if d_email:
                subject = "Urgent Blood Donation Request"
                email_status, email_msg = send_email(d_email, subject, message)

            if sms_status or email_status:
                notified_count += 1

        flash("Request Added Successfully")
        if matched_donors:
            flash(f"Notified {notified_count} matching donor(s) by SMS/email.")
        else:
            flash("No matching donors found to notify yet.")

        return redirect("/view_request")

    return render_template("add_request.html")

# ---------------- VIEW REQUEST ---------------- #
@app.route("/view_request")
def view_request():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM request")
    requests = c.fetchall()
    conn.close()
    return render_template("view_request.html", requests=requests)

# ---------------- LOGOUT ---------------- #
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
















