import os, json, uuid, shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from common import TOKEN, ADMIN_ID, CATEGORIES, BANKS, CHANNEL_URL, verify_init_data, is_member
from db import init, connect

ROOT=Path(__file__).parent
UPLOADS=ROOT/'uploads'
UPLOADS.mkdir(exist_ok=True)
bot=Bot(TOKEN)

@asynccontextmanager
async def lifespan(app):
    init()
    yield
    await bot.session.close()

app=FastAPI(title='KH SHOP',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

@app.get('/')
async def index():
    return FileResponse(ROOT/'static'/'index.html')

async def auth(x_telegram_init_data: str = Header(default='')):
    uid=verify_init_data(x_telegram_init_data)
    if not await is_member(bot,uid):
        raise HTTPException(403,'subscribe')
    return uid

def admin(uid=Depends(auth)):
    if uid!=ADMIN_ID:
        raise HTTPException(403,'admin only')
    return uid

@app.get('/api/me')
async def me(uid=Depends(auth)):
    return {'id':uid,'admin':uid==ADMIN_ID,'categories':CATEGORIES,'banks':BANKS,'manual_checkout':os.getenv('ENABLE_MANUAL_CHECKOUT')=='1'}

@app.get('/api/products')
async def products(uid=Depends(auth)):
    with connect() as db:
        return [dict(x) for x in db.execute('SELECT * FROM products WHERE active=1 ORDER BY id DESC')]

@app.get('/api/cards')
async def cards(uid=Depends(auth)):
    with connect() as db:
        return [dict(x) for x in db.execute('SELECT * FROM cards WHERE active=1 ORDER BY id DESC')]

class Product(BaseModel):
    category: str
    name: str = Field(min_length=1,max_length=120)
    price: int = Field(ge=0,le=10**12)
    description: str = Field(default='',max_length=3000)

@app.post('/api/admin/products')
async def add_product(p:Product,uid=Depends(admin)):
    if p.category not in CATEGORIES: raise HTTPException(400,'category')
    with connect() as db:
        cur=db.execute('INSERT INTO products(category,name,price,description) VALUES(?,?,?,?)',(p.category,p.name,p.price,p.description))
        return {'id':cur.lastrowid}

@app.put('/api/admin/products/{pid}')
async def edit_product(pid:int,p:Product,uid=Depends(admin)):
    if p.category not in CATEGORIES: raise HTTPException(400,'category')
    with connect() as db:
        cur=db.execute('UPDATE products SET category=?,name=?,price=?,description=? WHERE id=?',(p.category,p.name,p.price,p.description,pid))
        if not cur.rowcount: raise HTTPException(404,'product')
    return {'ok':True}

@app.delete('/api/admin/products/{pid}')
async def delete_product(pid:int,uid=Depends(admin)):
    with connect() as db:
        db.execute('UPDATE products SET active=0 WHERE id=?',(pid,))
    return {'ok':True}

async def store_file(file:UploadFile, allowed:dict, max_bytes:int):
    ext=Path(file.filename or '').suffix.lower()
    if ext not in allowed or file.content_type not in allowed[ext]:
        raise HTTPException(400,'File type not allowed')
    data=await file.read(max_bytes+1)
    if len(data)>max_bytes: raise HTTPException(413,'File too large')
    # Check signatures to prevent extension/content-type spoofing.
    if ext=='.pdf' and not data.startswith(b'%PDF-'): raise HTTPException(400,'Invalid PDF')
    if ext in ('.jpg','.jpeg') and not data.startswith(b'\xff\xd8\xff'): raise HTTPException(400,'Invalid JPEG')
    if ext=='.png' and not data.startswith(b'\x89PNG\r\n\x1a\n'): raise HTTPException(400,'Invalid PNG')
    if ext=='.webp' and not (data[:4]==b'RIFF' and data[8:12]==b'WEBP'): raise HTTPException(400,'Invalid WebP')
    filename=uuid.uuid4().hex+ext
    (UPLOADS/filename).write_bytes(data)
    return filename

IMAGES={'.jpg':{'image/jpeg'},'.jpeg':{'image/jpeg'},'.png':{'image/png'},'.webp':{'image/webp'}}
RECEIPTS={k:v for k,v in IMAGES.items() if k!='.webp'}|{'.pdf':{'application/pdf'}}

@app.post('/api/admin/products/{pid}/image')
async def product_image(pid:int,file:UploadFile=File(...),uid=Depends(admin)):
    filename=await store_file(file,IMAGES,5*1024*1024)
    with connect() as db:
        row=db.execute('SELECT image FROM products WHERE id=? AND active=1',(pid,)).fetchone()
        if not row:
            (UPLOADS/filename).unlink(missing_ok=True)
            raise HTTPException(404,'product')
        db.execute('UPDATE products SET image=? WHERE id=?',(filename,pid))
    return {'ok':True}

@app.get('/api/products/{pid}/image')
async def view_image(pid:int,uid=Depends(auth)):
    with connect() as db:
        row=db.execute('SELECT image FROM products WHERE id=? AND active=1',(pid,)).fetchone()
    if not row or not row['image']: raise HTTPException(404,'image')
    return FileResponse(UPLOADS/row['image'])

class Card(BaseModel):
    bank: str
    number: str
    holder: str = Field(min_length=2,max_length=100)

@app.post('/api/admin/cards')
async def add_card(p:Card,uid=Depends(admin)):
    if p.bank not in BANKS: raise HTTPException(400,'bank')
    number=p.number.replace(' ','')
    if not number.isdigit() or not (12<=len(number)<=19): raise HTTPException(400,'card number')
    with connect() as db:
        db.execute('INSERT INTO cards(bank,number,holder) VALUES(?,?,?)',(p.bank,number,p.holder))
    return {'ok':True}

@app.delete('/api/admin/cards/{cid}')
async def remove_card(cid:int,uid=Depends(admin)):
    with connect() as db:
        db.execute('UPDATE cards SET active=0 WHERE id=?',(cid,))
    return {'ok':True}

class OrderIn(BaseModel):
    items: list[dict]
    card_id: int

@app.post('/api/orders')
async def create_order(p:OrderIn,uid=Depends(auth)):
    # Disabled for digital-goods storefront until an approved payment flow is configured.
    if os.getenv('ENABLE_MANUAL_CHECKOUT')!='1':
        raise HTTPException(403,'Manual checkout disabled for digital goods. Configure compliant payment provider.')
    if not p.items or len(p.items)>50: raise HTTPException(400,'items')
    with connect() as db:
        card=db.execute('SELECT id FROM cards WHERE id=? AND active=1',(p.card_id,)).fetchone()
        if not card: raise HTTPException(400,'card')
        entries=[]
        total=0
        for item in p.items:
            try:
                pid=int(item['id']); qty=int(item['qty'])
            except (ValueError,KeyError,TypeError): raise HTTPException(400,'item')
            if not 1<=qty<=100: raise HTTPException(400,'qty')
            row=db.execute('SELECT * FROM products WHERE id=? AND active=1',(pid,)).fetchone()
            if not row: raise HTTPException(400,'product unavailable')
            # Telegram digital goods require Stars payment; do not allow manual cards here.
            if row['category'] in CATEGORIES:
                raise HTTPException(403,'Digital goods require compliant payment integration')
            total+=row['price']*qty
            entries.append((pid,row['name'],row['price'],qty))
        cur=db.execute('INSERT INTO orders(user_id,total,card_id) VALUES(?,?,?)',(uid,total,p.card_id))
        oid=cur.lastrowid
        db.executemany('INSERT INTO order_items(order_id,product_id,name,price,qty) VALUES(?,?,?,?,?)',[(oid,*x) for x in entries])
    return {'id':oid,'total':total}

@app.get('/api/orders')
async def my_orders(uid=Depends(auth)):
    with connect() as db:
        return [dict(x) for x in db.execute('SELECT id,total,status,created_at FROM orders WHERE user_id=? ORDER BY id DESC',(uid,))]

@app.post('/api/orders/{oid}/receipt')
async def upload_receipt(oid:int,file:UploadFile=File(...),uid=Depends(auth)):
    with connect() as db:
        row=db.execute('SELECT * FROM orders WHERE id=? AND user_id=?',(oid,uid)).fetchone()
    if not row or row['status'] not in ('pending','rejected'):
        raise HTTPException(400,'Order not eligible')
    filename=await store_file(file,RECEIPTS,10*1024*1024)
    with connect() as db:
        db.execute('UPDATE orders SET receipt=?,status=? WHERE id=?',(filename,'review',oid))
    keyboard=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Tasdiqlash',callback_data=f'approve:{oid}'),InlineKeyboardButton(text='❌ Rad etish',callback_data=f'reject:{oid}')]
    ])
    try:
        await bot.send_document(ADMIN_ID,FSInputFile(UPLOADS/filename),caption=f'🧾 Buyurtma #{oid}\nXaridor: {uid}\nJami: {row["total"]:,} so‘m')
        await bot.send_message(ADMIN_ID,f'Buyurtma #{oid}: chekni tekshiring. Bankdagi tushumni ham tekshiring.',reply_markup=keyboard)
    except Exception:
        # Preserve the receipt for admin to retrieve later.
        pass
    return {'ok':True,'status':'review'}

@app.get('/api/admin/orders')
async def admin_orders(uid=Depends(admin)):
    with connect() as db:
        return [dict(x) for x in db.execute('SELECT id,user_id,total,status,receipt,created_at FROM orders ORDER BY id DESC LIMIT 200')]

@app.get('/api/admin/orders/{oid}/receipt')
async def admin_receipt(oid:int,uid=Depends(admin)):
    with connect() as db:
        row=db.execute('SELECT receipt FROM orders WHERE id=?',(oid,)).fetchone()
    if not row or not row['receipt']: raise HTTPException(404,'receipt')
    return FileResponse(UPLOADS/row['receipt'],filename=row['receipt'])
