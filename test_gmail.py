from console import console
from gmail_service import GmailService

console.title("MailCleaner Gmail Test")

gmail = GmailService()

gmail.connect()

if gmail.verify_connection():

    console.success("Connected to Gmail")

    profile = gmail.get_profile()

    print()

    print(f"Email      : {profile.email_address}")
    print(f"Messages   : {profile.messages_total}")
    print(f"Threads    : {profile.threads_total}")
    print(f"History ID : {profile.history_id}")

else:

    console.error("Connection failed")