import json
import logging
from typing import Optional, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ParsedEmailEvent(BaseModel):
    message_id: str
    email_to: str
    email_from: str
    subject: str
    event_type: str  # send, delivery, bounce, complaint, open, click
    event_data: dict[str, Any]
    timestamp: str
    tenant_id: int


def parse_sns_message(raw_body: dict, tenant_id: int) -> Optional[ParsedEmailEvent]:
    """Parse SNS notification into a structured email event."""
    try:
        # Handle SNS subscription confirmation
        if raw_body.get("Type") == "SubscriptionConfirmation":
            return None

        if raw_body.get("Type") != "Notification":
            logger.warning("Unknown SNS message type: %s", raw_body.get("Type"))
            return None

        message = raw_body.get("Message", {})
        if isinstance(message, str):
            message = json.loads(message)

        mail = message.get("mail", {})
        notification = message.get("notification", {})

        # Extract email metadata
        message_id = mail.get("messageId", "")
        source = mail.get("source", "")
        common_headers = mail.get("commonHeaders", {})
        subject = common_headers.get("subject", "")
        destination = mail.get("destination", [])

        # Get recipient from notification or destination
        email_to = ""
        if notification:
            # For bounce/complaint, get from bouncedRecipients/complainedRecipients
            recipients = notification.get("bouncedRecipients", []) or \
                        notification.get("complainedRecipients", [])
            if recipients:
                email_to = recipients[0].get("emailAddress", "")
        
        if not email_to and destination:
            email_to = destination[0] if isinstance(destination, list) else destination

        # Determine event type
        event_type = _determine_event_type(message, notification)

        # Build event data
        event_data = {
            "timestamp": mail.get("timestamp", ""),
            "source": source,
            "subject": subject,
        }

        # Add type-specific data
        if event_type == "bounce":
            event_data.update({
                "bounceType": notification.get("bounceType", ""),
                "bounceSubType": notification.get("bounceSubType", ""),
                "bouncedRecipients": notification.get("bouncedRecipients", []),
            })
        elif event_type == "complaint":
            event_data.update({
                "complaintFeedbackType": notification.get("complaintFeedbackType", ""),
                "complainedRecipients": notification.get("complainedRecipients", []),
            })
        elif event_type == "delivery":
            event_data.update({
                "smtpResponse": notification.get("delivery", {}).get("smtpResponse", ""),
                "reportingMTA": notification.get("delivery", {}).get("reportingMTA", ""),
            })
        elif event_type == "click":
            event_data.update({
                "ipAddress": notification.get("click", {}).get("ipAddress", ""),
                "link": notification.get("click", {}).get("link", ""),
            })
        elif event_type == "open":
            event_data.update({
                "ipAddress": notification.get("open", {}).get("ipAddress", ""),
                "userAgent": notification.get("open", {}).get("userAgent", ""),
            })

        return ParsedEmailEvent(
            message_id=message_id,
            email_to=email_to,
            email_from=source,
            subject=subject,
            event_type=event_type,
            event_data=event_data,
            timestamp=mail.get("timestamp", ""),
            tenant_id=tenant_id,
        )

    except Exception as e:
        logger.error("Error parsing SNS message: %s", e, exc_info=True)
        return None


def _determine_event_type(message: dict, notification: dict) -> str:
    """Determine the SES event type from SNS notification."""
    if not notification:
        return "send"

    notification_type = notification.get("type", "").lower()

    type_map = {
        "bounce": "bounce",
        "complaint": "complaint",
        "delivery": "delivery",
        "send": "send",
        "open": "open",
        "click": "click",
        "rendering failure": "rendering_failure",
        "reject": "reject",
    }

    return type_map.get(notification_type, "send")
