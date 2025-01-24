from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import httpx
import asyncio

app = FastAPI()

# Middleware for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database for demo purposes
user_data: Dict[str, Dict] = {}  # {login: {"password": str, "token": str, "chat_id": int}}

# OLX API Placeholder
OLX_API_BASE_URL = "https://api.olx.ua"  # Replace with the real OLX API URL

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "7343250438:AAF-DDTunznzby_yi4zN02JI9lgbc6eR214"

# Models
class LoginRequest(BaseModel):
    login: str
    password: str
    chat_id: int

class Notification(BaseModel):
    message_id: str
    sender: str
    text: str

class NotificationResponse(BaseModel):
    notifications: List[Notification]

# --- API Routes ---

@app.post("/login")
async def login_user(login_request: LoginRequest):
    """
    Endpoint to log in a user. Validates credentials with OLX API and stores session data.
    """
    # Simulate token generation (replace this with a real OLX API token request)
    olx_token = f"fake_token_for_{login_request.login}"

    # Store user data
    user_data[login_request.login] = {
        "password": login_request.password,
        "token": olx_token,
        "chat_id": login_request.chat_id,
    }
    return {"message": "Login successful", "login": login_request.login}


@app.get("/notifications", response_model=NotificationResponse)
async def get_notifications(login: str):
    """
    Fetch notifications for a user from the OLX API.
    """
    if login not in user_data:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_data[login]
    token = user["token"]

    # Simulate fetching notifications (replace this with a real OLX API request)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{OLX_API_BASE_URL}/messages",  # Replace with the actual OLX messages endpoint
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            messages = response.json().get("messages", [])
            notifications = [
                Notification(
                    message_id=msg.get("id"),
                    sender=msg.get("sender"),
                    text=msg.get("text"),
                )
                for msg in messages
            ]
            return {"notifications": notifications}
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch notifications")


@app.post("/send_notification")
async def send_notification_to_user(login: str, background_tasks: BackgroundTasks):
    """
    Push notifications from OLX API to Telegram.
    """
    if login not in user_data:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_data[login]
    chat_id = user["chat_id"]

    # Fetch notifications
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{OLX_API_BASE_URL}/messages",  # Replace with the actual OLX messages endpoint
            headers={"Authorization": f"Bearer {user['token']}"}
        )
        if response.status_code == 200:
            messages = response.json().get("messages", [])
            for message in messages:
                background_tasks.add_task(send_to_telegram, chat_id, message["text"])
            return {"message": "Notifications sent"}
        else:
            raise HTTPException(status_code=500, detail="Failed to fetch notifications")


async def send_to_telegram(chat_id: int, message: str):
    """
    Sends a message to the user's Telegram chat via the Telegram bot.
    """
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": f"New notification: {message}"}
            )
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")


@app.on_event("startup")
async def schedule_notification_checks():
    """
    Background task to periodically fetch notifications for all users.
    """
    async def check_notifications():
        while True:
            for login in user_data:
                try:
                    await send_notification_to_user(login, background_tasks=BackgroundTasks())
                except Exception as e:
                    print(f"Error checking notifications for {login}: {e}")
            await asyncio.sleep(10)  # Poll every 10 seconds

asyncio.create_task(check_notifications())


@app.get("/users")
def get_all_users():
    """
    Returns all registered users for debugging purposes.
    """
    return user_data
