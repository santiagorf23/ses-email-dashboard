import logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SendEmailRequest(BaseModel):
    """Request to send email via SES."""
    to: list[str]
    subject: str
    html_body: str
    text_body: Optional[str] = None
    reply_to: Optional[str] = None
    source: Optional[str] = None


class SendEmailResponse(BaseModel):
    """Response from SES send email."""
    message_id: str
    status: str
    timestamp: datetime


class SESService:
    """AWS SES email sending service."""
    
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, region: str = "us-east-1"):
        self.client = boto3.client(
            'ses',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region
        )
    
    def send_email(self, request: SendEmailRequest, source: str) -> SendEmailResponse:
        """Send email via SES."""
        try:
            # Build message
            message = {
                'Subject': {'Data': request.subject, 'Charset': 'UTF-8'},
                'Body': {}
            }
            
            # Add HTML body
            if request.html_body:
                message['Body']['Html'] = {'Data': request.html_body, 'Charset': 'UTF-8'}
            
            # Add text body
            if request.text_body:
                message['Body']['Text'] = {'Data': request.text_body, 'Charset': 'UTF-8'}
            elif request.html_body:
                # Auto-generate text from HTML (simple strip)
                import re
                text = re.sub(r'<[^>]+>', '', request.html_body)
                text = re.sub(r'\s+', ' ', text).strip()
                message['Body']['Text'] = {'Data': text, 'Charset': 'UTF-8'}
            
            # Build kwargs
            kwargs = {
                'Source': source,
                'Destination': {'ToAddresses': request.to},
                'Message': message
            }
            
            # Add reply-to if provided
            if request.reply_to:
                kwargs['ReplyToAddresses'] = [request.reply_to]
            
            # Send email
            response = self.client.send_email(**kwargs)
            
            return SendEmailResponse(
                message_id=response['MessageId'],
                status='sent',
                timestamp=datetime.now(timezone.utc)
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"SES send error: {error_code} - {error_message}")
            raise Exception(f"Error sending email: {error_message}")
    
    def verify_email_identity(self, email: str) -> bool:
        """Verify email identity with SES."""
        try:
            self.client.verify_email_identity(EmailAddress=email)
            return True
        except ClientError as e:
            logger.error(f"SES verify error: {e}")
            return False
    
    def get_send_quota(self) -> dict:
        """Get SES send quota."""
        try:
            response = self.client.get_send_quota()
            return {
                'max_24_hour': response['Max24HourSend'],
                'max_per_second': response['MaxSendRate'],
                'sent_last_24_hours': response['SentLast24Hours']
            }
        except ClientError as e:
            logger.error(f"SES quota error: {e}")
            return {}
    
    def get_send_statistics(self) -> dict:
        """Get SES send statistics."""
        try:
            response = self.client.get_send_statistics()
            return response['SendDataPoints']
        except ClientError as e:
            logger.error(f"SES stats error: {e}")
            return {}


# Global instance
ses_service: Optional[SESService] = None


def get_ses_service() -> Optional[SESService]:
    """Get SES service instance."""
    return ses_service


def init_ses_service(aws_access_key_id: str, aws_secret_access_key: str, region: str = "us-east-1") -> SESService:
    """Initialize SES service."""
    global ses_service
    ses_service = SESService(aws_access_key_id, aws_secret_access_key, region)
    return ses_service
