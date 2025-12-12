"""
FastAPI Backend for PayPal Payment Processing
Provides comprehensive error tracking and logging for payment operations
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, TYPE_CHECKING
import os
import logging
from datetime import datetime
import traceback
import sys
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import Supabase client (with error handling)
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None
    logging.warning("Supabase package not installed. Database operations will fail.")

# Type checking imports
if TYPE_CHECKING:
    from supabase import Client

# Configure logging
# In production (Render), log only to stdout (no file logging)
# Render automatically captures stdout logs
is_production = (
    os.getenv('RENDER', '').lower() == 'true' or 
    os.getenv('ENVIRONMENT', '').lower() == 'production' or
    os.getenv('RENDER_SERVICE_NAME') is not None
)
handlers = [logging.StreamHandler(sys.stdout)]
if not is_production:
    # Only log to file in development
    try:
        handlers.append(logging.FileHandler('payment_errors.log'))
    except Exception:
        pass  # If file logging fails, continue with stdout only

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PayPal Payment API",
    description="Backend API for PayPal payment processing with error tracking",
    version="1.0.0"
)

# CORS configuration
# Get allowed origins from environment variable or allow all in development
allowed_origins = os.getenv("CORS_ORIGINS", "*")
if allowed_origins != "*":
    allowed_origins = [origin.strip() for origin in allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if isinstance(allowed_origins, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class DonationData(BaseModel):
    amount: float = Field(..., description="Amount in INR (rupees)")
    donorName: str
    donorEmail: Optional[str] = None
    donorAddress: Optional[str] = None
    donationType: str
    userId: Optional[str] = None

class CapturePaymentRequest(BaseModel):
    orderId: str = Field(..., description="PayPal order ID")
    donationData: Optional[DonationData] = None

class PaymentDetails(BaseModel):
    orderId: str
    captureId: str
    transactionId: str
    status: str
    amount: dict
    payer: dict
    createTime: Optional[str] = None
    updateTime: Optional[str] = None
    fullResponse: Optional[dict] = None

class CapturePaymentResponse(BaseModel):
    success: bool
    payment: PaymentDetails
    donation: Optional[dict] = None
    message: str

# Global exception handler for detailed error tracking
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with comprehensive error logging"""
    error_id = f"ERR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{id(exc)}"
    
    error_details = {
        "error_id": error_id,
        "timestamp": datetime.now().isoformat(),
        "path": str(request.url),
        "method": request.method,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "traceback": traceback.format_exc(),
    }
    
    # Log full error details
    logger.error(f"Error {error_id}: {error_details}")
    
    # Log to file for persistent tracking
    with open("payment_errors.log", "a") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"Error ID: {error_id}\n")
        f.write(f"Timestamp: {error_details['timestamp']}\n")
        f.write(f"Path: {error_details['path']}\n")
        f.write(f"Method: {error_details['method']}\n")
        f.write(f"Error Type: {error_details['error_type']}\n")
        f.write(f"Error Message: {error_details['error_message']}\n")
        f.write(f"Traceback:\n{error_details['traceback']}\n")
        f.write(f"{'='*80}\n")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "message": str(exc),
            "timestamp": error_details["timestamp"]
        }
    )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "PayPal Payment API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("PAYPAL_ENVIRONMENT", "unknown")
    }

