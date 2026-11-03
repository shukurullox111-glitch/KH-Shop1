import os, json, hmac, hashlib, time
from urllib.parse import parse_qsl
from dotenv import load_dotenv
from aiogram import Bot
from fastapi import HTTPException
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
CHANNEL = os.getenv('CHANNEL_ID', '@Kh_savdo_news')
CHANNEL_URL = os.getenv('CHANNEL_URL', 'https://t.me/Kh_savdo_news')
PUBLIC_URL = os.getenv('PUBLIC_URL', '')
CATEGORIES = ('Stars', 'Gift', 'TON', 'NFT')
BANKS = ('Ipak Yo‘li', 'Anorbank', 'Cmartbank', 'Hamkorbank', 'Tez Karta', 'Alynes Pay', 'UNide', 'Openbank')
# Names are user-supplied labels, not verified bank identities.

def verify_init_data(raw):
    try:
        data = dict(parse_qsl(raw, keep_blank_values=True))
        given = data.pop('hash')
        data.pop('signature', None)
        timestamp = int(data['auth_date'])
        if timestamp > time.time()+60 or time.time()-timestamp > 3600:
            raise ValueError('expired')
        check = '\n'.join(f'{k}={v}' for k,v in sorted(data.items()))
        secret = hmac.new(b'WebAppData', TOKEN.encode(), hashlib.sha256).digest()
        actual = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(given, actual):
            raise ValueError('signature')
        return int(json.loads(data['user'])['id'])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(401, 'Telegram login is invalid or expired')

async def is_member(bot: Bot, user_id: int):
    try:
        m = await bot.get_chat_member(CHANNEL, user_id)
        status = str(m.status)
        return status in ('creator','administrator','member') or (status=='restricted' and bool(getattr(m,'is_member',False)))
    except Exception:
        return False
