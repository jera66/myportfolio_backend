import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_user = os.environ.get('SMTP_USER', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.admin_email = os.environ.get('ADMIN_EMAIL', 'jerathelczerny@yahoo.com')
        self.enabled = bool(self.smtp_user and self.smtp_password)
        
        if not self.enabled:
            logger.warning("Email service not configured. Set SMTP_USER and SMTP_PASSWORD to enable.")

    async def send_contact_notification(self, name: str, email: str, subject: str, message: str):
        """Send email notification when contact form is submitted"""
        if not self.enabled:
            logger.info(f"Email notification skipped (not configured). Contact from: {name} <{email}>")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'Portfolio Contact: {subject}'
            msg['From'] = self.smtp_user
            msg['To'] = self.admin_email

            # HTML content
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f4f4;">
                        <div style="background-color: #1e3a5f; color: white; padding: 20px; text-align: center;">
                            <h2 style="margin: 0;">New Contact Form Submission</h2>
                        </div>
                        <div style="background-color: white; padding: 30px; margin-top: 20px; border-radius: 8px;">
                            <h3 style="color: #8b2635; margin-top: 0;">Contact Details</h3>
                            <p><strong>Name:</strong> {name}</p>
                            <p><strong>Email:</strong> <a href="mailto:{email}" style="color: #8b2635;">{email}</a></p>
                            <p><strong>Subject:</strong> {subject}</p>
                            
                            <h3 style="color: #8b2635; margin-top: 30px;">Message</h3>
                            <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #8b2635; border-radius: 4px;">
                                <p style="margin: 0; white-space: pre-wrap;">{message}</p>
                            </div>
                        </div>
                        <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
                            <p>This email was sent from your portfolio contact form.</p>
                        </div>
                    </div>
                </body>
            </html>
            """

            # Plain text fallback
            text_content = f"""
            New Contact Form Submission
            
            Name: {name}
            Email: {email}
            Subject: {subject}
            
            Message:
            {message}
            
            ---
            This email was sent from your portfolio contact form.
            """

            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True
            )

            logger.info(f"Email notification sent successfully to {self.admin_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False

email_service = EmailService()
