import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app import models
from app.routers import (
    users,
    appointments,
    auth,
    medical_records,
    payments,
    prescriptions,
    queue,
    reports,
    transactions,
    doctors,
    documents,
    announcements,
    settings,
    telemedicine_session,
)
from app.routers import mevo_webhooks

load_dotenv()

app = FastAPI()

# Configure CORS from environment variables
# CORS_ORIGINS can be a comma-separated list of origins
# Example: CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000
# If not set or set to "*", allows all origins (development only)
cors_origins_env = os.getenv("CORS_ORIGINS", "*")

if cors_origins_env == "*":
    origins = ["*"]
else:
    # Split comma-separated origins and strip whitespace
    origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(medical_records.router, prefix="/medical_records", tags=["medical_records"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(prescriptions.router, prefix="/prescriptions", tags=["prescriptions"])
app.include_router(queue.router, prefix="/queue", tags=["queue"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(doctors.router, prefix="/doctors", tags=["doctors"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(mevo_webhooks.router, prefix="/webhooks/mevo", tags=["mevo_webhooks"])
app.include_router(announcements.router, prefix="/announcements", tags=["announcements"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
app.include_router(telemedicine_session.router, prefix="/telemedicine-sessions", tags=["telemedicine-sessions"])

@app.get("/")
async def root():
    return {"message": "Hello World"}