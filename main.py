from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from models import Contact, ContactCreate
from email_service import email_service

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Jerathel Portfolio API")
@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "Backend is running"
    }


# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Test route
@api_router.get("/")
async def root():
    return {"message": "Portfolio API is running"}

# Contact form submission endpoint
@api_router.post("/contact", response_model=dict)
async def submit_contact(contact_data: ContactCreate):
    """
    Handle contact form submissions
    - Validates input data
    - Stores in MongoDB
    - Sends email notification
    """
    try:
        # Create contact object
        contact = Contact(
            name=contact_data.name,
            email=contact_data.email,
            subject=contact_data.subject,
            message=contact_data.message
        )
        
        # Store in MongoDB
        result = await db.contacts.insert_one(contact.dict())
        
        # Send email notification (async, don't block response)
        try:
            await email_service.send_contact_notification(
                name=contact.name,
                email=contact.email,
                subject=contact.subject,
                message=contact.message
            )
        except Exception as email_error:
            # Log but don't fail the request if email fails
            logging.error(f"Email notification failed: {str(email_error)}")
        
        return {
            "success": True,
            "message": "Message received successfully. I'll get back to you soon!",
            "id": contact.id
        }
    
    except Exception as e:
        logging.error(f"Contact submission error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit contact form. Please try again or email me directly."
        )

# Get all contacts (admin endpoint - could add auth later)
@api_router.get("/contacts")
async def get_contacts():
    """
    Retrieve all contact submissions (admin use)
    """
    try:
        contacts_cursor = db.contacts.find().sort("created_at", -1).limit(1000)
        contacts = []
        
        async for contact in contacts_cursor:
            # Convert MongoDB document to JSON-serializable format
            contact_dict = {
                "id": contact.get("id"),
                "name": contact.get("name"),
                "email": contact.get("email"),
                "subject": contact.get("subject"),
                "message": contact.get("message"),
                "created_at": contact.get("created_at").isoformat() if contact.get("created_at") else None,
                "read": contact.get("read", False)
            }
            contacts.append(contact_dict)
        
        return {"contacts": contacts, "count": len(contacts)}
    except Exception as e:
        logging.error(f"Failed to fetch contacts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch contacts")

# Health check endpoint
@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "email_configured": email_service.enabled
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["http://localhost:5173",  # Vite
        "http://127.0.0.1:5173",],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
