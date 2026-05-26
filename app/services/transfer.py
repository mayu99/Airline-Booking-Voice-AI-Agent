import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger("transfer_service")

def initiate_transfer(call_context: str, session_id: str) -> Dict[str, Any]:
    """
    Initiates caller transfer to the test phone number.
    Logs transaction as JSON line to transfers.log and returns handoff payload.
    """
    transfer_number = settings.MY_TEST_PHONE
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Generate one sentence handoff summary
    handoff_summary = f"Caller requested human agent. Context: {call_context.strip()}"
    
    log_entry = {
        "timestamp": timestamp,
        "session_id": session_id,
        "call_context": call_context,
        "transfer_number": transfer_number
    }
    
    # Log to transfers.log as a single JSON line
    filepath = "transfers.log"
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        logger.info(f"Handoff successfully logged in transfers.log for session: {session_id}")
    except Exception as e:
        logger.error(f"Failed to write to transfers.log: {e}")

    return {
        "status": "transfer_initiated",
        "transfer_number": transfer_number,
        "handoff_summary": handoff_summary
    }
