import yagmail
from langchain.tools import tool
from app.core.config import settings, logger

@tool("send_email")
def send_email_tool(to_email: str, subject: str, body_html: str) -> str:
    """
    Sends an email with the final trip itinerary to the user.
    Args:
        to_email (str): The recipient's email address.
        subject (str): The subject line of the email.
        body_html (str): The HTML content of the email body, typically the final plan in Markdown.
    """
    if not (settings.GMAIL_SENDER_EMAIL and settings.GMAIL_APP_PASSWORD):
        return "Error: Email functionality is disabled because Gmail credentials are not configured."
    
    logger.info(f"Attempting to send email via yagmail to {to_email} with subject: {subject}")
    try:
        yag_client = yagmail.SMTP(
            user=settings.GMAIL_SENDER_EMAIL,
            password=settings.GMAIL_APP_PASSWORD
        )
        yag_client.send(
            to=to_email,
            subject=subject,
            contents=body_html
        )
        logger.info(f"Email sent successfully to {to_email}.")
        return f"Email with the trip plan has been successfully sent to {to_email}."
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending email via yagmail: {e}", exc_info=True)
        return f"An unexpected error occurred while sending the email: {str(e)}"