from auth import authenticate
from gmail_service import get_gmail_service
from database import initialize_database
from label_analyzer import print_labels
from email_analyzer import list_recent_messages
from sync_engine import fetch_message_ids


def main():
    print("=" * 50)
    print(" Gmail Cleaner")
    print("=" * 50)

    # Authenticate
    creds = authenticate()

    # Initialize database
    initialize_database()

    # Create Gmail service
    service = get_gmail_service(creds)

    # Get Gmail profile
    profile = service.users().getProfile(userId="me").execute()

    print(f"Connected to      : {profile['emailAddress']}")
    print(f"Total Messages    : {profile['messagesTotal']}")
    print(f"Total Threads     : {profile['threadsTotal']}")

    # Display Gmail Labels
    print_labels(service)

    # Display Recent Emails
    list_recent_messages(service)

    # Fetch latest message IDs
    messages = fetch_message_ids(service)

    print(f"\nFetched {len(messages)} message IDs.")

    print("\n✅ Authentication Successful")


if __name__ == "__main__":
    main()