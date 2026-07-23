from dataclasses import dataclass
import email.utils

@dataclass(slots=True)
class SenderInfo:
    display_name: str
    email: str
    domain: str

def parse_sender(sender: str) -> SenderInfo:
    """
    Parse a sender string into display name, email, and domain.
    
    Args:
        sender: The sender string to parse. Can be in the format:
            "Display Name <email@domain>", "email@domain", or empty.
    
    Returns:
        SenderInfo object with parsed information. For empty or malformed inputs,
        returns a SenderInfo with empty strings.
    """
    if not sender:
        return SenderInfo("", "", "")
    
    display_name, email_str = email.utils.parseaddr(sender)
    
    if email_str:
        # Extract domain from the email string
        if '@' in email_str:
            _, domain = email_str.split('@', 1)
        else:
            domain = ""
        return SenderInfo(display_name or "", email_str, domain)
    else:
        # Handle cases where parseaddr returned empty email
        if '@' in sender:
            email, domain = sender.split('@', 1)
            return SenderInfo("", email, domain)
        else:
            return SenderInfo("", "", "")
