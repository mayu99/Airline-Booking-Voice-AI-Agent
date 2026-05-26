import time
import json
import logging
import re
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.airports import load_airports_data
from app.routers import airports, flights, bookings, notifications, transfer

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")

# Uptime tracker start time
APP_START_TIME = time.time()

# Eager loading lifespan context
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup eager load
    try:
        load_airports_data()
    except Exception as e:
        logger.error(f"Eager loading of airports data failed: {e}")
    yield
    # Shutdown
    logger.info("Application shutting down.")

app = FastAPI(
    title="Phonely Airline Booking Agent Backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PII Redaction Log Helper ---
PHONE_PAT = re.compile(r"\+1\d{10}")
EMAIL_PAT = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

def redact_pii(text: str) -> str:
    """
    Scans a text and masks US phone numbers and email addresses.
    """
    def mask_phone_match(m):
        phone = m.group(0)
        return phone[:5] + "***" + phone[-4:]
    
    def mask_email_match(m):
        email = m.group(0)
        parts = email.split("@", 1)
        name = parts[0]
        domain = parts[1]
        if len(name) > 2:
            return f"{name[0]}***{name[-1]}@{domain}"
        return f"***@{domain}"

    text_phone = PHONE_PAT.sub(mask_phone_match, text)
    return EMAIL_PAT.sub(mask_email_match, text_phone)

# --- Custom PII-redacted Structured Logging Middleware ---
class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        latency_ms = round((time.time() - start_time) * 1000, 2)
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": latency_ms
        }
        
        # PII-redacted JSON line logged to stdout
        log_str = json.dumps(log_data)
        print(redact_pii(log_str), flush=True)
        return response

app.add_middleware(StructuredLoggingMiddleware)

# --- Global Exception Handlers returning HTTP 200 speech envelopes ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=200, # HTTP 200 as required
        content={
            "status": "error",
            "message": f"An unexpected error occurred: {str(exc)}"
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Request validation failed: {exc}")
    errors = "; ".join([f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()])
    return JSONResponse(
        status_code=200, # HTTP 200 as required
        content={
            "status": "error",
            "message": f"Input validation failed: {errors}"
        }
    )

# --- Health Check Endpoint ---
@app.get("/healthz")
async def healthz():
    uptime_seconds = time.time() - APP_START_TIME
    return {
        "status": "ok",
        "uptime_seconds": round(uptime_seconds, 2)
    }

# --- Mounting Router Webhooks ---
app.include_router(airports.router, tags=["Airports"])
app.include_router(flights.router, tags=["Flights"])
app.include_router(bookings.router, tags=["Bookings"])
app.include_router(notifications.router, tags=["Notifications"])
app.include_router(transfer.router, tags=["Transfer"])
