import asyncio, logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from common import TOKEN, ADMIN_ID, CHANNEL_URL, PUBLIC_URL, is_member
from db import init, connect

bot = Bot(TOKEN)
dp = Dispatcher()

def subscribe_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📢 Kanalga aʼzo bo‘lish',url=CHANNEL_URL)],
        [InlineKeyboardButton(text='✅ Obunani tekshirish',callback_data='check')]
    ])

def shop_buttons():
    rows = []
    if PUBLIC_URL.startswith('https://') and 'example' not in PUBLIC_URL:
        rows.append([InlineKeyboardButton(text='🛍 KH SHOP ni ochish', web_app=WebAppInfo(url=PUBLIC_URL))])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None

@dp.message(CommandStart())
async def start(m: Message):
    if not await is_member(bot,m.from_user.id):
        await m.answer('🔒 KH SHOP dan foydalanish uchun kanalga aʼzo bo‘ling.',reply_markup=subscribe_buttons())
    else:
        await m.answer('✅ Obuna tasdiqlandi. KH SHOP ga xush kelibsiz!',reply_markup=shop_buttons())

@dp.callback_query(F.data=='check')
async def check(c: CallbackQuery):
    ok=await is_member(bot,c.from_user.id)
    await c.answer('✅ Obuna tasdiqlandi' if ok else '❌ Avval kanalga obuna bo‘ling',show_alert=True)
    if ok:
        await c.message.answer('🛍 Do‘konni oching:',reply_markup=shop_buttons())

@dp.message(Command('admin'))
async def admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        await m.answer('Ruxsat yo‘q.')
        return
    if not await is_member(bot,m.from_user.id):
        await m.answer('Avval kanalga obuna bo‘ling.',reply_markup=subscribe_buttons())
        return
    await m.answer('🛡 Admin panelni Mini App ichida oching.',reply_markup=shop_buttons())

@dp.callback_query(F.data.startswith('approve:'))
@dp.callback_query(F.data.startswith('reject:'))
async def decide(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        await c.answer('Ruxsat yo‘q',show_alert=True)
        return
    action, oid = c.data.split(':',1)
    with connect() as db:
        row=db.execute('SELECT user_id,status FROM orders WHERE id=?',(int(oid),)).fetchone()
        if not row or row['status']!='review':
            await c.answer('Buyurtma allaqachon ko‘rilgan.',show_alert=True)
            return
        status='approved' if action=='approve' else 'rejected'
        db.execute('UPDATE orders SET status=? WHERE id=?',(status,int(oid)))
    await c.answer('Saqlandi')
    await c.message.edit_reply_markup(reply_markup=None)
    await c.message.answer(f'Buyurtma #{oid}: {status}')
    try:
        await bot.send_message(row['user_id'],f'Buyurtma #{oid}: '+('✅ To‘lov tasdiqlandi' if status=='approved' else '❌ To‘lov rad etildi'))
    except Exception:
        logging.exception('Could not notify user')

async def main():
    logging.basicConfig(level=logging.INFO)
    init()
    await dp.start_polling(bot)

if __name__=='__main__':
    asyncio.run(main())
