"""
Portfolio Backend Server - FastAPI Application

Main server module for Jerathel's portfolio website.
Handles contact form submissions, email notifications, and admin endpoints.

ENDPOINTS:
    GET  /api/               - Health check (API status)
    GET  /api/health         - System health with email config status
    POST /api/contact        - Submit contact form
    GET  /api/download/resume - Download résumé PDF

ENVIRONMENT VARIABLES (backend/.env):
    MONGO_URL: MongoDB connection string
    DB_NAME: Database name (default: test_database)
    RESEND_API_KEY: Resend email API key
    SENDER_EMAIL: Email sender address
    ADMIN_EMAIL: Notification recipient

RUNNING:
    Managed by Supervisor on port 8001
    Restart: sudo supervisorctl restart backend
"""

# ============================================================
# IMPORTS
# ============================================================

from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
import logging
import os

from models import Contact, ContactCreate
from email_service import email_service


# ============================================================
# CONFIGURATION
# ============================================================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Résumé file configuration
RESUME_DIR = ROOT_DIR / "resume"
RESUME_FILENAME = "Jerathel-Czerny-Software Engineer.pdf"
RESUME_PATH = RESUME_DIR / RESUME_FILENAME


# ============================================================
# DATABASE CONNECTION
# ============================================================

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]


# ============================================================
# APP INITIALIZATION
# ============================================================

app = FastAPI(
    title="Jerathel Portfolio API",
    description="Backend API for portfolio contact form and admin functions",
    version="1.0.0",
)

api_router = APIRouter(prefix="/api")


# ============================================================
# ROUTES — HEALTH CHECK
# ============================================================

@api_router.get("/")
async def root():
    return {"message": "Portfolio API is running"}


@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "email_configured": email_service.enabled,
    }


# ============================================================
# ROUTES — CONTACT FORM
# ============================================================

@api_router.post("/contact", response_model=dict)
async def submit_contact(contact_data: ContactCreate):
    """
    Handle contact form submissions:
    - Validate input
    - Save to MongoDB
    - Send email notification
    """
    try:
        contact = Contact(
            name=contact_data.name,
            email=contact_data.email,
            subject=contact_data.subject,
            message=contact_data.message,
        )

        await db.contacts.insert_one(contact.dict())

        try:
            await email_service.send_contact_notification(
                name=contact.name,
                email=contact.email,
                subject=contact.subject,
                message=contact.message,
            )
        except Exception as email_error:
            logging.error(f"Email notification failed: {email_error}")

        return {
            "success": True,
            "message": "Message received successfully. I'll get back to you soon!",
            "id": contact.id,
        }

    except Exception as e:
        logging.error(f"Contact submission error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit contact form. Please try again or email me directly.",
        )


# ============================================================
# ROUTES — RÉSUMÉ DOWNLOAD
# ============================================================

@api_router.get("/download/resume")
async def download_resume():
    """
    Serve the résumé PDF as a downloadable file.
    """
    try:
        if not RESUME_PATH.exists():
            logging.error(f"Resume file not found at: {RESUME_PATH}")
            raise HTTPException(status_code=404, detail="Resume file not found")

        return FileResponse(
            path=RESUME_PATH,
            media_type="application/pdf",
            filename=RESUME_FILENAME,
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": f'attachment; filename="{RESUME_FILENAME}"',
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Resume download failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to download resume")


# ============================================================
# ROUTER REGISTRATION
# ============================================================

app.include_router(api_router)


# ============================================================
# MIDDLEWARE — CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Allow all origins (adjust for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
# LIFECYCLE EVENTS
# ============================================================

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
