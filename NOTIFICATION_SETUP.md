# Smart Blood Bank - Notification Feature Setup Guide

## Overview
The notification feature sends automatic email alerts when:
- **New donor matches a blood request** - Hospitals are notified of available donors
- **New donor registered** - Donor receives confirmation, hospitals are notified if they have pending requests
- **New request created** - System matches with existing donors and notifies if matches found

---

## Email Configuration Setup

### Step 1: Enable Email Credentials

Open `app.py` and update the email configuration section (around line 10-14):

```python
# --------------- EMAIL CONFIGURATION --------------- #
# Configure your email credentials here
EMAIL_ADDRESS = "your-email@gmail.com"  # Change this
EMAIL_PASSWORD = "your-app-password"    # Use app-specific password for Gmail
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
```

### Step 2: Get Gmail App Password (Recommended)

For **Gmail accounts** (most secure method):

1. Go to [Google Account Security Settings](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (if not already enabled)
3. Generate an **App Password**:
   - Security → App passwords → Select "Mail" and "Windows Computer"
   - Google will generate a 16-character password
4. Copy this 16-character password to `EMAIL_PASSWORD`

**Example:**
```python
EMAIL_ADDRESS = "mybloodbank@gmail.com"
EMAIL_PASSWORD = "abcd efgh ijkl mnop"  # 16-character app password
```

### Step 3: For Other Email Providers

| Provider | SMTP Server | SMTP Port |
|----------|-----------|-----------|
| Gmail | smtp.gmail.com | 587 |
| Outlook | smtp-mail.outlook.com | 587 |
| Yahoo | smtp.mail.yahoo.com | 587 |
| Office 365 | smtp.office365.com | 587 |

---

## How to Use the Feature

### Adding a New Donor with Email

1. Go to **Add New Donor**
2. Fill in all donor details
3. **NEW:** Add donor's email address in "Email (for notifications)" field
4. Submit - Donor receives confirmation email, hospitals with pending requests are notified

### Creating a Blood Request with Email

1. Go to **Create Request**
2. Fill in all request details
3. **NEW:** Add hospital email address in "Hospital Email (for notifications)" field
4. Submit - Matching donors are found and hospital is notified immediately

### Viewing Notifications

1. Go to **Admin Dashboard**
2. Click **Notifications** button
3. View all sent notifications:
   - Match Found (green badge) - Donor matched with request
   - Donor Registered (blue badge) - New donor registered
   - New Donor (primary badge) - Notification to hospitals about new donor

---

## Email Templates

### Donor Registration Email
```
Subject: ✅ New Donor Available - [Blood Group]

Thank you for registering as a donor!

Your blood group: [Blood Group]

We will contact you when your blood type is needed.
Blood Bank Management System
```

### Donor Match Alert (to Hospital)
```
Subject: 🩸 Blood Match Found - [Blood Group]

Blood Request Match Alert!

We found X potential donor(s) for blood group [Blood Group]:
[Donor Names]

Please contact the donors immediately.

Blood Bank Management System
```

---

## Troubleshooting

### Email Not Sending?

1. **Check credentials** - Verify EMAIL_ADDRESS and EMAIL_PASSWORD are correct
2. **App Password for Gmail** - Make sure you're using a 16-character app password, NOT your account password
3. **2-Step Verification** - Gmail requires 2-Step Verification enabled
4. **Check spam folder** - Emails might be marked as spam
5. **View terminal logs** - Error messages print to console

### Testing Email Configuration

Add a test route to app.py temporarily:
```python
@app.route("/test-email")
def test_email():
    result = send_email(
        "recipient@example.com",
        "Test Email",
        "This is a test email from Blood Bank System"
    )
    return f"Email sent: {result}"
```

Then visit `http://localhost:5000/test-email`

---

## Database Tables

### Notification Table
```sql
CREATE TABLE notification(
    id INTEGER PRIMARY KEY,
    recipient_email TEXT,
    recipient_type TEXT,          -- 'donor' or 'hospital'
    subject TEXT,
    message TEXT,
    notification_type TEXT,        -- 'match_found', 'donor_registered', 'new_donor'
    created_at TIMESTAMP,
    is_sent INTEGER DEFAULT 0      -- 0: pending, 1: sent
)
```

---

## Features Added

### Modified Tables
- **donor table**: Added `email TEXT` field
- **request table**: Added `hospital_email TEXT` field

### New Functions
- `send_email()` - Sends email via SMTP
- `create_notification()` - Logs notification in database
- `check_donor_request_match()` - Finds matching donors for blood request
- `notify_on_new_donor()` - Notifies all relevant parties when donor added

### New Route
- `/notifications` - View all notifications history (admin only)

### Updated Routes
- `/add_donor` - Now triggers donor notification emails
- `/add_request` - Now triggers donor matching and email alerts

---

## Security Notes

1. **Never commit real credentials** - Add `.gitignore` entry for app.py with real credentials
2. **Use environment variables** (optional enhancement):
   ```python
   import os
   EMAIL_ADDRESS = os.environ.get('BLOOD_BANK_EMAIL')
   EMAIL_PASSWORD = os.environ.get('BLOOD_BANK_PASSWORD')
   ```
3. **Email passwords are app-specific** - Use 16-character app passwords for Gmail
4. **Consider rate limiting** - In production, add rate limiting to prevent email spam

---

## Future Enhancements

- [ ] SMS notifications via Twilio
- [ ] In-app notification dashboard with unread count
- [ ] Notification preferences (choose what to receive)
- [ ] Email templates with HTML formatting
- [ ] Scheduled summary emails
- [ ] Push notifications for mobile app
- [ ] Donor confirmation before sharing contact info

---

## Support

For issues or questions, check the terminal output for error messages or consult the Flask documentation.
