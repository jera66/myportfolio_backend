"""
Email Service Module - Resend Integration

This module handles email notifications for the portfolio contact form.
Uses Resend API for reliable email delivery via HTTPS (bypasses SMTP restrictions).

CONFIGURATION (backend/.env):
    RESEND_API_KEY: Your Resend API key (starts with 're_...')
    SENDER_EMAIL: Email address to send from (default: onboarding@resend.dev)
    ADMIN_EMAIL: Email address to receive notifications

USAGE:
    from email_service import email_service
    
    await email_service.send_contact_notification(
        name="John Doe",
        email="john@example.com",
        subject="Project Inquiry",
        message="I'd like to discuss..."
    )

NOTES:
    - Resend free tier only sends to verified addresses
    - To use custom sender domain, verify domain in Resend dashboard
    - Uses asyncio.to_thread() for non-blocking operation
"""

import resend
import asyncio
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# =========================================
# ENVIRONMENT SETUP
# =========================================

# Load environment variables from .env file
# Path is relative to this file's location (backend/.env)
load_dotenv(Path(__file__).parent / '.env')

# Configure logger for this module
logger = logging.getLogger(__name__)


class EmailService:
    """
    Email notification service using Resend API.
    
    Attributes:
        api_key (str): Resend API key for authentication
        sender_email (str): Email address used as 'from' address
        admin_email (str): Recipient email for notifications
        enabled (bool): Whether the service is properly configured
    
    Example:
        service = EmailService()
        if service.enabled:
            await service.send_contact_notification(...)
    """
    
    def __init__(self):
        """
        Initialize the email service with configuration from environment variables.
        
        Environment Variables:
            RESEND_API_KEY: Required for email sending
            SENDER_EMAIL: Defaults to 'onboarding@resend.dev' (Resend test sender)
            ADMIN_EMAIL: Defaults to 'jerathelczerny@yahoo.com'
        """
        # Load configuration from environment
        self.api_key = os.environ.get('RESEND_API_KEY', '')
        self.sender_email = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
        self.admin_email = os.environ.get('ADMIN_EMAIL', 'jerathelczerny@yahoo.com')
        
        # Service is enabled only if API key is provided
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            # Configure Resend SDK with API key
            resend.api_key = self.api_key
            logger.info("Email service configured with Resend API")
        else:
            logger.warning("Email service not configured. Set RESEND_API_KEY to enable.")

    async def send_contact_notification(
        self, 
        name: str, 
        email: str, 
        subject: str, 
        message: str
    ) -> bool:
        """
        Send email notification when contact form is submitted.
        
        Args:
            name: Sender's name from contact form
            email: Sender's email address (used for reply-to)
            subject: Message subject
            message: Message body content
        
        Returns:
            bool: True if email sent successfully, False otherwise
        
        Note:
            - Uses asyncio.to_thread() because Resend SDK is synchronous
            - This keeps FastAPI's event loop non-blocking
            - Email is sent to admin_email, reply-to is set to sender's email
        """
        # Skip if service not configured
        if not self.enabled:
            logger.info(f"Email notification skipped (not configured). Contact from: {name} <{email}>")
            return False

        try:
            # =========================================
            # BUILD HTML EMAIL CONTENT
            # =========================================
            
            # Professional HTML email template with inline CSS
            # (Email clients don't support external stylesheets)
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f4f4;">
                        <!-- Header with navy background -->
                        <div style="background-color: #1e3a5f; color: white; padding: 20px; text-align: center;">
                            <h2 style="margin: 0;">New Contact Form Submission</h2>
                        </div>
                        
                        <!-- Main content card -->
                        <div style="background-color: white; padding: 30px; margin-top: 20px; border-radius: 8px;">
                            <!-- Contact details section -->
                            <h3 style="color: #8b2635; margin-top: 0;">Contact Details</h3>
                            <p><strong>Name:</strong> {name}</p>
                            <p><strong>Email:</strong> <a href="mailto:{email}" style="color: #8b2635;">{email}</a></p>
                            <p><strong>Subject:</strong> {subject}</p>
                            
                            <!-- Message section with accent border -->
                            <h3 style="color: #8b2635; margin-top: 30px;">Message</h3>
                            <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #8b2635; border-radius: 4px;">
                                <p style="margin: 0; white-space: pre-wrap;">{message}</p>
                            </div>
                        </div>
                        
                        <!-- Footer -->
                        <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
                            <p>This email was sent from your portfolio contact form.</p>
                        </div>
                    </div>
                </body>
            </html>
            """

            # =========================================
            # PREPARE AND SEND EMAIL
            # =========================================
            
            # Resend API parameters
            params = {
                "from": self.sender_email,      # Sender address (must be verified in Resend)
                "to": [self.admin_email],       # Recipient list
                "subject": f"Portfolio Contact: {subject}",
                "html": html_content,
                "reply_to": email               # Allow direct reply to form submitter
            }

            # Send email using Resend SDK
            # asyncio.to_thread() runs sync code in thread pool to avoid blocking
            result = await asyncio.to_thread(resend.Emails.send, params)
            
            # Log success with email ID for tracking
            logger.info(f"Email notification sent successfully to {self.admin_email}, ID: {result.get('id')}")
            return True

        except Exception as e:
            # Log error but don't crash - email is nice-to-have, not critical
            logger.error(f"Failed to send email notification: {str(e)}")
            return False


# =========================================
# SINGLETON INSTANCE
# =========================================

# Create single instance for import
# Usage: from email_service import email_service
email_service = EmailService()
