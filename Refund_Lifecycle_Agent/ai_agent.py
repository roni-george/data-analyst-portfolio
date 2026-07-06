# ai_agent.py
import os
import time
from google import genai
from pydantic import BaseModel, Field
from typing import Optional

# Setup the clean Gemini client structure
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Missing GEMINI_API_KEY environment variable!")
client = genai.Client(api_key=api_key)

# Pydantic Structural Blueprint
class RefundRequest(BaseModel):
    customer_name: Optional[str] = Field(default=None, description="Full name of the customer.")
    order_number: Optional[str] = Field(default=None, description="Order ID (e.g., #ORD-1024).")
    item_name: Optional[str] = Field(default=None, description="Specific product name.")
    days_since_purchase: Optional[int] = Field(default=None, description="Days since purchase.")
    item_condition: Optional[str] = Field(default=None, description="Exactly: 'Unopened', 'Opened/Like New', or 'Damaged'.")
    customer_reason: Optional[str] = Field(default=None, description="Summary of why they want a refund.")

def get_policy_text():
    """Reads store refund conditions safely or provides standard fallbacks."""
    try:
        with open("refund_policy.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Standard 30-day return policy applies. Items must be Unopened or Opened/Like New."

def call_gemini_with_retry(model_name, contents, config=None, retries=3, delay=2):
    """Helper to safely retry Gemini calls if the server returns a 503 error."""
    for attempt in range(retries):
        try:
            if config:
                return client.models.generate_content(model=model_name, contents=contents, config=config)
            else:
                return client.models.generate_content(model=model_name, contents=contents)
        except Exception as e:
            # If it's a 503 error and we have attempts left, wait and retry
            if "503" in str(e) and attempt < retries - 1:
                print(f"  └─ ⏳ Gemini server busy (503). Retrying in {delay}s (Attempt {attempt + 1}/{retries})...")
                time.sleep(delay)
                delay *= 2  # Wait a bit longer next time
            else:
                # If 2.5 fails completely, try falling back to the highly stable 2.0 model
                if model_name == 'gemini-2.5-flash':
                    print("  └─ 🔄 Switching to backup model (gemini-2.0-flash)...")
                    return call_gemini_with_retry('gemini-2.0-flash', contents, config, retries=2, delay=1)
                raise e

def extract_refund_details(email_body, is_reply=False):
    """Executes structured extraction via Gemini with 503 error resilience."""
    prompt = f"Extract details from this customer email:\n{email_body}"
    if is_reply:
        prompt = (
            f"The customer is replying to a request for missing data. Focus ONLY on the fresh, "
            f"top-most message details. Do NOT extract values from older automated requests "
            f"quoted down below. Extract details:\n{email_body}"
        )

    response = call_gemini_with_retry(
        model_name='gemini-2.5-flash',
        contents=prompt,
        config={"response_mime_type": "application/json", "response_schema": RefundRequest}
    )
    return RefundRequest.model_validate_json(response.text)

def run_policy_audit(name, days, condition, reason, item_name, order_number):
    """Evaluates fully compiled claim profiles against policy data with retries."""
    policy_text = get_policy_text()
    audit_prompt = f"""
    You are an automated E-commerce Compliance Auditor. Evaluate the customer's completed data against our store policy.
    
    [STORE POLICY DOCUMENTATION]:
    {policy_text}
    
    [CUSTOMER DATA]:
    Customer Name: {name}
    Order Number: {order_number}
    Item Name: {item_name}
    Days Since Purchase: {days}
    Item Condition: {condition}
    Reason: {reason}
    
    Your output must follow this template format stringently:
    STATUS: [Approved, Denied, or Manual Review]
    REASONING: [One sentence explanation]
    DRAFT: [Response text]
    """
    response = call_gemini_with_retry(model_name='gemini-2.5-flash', contents=audit_prompt)
    
    status = "Manual Review"
    for line in response.text.strip().split('\n'):
        if line.upper().startswith("STATUS:"):
            status = line.split(":", 1)[1].strip()
            break
            
    return status, response.text