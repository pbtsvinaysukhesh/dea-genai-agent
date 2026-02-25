"""
Enhanced Mailer for On-Device AI Memory Intelligence Agent
Improved error handling, retry logic, and email delivery
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import time
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MailerConfig:
    """Configuration for email sending"""
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    CONNECTION_TIMEOUT = 30  # seconds


class Mailer:
    """
    Enhanced mailer with retry logic and better error handling
    """
    
    def __init__(self, email_config: dict, config: MailerConfig = None):
        self.config = config or MailerConfig()
        
        # Email server settings
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.username = os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")
        
        # Recipients
        self.recipients = email_config.get('recipients', [])
        self.cc_recipients = email_config.get('cc', [])
        self.bcc_recipients = email_config.get('bcc', [])
        
        # Validate configuration
        self._validate_config()
        
        # Statistics
        self.stats = {
            'emails_sent': 0,
            'emails_failed': 0,
            'retries': 0
        }
    
    def _validate_config(self):
        """Validate email configuration"""
        if not self.username or not self.password:
            logger.warning("Email credentials not configured - emails will not be sent")
            return False
        
        if not self.recipients:
            logger.warning("No recipients configured - emails will not be sent")
            return False
        
        return True
    
    def send(
        self, 
        html_content: str, 
        subject: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        retry_count: int = 0
    ) -> bool:
        """
        Send HTML email with optional attachments
        
        Args:
            html_content: HTML body of email
            subject: Email subject (default: generated from date)
            attachments: List of file paths to attach
            retry_count: Current retry attempt (internal use)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Check if email is configured
        if not self.username or not self.password:
            logger.warning("Email credentials not found. Skipping email dispatch.")
            return False
        
        if not self.recipients:
            logger.warning("No recipients configured. Skipping email dispatch.")
            return False
        
        # Generate subject if not provided
        if not subject:
            today = datetime.now().strftime("%B %d, %Y")
            subject = f"On-Device AI Memory Intelligence - {today}"
        
        try:
            # Create message
            msg = self._create_message(html_content, subject, attachments)
            
            # Send email
            logger.info(f"Sending email to {len(self.recipients)} recipient(s)...")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.config.CONNECTION_TIMEOUT) as server:
                # Enable TLS
                server.starttls()
                
                # Login
                server.login(self.username, self.password)
                
                # Send email
                all_recipients = self.recipients + self.cc_recipients + self.bcc_recipients
                server.sendmail(self.username, all_recipients, msg.as_string())
            
            logger.info("[OK] Email sent successfully")
            self.stats['emails_sent'] += 1
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            logger.error("Check SMTP_USER and SMTP_PASSWORD environment variables")
            self.stats['emails_failed'] += 1
            return False
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            
            # Retry logic
            if retry_count < self.config.MAX_RETRIES:
                return self._retry_send(html_content, subject, attachments, retry_count, str(e))
            else:
                logger.error(f"Failed to send email after {self.config.MAX_RETRIES} attempts")
                self.stats['emails_failed'] += 1
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            
            # Retry logic for general errors
            if retry_count < self.config.MAX_RETRIES:
                return self._retry_send(html_content, subject, attachments, retry_count, str(e))
            else:
                self.stats['emails_failed'] += 1
                return False
    
    def _create_message(
        self, 
        html_content: str, 
        subject: str,
        attachments: Optional[List[str]] = None
    ) -> MIMEMultipart:
        """
        Create email message with HTML content and attachments
        
        Args:
            html_content: HTML body
            subject: Email subject
            attachments: List of file paths to attach
            
        Returns:
            MIMEMultipart message object
        """
        # Create message container
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = self.username
        msg['To'] = ", ".join(self.recipients)
        
        if self.cc_recipients:
            msg['Cc'] = ", ".join(self.cc_recipients)
        
        # Add custom headers
        msg['X-Priority'] = '3'  # Normal priority
        msg['X-Mailer'] = 'On-Device AI Intelligence Agent v1.0'
        
        # Create alternative part for HTML/text
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)
        
        # Add plain text version (fallback)
        text_content = self._html_to_text(html_content)
        msg_text = MIMEText(text_content, 'plain', 'utf-8')
        msg_alternative.attach(msg_text)
        
        # Add HTML version
        msg_html = MIMEText(html_content, 'html', 'utf-8')
        msg_alternative.attach(msg_html)
        
        # Add attachments if any
        if attachments:
            for filepath in attachments:
                self._attach_file(msg, filepath)
        
        return msg
    
    def _attach_file(self, msg: MIMEMultipart, filepath: str):
        """
        Attach a file to the email message
        
        Args:
            msg: Message object to attach to
            filepath: Path to file
        """
        try:
            if not os.path.exists(filepath):
                logger.warning(f"Attachment not found: {filepath}")
                return
            
            filename = os.path.basename(filepath)
            
            with open(filepath, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {filename}')
            msg.attach(part)
            
            logger.info(f"Attached file: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to attach file {filepath}: {e}")
    
    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to plain text (simple version)
        
        Args:
            html: HTML string
            
        Returns:
            Plain text version
        """
        try:
            import re
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html)
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove leading/trailing whitespace
            text = text.strip()
            
            return text
            
        except Exception as e:
            logger.error(f"Error converting HTML to text: {e}")
            return "On-Device AI Memory Intelligence Report (view HTML version for formatted content)"
    
    def _retry_send(
        self,
        html_content: str,
        subject: str,
        attachments: Optional[List[str]],
        retry_count: int,
        error_msg: str
    ) -> bool:
        """
        Retry sending email with exponential backoff
        
        Args:
            html_content: Email content
            subject: Email subject
            attachments: File attachments
            retry_count: Current retry count
            error_msg: Previous error message
            
        Returns:
            True if successful, False otherwise
        """
        retry_count += 1
        self.stats['retries'] += 1
        
        delay = self.config.RETRY_DELAY * retry_count
        logger.warning(f"Retry {retry_count}/{self.config.MAX_RETRIES} after {delay}s (reason: {error_msg})")
        time.sleep(delay)
        
        return self.send(html_content, subject, attachments, retry_count)
    
    def send_test_email(self) -> bool:
        """
        Send a test email to verify configuration
        
        Returns:
            True if successful, False otherwise
        """
        test_html = """
        <html>
        <body>
            <h1>Test Email</h1>
            <p>This is a test email from the On-Device AI Memory Intelligence Agent.</p>
            <p>If you received this, your email configuration is working correctly.</p>
            <p><strong>Configuration:</strong></p>
            <ul>
                <li>SMTP Server: {server}</li>
                <li>SMTP Port: {port}</li>
                <li>Recipients: {recipients}</li>
            </ul>
        </body>
        </html>
        """.format(
            server=self.smtp_server,
            port=self.smtp_port,
            recipients=", ".join(self.recipients)
        )
        
        return self.send(test_html, subject="Test Email - On-Device AI Intelligence Agent")
    
    def get_statistics(self) -> dict:
        """Get email sending statistics"""
        return {**self.stats}
    
    def reset_statistics(self):
        """Reset statistics counters"""
        for key in self.stats:
            self.stats[key] = 0


# Utility function for sending notification emails
def send_error_notification(mailer: Mailer, error_details: str):
    """
    Send error notification email to admins
    
    Args:
        mailer: Mailer instance
        error_details: Details of the error
    """
    error_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2 style="color: #d32f2f;">⚠️ Pipeline Error Alert</h2>
        <p>The On-Device AI Memory Intelligence Agent encountered an error:</p>
        <div style="background: #f5f5f5; padding: 15px; border-left: 4px solid #d32f2f; margin: 20px 0;">
            <pre>{error_details}</pre>
        </div>
        <p><strong>Time:</strong> {datetime.now().isoformat()}</p>
        <p>Please check the logs for more details.</p>
    </body>
    </html>
    """
    
    try:
        mailer.send(error_html, subject="🚨 Pipeline Error - Immediate Attention Required")
    except Exception as e:
        logger.error(f"Failed to send error notification: {e}")