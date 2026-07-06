# email_service.py
import imaplib
import smtplib
import email
import os
from email.message import EmailMessage
import database
import ai_agent

# 🔒 ENVIRONMENT AUTOPILOT
# Instead of prompting for inputs, we pull securely from the system background
EMAIL_ACCOUNT = os.environ.get("REFUND_EMAIL")
APP_PASSWORD = os.environ.get("REFUND_APP_PASS")

if not EMAIL_ACCOUNT or not APP_PASSWORD:
    raise ValueError(
        "Missing environment configuration! Make sure both REFUND_EMAIL "
        "and REFUND_APP_PASS environment variables are fully set."
    )

def send_reply(to_email, customer_name, content_body):
    """Utility function to deliver plain text outbound emails."""
    msg = EmailMessage()
    msg["Subject"] = "Update regarding your Gadget World Return Request"
    msg["From"] = EMAIL_ACCOUNT
    msg["To"] = to_email
    msg.set_content(f"Dear {customer_name},\n\n{content_body}")
    
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ACCOUNT, APP_PASSWORD)
        server.send_message(msg)
    print(f"  └─ 📨 Outbound message sent to {to_email}")

def parse_body_content(msg):
    """Extracts raw text string bodies safely from nested multipart streams."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
    return msg.get_payload(decode=True).decode(errors="ignore")

def process_new_requests():
    print("📬 Ingesting new incoming return files...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
    mail.select("inbox")
    
    _, search_data = mail.search(None, "UNSEEN")
    mail_ids = search_data[0].split()
    
    if not mail_ids or mail_ids == [b'']:
        print("📥 Clean slate! No new inbox items found.")
        mail.logout()
        return

    for m_id in mail_ids:
        try:
            _, data = mail.fetch(m_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            name, email_addr = email.utils.parseaddr(msg.get("From"))
            body = parse_body_content(msg)
            
            print(f"\nProcessing new ticket: {email_addr}...")
            parsed = ai_agent.extract_refund_details(body, is_reply=False)
            
            # Check for empty requirements
            missing = []
            if not parsed.order_number: missing.append("Order Number")
            if not parsed.item_name: missing.append("Product/Item Name")
            if parsed.days_since_purchase is None: missing.append("Days Since Purchase")
            if not parsed.item_condition: missing.append("Item Condition")

            if missing:
                print(f"  └─ ⚠️ Data components missing: {missing}")
                bullet_list = "\n".join([f"- {m}" for m in missing])
                info_request_text = f"We received your request, but are missing critical information:\n\n{bullet_list}\n\nPlease reply directly to this message."
                
                send_reply(email_addr, parsed.customer_name or "Customer", info_request_text)
                database.insert_new_request(
                    parsed.customer_name or "Unknown", email_addr, parsed.order_number, 
                    parsed.item_name, parsed.days_since_purchase, parsed.item_condition, 
                    parsed.customer_reason, status='Incomplete Data', sent_status='Sent - Info Request'
                )
            else:
                # Valid track
                row_id = database.insert_new_request(
                    parsed.customer_name, email_addr, parsed.order_number, 
                    parsed.item_name, parsed.days_since_purchase, parsed.item_condition, 
                    parsed.customer_reason, status='Pending Evaluation'
                )
                
                status, draft = ai_agent.run_policy_audit(
                    parsed.customer_name, parsed.days_since_purchase, parsed.item_condition, 
                    parsed.customer_reason, parsed.item_name, parsed.order_number
                )
                
                sent_lbl = "Sent - Resolution" if status in ["Approved", "Denied"] else "Sent - Escalation"
                msg_out = draft if status in ["Approved", "Denied"] else "Your request is currently under human managerial review."
                
                send_reply(email_addr, parsed.customer_name, msg_out)
                database.update_record(row_id, parsed.order_number, parsed.item_name, parsed.days_since_purchase, parsed.item_condition, parsed.customer_reason, status, draft, sent_lbl)
                print(f"  └─ ✅ Complete. File status resolved to: {status}")

            mail.store(m_id, '+FLAGS', '\\Seen')

        except Exception as e:
            print(f"  └─ ❌ Error parsing mailbox index context: {e}")

    mail.logout()

def process_customer_replies():
    print("\n🔄 Ingesting follow-up customer reply threads...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
    mail.select("inbox")
    
    _, search_data = mail.search(None, "UNSEEN")
    mail_ids = search_data[0].split()
    
    if not mail_ids or mail_ids == [b'']:
        print("📥 No fresh response messages inside queue.")
        mail.logout()
        return

    for m_id in mail_ids:
        try:
            _, data = mail.fetch(m_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            name, email_addr = email.utils.parseaddr(msg.get("From"))
            
            # Check the database for an existing incomplete file
            incomplete_file = database.get_last_incomplete_record(email_addr)
            
            # 🔥 SAFEGUARD: If this is NOT a reply to an incomplete ticket, 
            # explicitly keep it UNREAD and skip it so process_new_requests() can grab it!
            if not incomplete_file:
                mail.store(m_id, '-FLAGS', '\\Seen') 
                continue

            body = parse_body_content(msg)
            r_id, old_ord, old_itm, old_days, old_cond, old_reas = incomplete_file
            print(f"Found active open ticket for {email_addr}. Merging inputs...")
            
            new_parsed = ai_agent.extract_refund_details(body, is_reply=True)
            
            f_ord = new_parsed.order_number if new_parsed.order_number else old_ord
            f_itm = new_parsed.item_name if new_parsed.item_name else old_itm
            f_cond = new_parsed.item_condition if new_parsed.item_condition else old_cond
            f_reas = new_parsed.customer_reason if new_parsed.customer_reason else old_reas
            f_days = new_parsed.days_since_purchase if new_parsed.days_since_purchase is not None else old_days

            status, draft = ai_agent.run_policy_audit(name, f_days, f_cond, f_reas, f_itm, f_ord)
            sent_lbl = "Sent - Resolution" if status in ["Approved", "Denied"] else "Sent - Escalation"
            msg_out = draft if status in ["Approved", "Denied"] else "Your files have been sent up to management for physical review."
            
            send_reply(email_addr, name, msg_out)
            database.update_record(r_id, f_ord, f_itm, f_days, f_cond, f_reas, status, draft, sent_lbl)
            print(f"  └─ ✅ Open item ID {r_id} successfully closed.")
            
            mail.store(m_id, '+FLAGS', '\\Seen')

        except Exception as e:
            print(f"  └─ ❌ Error running loop validation check: {e}")

    mail.logout()

if __name__ == "__main__":
    database.init_db()
    # 1. Look for replies to open/incomplete tickets first!
    process_customer_replies() 
    
    # 2. Only process completely new threads if they aren't replies
    process_new_requests()
