def fetch_message_ids(service, max_results=100):
    """
    Fetches the latest message IDs from Gmail.
    """

    response = service.users().messages().list(
        userId="me",
        maxResults=max_results
    ).execute()

    messages = response.get("messages", [])

    print(f"\nDownloaded {len(messages)} message IDs.")

    return messages