@app.post("/api/paypal/capture-payment", response_model=CapturePaymentResponse)
async def capture_payment(request: CapturePaymentRequest):
    """
    Capture PayPal payment and store in database
    
    This endpoint:
    1. Captures the PayPal payment using PayPal SDK
    2. Verifies payment status
    3. Stores payment details in Supabase
    4. Provides comprehensive error tracking
    """
    error_context = {
        "order_id": request.orderId,
        "timestamp": datetime.now().isoformat(),
        "endpoint": "/api/paypal/capture-payment"
    }
    
    try:
        logger.info("=== PayPal Capture API Called ===")
        logger.info(f"Request: {request.model_dump()}")
        env_check = {
            'hasPayPalClientId': bool(os.getenv('PAYPAL_CLIENT_ID')),
            'hasPayPalSecret': bool(os.getenv('PAYPAL_SECRET')),
            'hasSupabaseUrl': bool(os.getenv('SUPABASE_URL')),
            'hasSupabaseKey': bool(os.getenv('SUPABASE_SERVICE_ROLE_KEY')),
            'paypalEnv': os.getenv('PAYPAL_ENVIRONMENT', 'sandbox')
        }
        logger.info(f"Environment check: {env_check}")
        
        # Validate order ID
        if not request.orderId:
            raise HTTPException(
                status_code=400,
                detail="Order ID is required"
            )
        
        # Verify Supabase is available
        if create_client is None:
            raise HTTPException(
                status_code=500,
                detail="Server configuration error: Supabase package not installed. Install with: pip install -r requirements.txt"
            )
        
        # Step 1: Initialize PayPal client configuration
        try:
            paypal_config = _get_paypal_client()
            logger.info(f"PayPal client initialized successfully")
        except Exception as e:
            logger.error(f"PayPal client initialization failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"PayPal configuration error: {str(e)}"
            )
        
        # Step 2: Capture the payment using PayPal Orders API v2
        try:
            logger.info(f"Capturing PayPal order: {request.orderId}")
            
            base_url = "https://api.paypal.com" if paypal_config["environment"] == "production" else "https://api.sandbox.paypal.com"
            
            # Get access token with timeout
            try:
                auth_response = requests.post(
                    f"{base_url}/v1/oauth2/token",
                    auth=(paypal_config["client_id"], paypal_config["client_secret"]),
                    data={"grant_type": "client_credentials"},
                    headers={"Accept": "application/json", "Accept-Language": "en_US"},
                    timeout=10  # 10 second timeout
                )
            except requests.exceptions.Timeout:
                raise HTTPException(
                    status_code=500,
                    detail="PayPal API timeout: Failed to get access token (request timed out after 10 seconds)"
                )
            except requests.exceptions.ConnectionError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"PayPal API connection error: Unable to connect to PayPal servers. {str(e) if str(e) else 'Check your internet connection and PayPal API status.'}"
                )
            except requests.exceptions.RequestException as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"PayPal API request error: {str(e) if str(e) else 'Failed to communicate with PayPal API'}"
                )
            
            if not auth_response.ok:
                error_text = auth_response.text or "No error details provided"
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get PayPal access token (HTTP {auth_response.status_code}): {error_text[:500]}"
                )
            
            try:
                auth_data = auth_response.json()
                access_token = auth_data.get("access_token")
                if not access_token:
                    raise HTTPException(
                        status_code=500,
                        detail="PayPal access token not found in response"
                    )
            except (ValueError, KeyError) as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid PayPal auth response: {str(e)}"
                )
            
            # Capture the order with timeout
            try:
                capture_response = requests.post(
                    f"{base_url}/v2/checkout/orders/{request.orderId}/capture",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json"
                    },
                    timeout=30  # 30 second timeout for capture
                )
            except requests.exceptions.Timeout:
                raise HTTPException(
                    status_code=500,
                    detail="PayPal API timeout: Payment capture request timed out after 30 seconds"
                )
            except requests.exceptions.ConnectionError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"PayPal API connection error: Unable to connect to PayPal servers. {str(e) if str(e) else 'Check your internet connection and PayPal API status.'}"
                )
            except requests.exceptions.RequestException as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"PayPal API request error: {str(e) if str(e) else 'Failed to communicate with PayPal API'}"
                )
            
            if not capture_response.ok:
                # Try to extract detailed error information
                error_text = capture_response.text or ""
                status_code = capture_response.status_code
                
                logger.error(f"PayPal capture failed with HTTP {status_code}")
                logger.error(f"Response headers: {dict(capture_response.headers)}")
                logger.error(f"Response body: {error_text}")
                
                try:
                    error_data = capture_response.json()
                    error_message = error_data.get('message', '') or error_data.get('error', '') or 'Unknown error'
                    error_name = error_data.get('name', '')
                    error_details = error_data.get('details', [])
                    debug_id = error_data.get('debug_id', '')
                    
                    # Build detailed error message
                    detail_parts = []
                    if error_name:
                        detail_parts.append(error_name)
                    if error_message and error_message != 'Unknown error':
                        detail_parts.append(error_message)
                    
                    detail_msg = "PayPal API Error"
                    if detail_parts:
                        detail_msg = f"PayPal API Error: {' - '.join(detail_parts)}"
                    
                    if error_details:
                        detail_list = []
                        for d in error_details:
                            issue = d.get('issue', '')
                            description = d.get('description', '')
                            field = d.get('field', '')
                            if issue or description:
                                detail_str = f"{field}: {issue}" if field else issue
                                if description:
                                    detail_str += f" - {description}"
                                detail_list.append(detail_str)
                        if detail_list:
                            detail_msg += f" ({'; '.join(detail_list)})"
                    
                    if debug_id:
                        detail_msg += f" [Debug ID: {debug_id}]"
                    
                    # If we still don't have a good message, use the raw response
                    if detail_msg == "PayPal API Error" or not detail_msg.strip():
                        detail_msg = f"PayPal API returned error (HTTP {status_code}): {error_text[:300]}"
                    
                    logger.error(f"PayPal capture error details: {error_data}")
                    
                    raise HTTPException(
                        status_code=min(status_code, 500),  # Cap at 500 for client errors
                        detail=detail_msg
                    )
                except (ValueError, KeyError, TypeError) as json_error:
                    # Response is not JSON or missing expected fields
                    logger.error(f"PayPal capture failed (HTTP {status_code}, non-JSON or malformed): {error_text}")
                    logger.error(f"JSON parse error: {json_error}")
                    
                    # Provide meaningful error message
                    if error_text:
                        detail_msg = f"PayPal API error (HTTP {status_code}): {error_text[:500]}"
                    else:
                        detail_msg = f"PayPal API returned error status {status_code} with no response body"
                    
                    raise HTTPException(
                        status_code=min(status_code, 500),
                        detail=detail_msg
                    )
            
            order_data = capture_response.json()
            status = order_data.get("status", "UNKNOWN")
            order = order_data
            
            logger.info(f"PayPal capture response status: {status}")
            
        except HTTPException:
            # Re-raise HTTPExceptions as-is (they already have proper error messages)
            raise
        except requests.exceptions.RequestException as e:
            # Handle requests library exceptions specifically
            error_type = type(e).__name__
            error_message = str(e) if str(e) else f"{error_type} occurred"
            logger.error(f"PayPal API request exception: {error_type}: {error_message}", exc_info=True)
            error_context["paypal_error"] = error_message
            error_context["error_type"] = error_type
            
            # Provide specific error messages based on exception type
            if isinstance(e, requests.exceptions.Timeout):
                detail_msg = "PayPal API request timed out. Please try again."
            elif isinstance(e, requests.exceptions.ConnectionError):
                detail_msg = "Unable to connect to PayPal API. Check your internet connection."
            elif isinstance(e, requests.exceptions.HTTPError):
                detail_msg = f"PayPal API HTTP error: {error_message}"
            else:
                detail_msg = f"PayPal API request failed: {error_message}"
            
            raise HTTPException(
                status_code=500,
                detail=detail_msg
            )
        except Exception as e:
            # Log full exception details for any other exceptions
            error_message = str(e) if e else "Unknown error"
            error_type = type(e).__name__
            logger.error(f"PayPal capture error: {error_type}: {error_message}", exc_info=True)
            logger.error(f"Exception args: {e.args if hasattr(e, 'args') else 'N/A'}")
            error_context["paypal_error"] = error_message
            error_context["error_type"] = error_type
            
            # Provide more detailed error message
            if not error_message or error_message.strip() == "":
                error_message = f"PayPal API call failed ({error_type})"
                # Try to get more info from exception args
                if hasattr(e, 'args') and e.args:
                    error_message = f"{error_message}: {', '.join(str(arg) for arg in e.args if arg)}"
            
            raise HTTPException(
                status_code=400,
                detail=f"PayPal capture failed: {error_message}"
            )
        
        # Step 3: Verify payment status
        if status != "COMPLETED":
            logger.warning(f"Payment not completed. Status: {status}, Order: {order.id}")
            raise HTTPException(
                status_code=400,
                detail=f"Payment not completed. Status: {status}",
                headers={"X-Payment-Status": status}
            )
        
        # Step 4: Extract payment details from PayPal Orders API v2 response
        try:
            purchase_unit = order.get("purchase_units", [{}])[0] if isinstance(order, dict) else {}
            capture = purchase_unit.get("payments", {}).get("captures", [{}])[0] if isinstance(purchase_unit, dict) else {}
            payer = order.get("payer", {}) if isinstance(order, dict) else {}
            
            payment_details = {
                "orderId": order.get("id", "") if isinstance(order, dict) else str(order),
                "captureId": capture.get("id", "") if isinstance(capture, dict) else "",
                "transactionId": capture.get("id", "") if isinstance(capture, dict) else "",
                "status": status,
                "amount": {
                    "value": capture.get("amount", {}).get("value", "0") if isinstance(capture, dict) else purchase_unit.get("amount", {}).get("value", "0") if isinstance(purchase_unit, dict) else "0",
                    "currency": capture.get("amount", {}).get("currency_code", "USD") if isinstance(capture, dict) else purchase_unit.get("amount", {}).get("currency_code", "USD") if isinstance(purchase_unit, dict) else "USD"
                },
                "payer": {
                    "payerId": payer.get("payer_id", "") if isinstance(payer, dict) else "",
                    "email": payer.get("email_address", "") if isinstance(payer, dict) else "",
                    "name": f"{payer.get('name', {}).get('given_name', '')} {payer.get('name', {}).get('surname', '')}".strip() if isinstance(payer, dict) and payer.get("name") else ""
                },
                "createTime": capture.get("create_time", "") if isinstance(capture, dict) else order.get("create_time", "") if isinstance(order, dict) else "",
                "updateTime": capture.get("update_time", "") if isinstance(capture, dict) else order.get("update_time", "") if isinstance(order, dict) else "",
                "fullResponse": order
            }
            
            logger.info(f"Payment details extracted: Order ID {payment_details['orderId']}, Capture ID {payment_details['captureId']}")
            
        except Exception as e:
            logger.error(f"Error extracting payment details: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error processing payment details: {str(e)}"
            )
        
        # Step 5: Store in database (if donation data provided)
        donation_record = None
        if request.donationData:
            try:
                supabase = _get_supabase_client()
                
                amount_in_inr = request.donationData.amount
                donation_id = f"SSLF-{str(int(datetime.now().timestamp()))[-6:]}"
                receipt_number = f"RCP-{datetime.now().year}-{str(int(datetime.now().timestamp() * 1000) % 10000).zfill(4)}"
                
                # Build donation data with only required and non-None fields
                donation_data = {
                    "donation_id": donation_id,
                    "amount": amount_in_inr,
                    "donor_name": request.donationData.donorName,
                    "donation_type": request.donationData.donationType,
                    "payment_id": payment_details["captureId"],
                    "payment_method": "PayPal",
                    "receipt_number": receipt_number,
                    "status": "completed",
                    "currency": "INR",
                }
                
                # Add optional fields only if they have values (not None)
                if request.donationData.userId:
                    donation_data["user_id"] = request.donationData.userId
                if request.donationData.donorAddress:
                    donation_data["donor_address"] = request.donationData.donorAddress
                if request.donationData.donorEmail:
                    donation_data["donor_email"] = request.donationData.donorEmail
                
                # Try to add PayPal-specific fields (these columns may not exist in all databases)
                # First, try with all PayPal fields
                paypal_fields = {}
                try:
                    paypal_fields["paypal_order_id"] = payment_details["orderId"]
                    paypal_fields["paypal_capture_id"] = payment_details["captureId"]
                    if payment_details.get("payer", {}).get("payerId"):
                        paypal_fields["paypal_payer_id"] = payment_details["payer"]["payerId"]
                    # Use paypal_payment_details (JSONB) - correct column name from migration
                    if payment_details.get("fullResponse"):
                        paypal_fields["paypal_payment_details"] = payment_details["fullResponse"]
                except Exception as e:
                    logger.warning(f"Could not prepare PayPal-specific fields: {e}")
                
                # Try inserting with PayPal fields first, fallback to without if it fails
                try:
                    donation_data_with_paypal = {**donation_data, **paypal_fields}
                    result = supabase.table("donations").insert(donation_data_with_paypal).execute()
                except Exception as insert_error:
                    error_str = str(insert_error).lower()
                    error_message = str(insert_error)
                    
                    # Check if error is about missing columns
                    if "column" in error_str or "pgrst204" in error_str.lower():
                        logger.warning(f"Column may not exist in database, trying without optional fields: {insert_error}")
                        
                        # Remove optional fields that might not exist
                        minimal_donation_data = {
                            "donation_id": donation_id,
                            "amount": amount_in_inr,
                            "donor_name": request.donationData.donorName,
                            "donation_type": request.donationData.donationType,
                            "payment_id": payment_details["captureId"],
                            "payment_method": "PayPal",
                            "receipt_number": receipt_number,
                            "status": "completed",
                            "currency": "INR",
                        }
                        
                        # Only add user_id if it exists (it's a standard column)
                        if request.donationData.userId:
                            minimal_donation_data["user_id"] = request.donationData.userId
                        
                        # Try with minimal data (no optional columns)
                        try:
                            result = supabase.table("donations").insert(minimal_donation_data).execute()
                        except Exception as minimal_error:
                            logger.error(f"Failed to insert even with minimal data: {minimal_error}")
                            raise HTTPException(
                                status_code=500,
                                detail=f"Database error: {str(minimal_error)}. Please check your database schema."
                            )
                    else:
                        # Re-raise if it's a different error (not a column issue)
                        raise
                
                if result.data:
                    donation_record = result.data[0] if isinstance(result.data, list) else result.data
                    logger.info(f"Donation record saved: {donation_id}")
                else:
                    logger.warning(f"Donation record insert returned no data")
                    
            except Exception as e:
                # Don't fail the request if database save fails - payment was successful
                logger.error(f"Error saving donation to database: {e}", exc_info=True)
                error_context["database_error"] = str(e)
                # Continue without donation record
        
        # Step 6: Return success response
        logger.info(f"Payment captured successfully: Order {payment_details['orderId']}")
        
        return CapturePaymentResponse(
            success=True,
            payment=PaymentDetails(**payment_details),
            donation=donation_record,
            message="Payment captured successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in capture_payment: {e}", exc_info=True)
        error_context["unexpected_error"] = str(e)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

def _get_paypal_client():
    """Initialize PayPal client configuration"""
    client_id = os.getenv("PAYPAL_CLIENT_ID")
    client_secret = os.getenv("PAYPAL_SECRET")
    environment = os.getenv("PAYPAL_ENVIRONMENT", "sandbox")
    
    if not client_id or not client_secret:
        raise ValueError("PayPal credentials not configured. Set PAYPAL_CLIENT_ID and PAYPAL_SECRET")
    
    # Return configuration dict (actual API calls use requests library)
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "environment": environment
    }

def _get_supabase_client():
    """Initialize and return Supabase client"""
    if create_client is None:
        raise ValueError("Supabase package not installed. Install with: pip install -r requirements.txt")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    
    return create_client(supabase_url, supabase_key)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

