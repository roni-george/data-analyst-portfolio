# # main.py
# import os
# from fastapi import FastAPI
# import database
# import email_service

# app = FastAPI()

# @app.post("/run-audit")
# def trigger_refund_audit():
#     """This endpoint gets triggered by the cloud clock every 10 minutes."""
#     print("🚀 Cloud trigger received. Starting refund audit loop...")
#     database.init_db()
#     email_service.process_customer_replies()
#     email_service.process_new_requests()
#     return {"status": "success", "message": "Inbox processing complete"}

# if __name__ == "__main__":
#     # This allows you to test it locally by running 'python main.py'
#     import uvicorn
#     port = int(os.environ.get("PORT", 8080))
#     uvicorn.run(app, host="0.0.0.0", port=port)


# main.py
import os
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
import database
import email_service

async def local_one_minute_loop():
    """An automated local loop that triggers your code every 60 seconds."""
    print("⏳ Local 1-minute automation loop activated.")
    while True:
        try:
            print("\n⏰ [Automated Clock] Triggering refund audit sweep...")
            database.init_db()
            email_service.process_customer_replies()
            email_service.process_new_requests()
        except Exception as e:
            print(f"❌ Error during automated sweep: {e}")
        
        # Wait for 60 seconds before running again
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs as soon as the server boots up
    loop_task = asyncio.create_task(local_one_minute_loop())
    yield
    # Clean up when the server stops
    loop_task.cancel()

# Pass the lifespan manager to FastAPI
app = FastAPI(lifespan=lifespan)

@app.post("/run-audit")
def trigger_refund_audit():
    """This endpoint remains open so the cloud can still trigger it manually later."""
    print("🚀 Manual web trigger received. Starting refund audit loop...")
    database.init_db()
    email_service.process_customer_replies()
    email_service.process_new_requests()
    return {"status": "success", "message": "Inbox processing complete"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)