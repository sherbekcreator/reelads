import os
import json
import hmac
import hashlib
from urllib.parse import parse_qs, unquote
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# .env faylidan o'zgaruvchilarni yuklaymiz
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = FastAPI(title="Loot API")

# Papka yo'llari
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# --- TELEGRAM IMZOSINI TEKSHIRISH ---
def verify_telegram_init_data(init_data: str, bot_token: str) -> dict | None:
    if not init_data or not bot_token:
        return None
    try:
        # Telegramdan kelgan url-kodlangan satrni ajratamiz
        parsed_data = parse_qs(init_data)
        if "hash" not in parsed_data:
            return None

        received_hash = parsed_data["hash"][0]

        # Tekshirish uchun hashdan tashqari qolgan elementlarni alfavit bo'yicha yig'amiz
        data_check_list = []
        for key in sorted(parsed_data.keys()):
            if key != "hash":
                data_check_list.append(f"{key}={parsed_data[key][0]}")

        data_check_string = "\n".join(data_check_list)

        # HMAC-SHA256 kalitini hosil qilamiz
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode("utf-8"),
            hashlib.sha256
        ).digest()

        # Olingan ma'lumotning xeshini hisoblaymiz
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if calculated_hash == received_hash:
            # Tekshiruv muvaffaqiyatli o'tsa, user ma'lumotlarini dict qilib qaytaramiz
            result = {}
            for k, v in parsed_data.items():
                if k == "user":
                    result[k] = json.loads(v[0])
                else:
                    result[k] = v[0]
            return result
        return None
    except Exception:
        return None

# --- API ENDPOINTS ---
class AuthRequest(BaseModel):
    init_data: str

@app.get("/")
def serve_home():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Loot Platform"}

@app.post("/api/auth/verify")
def verify_user(payload: AuthRequest):
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="Serverda BOT_TOKEN sozlanmagan")

    user_data = verify_telegram_init_data(payload.init_data, BOT_TOKEN)
    if not user_data:
        raise HTTPException(status_code=401, detail="Soxta yoki yaroqsiz Telegram ma'lumoti!")

    return {
        "status": "success",
        "authenticated": True,
        "user": user_data.get("user")
    }