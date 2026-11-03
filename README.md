# KH SHOP — Telegram Mini App starter

## Features
- Telegram `/start` and Mini App server-side required membership check for `@Kh_savdo_news`.
- Admin authorization by Telegram numeric ID, verified server-side using signed `initData`.
- Product catalog: Stars, Gift, TON, NFT; name, price, description, single image (JPG/PNG/WEBP), edit, soft delete.
- Cart, order database schema, admin card list (user-supplied bank labels), receipt PDF/JPG/PNG upload API, admin review with Telegram notification.
- SQLite storage, responsive Mini App.

## IMPORTANT LIMITATIONS
- **Real checkout is deliberately disabled** for the four digital-goods categories. Telegram digital goods/services sold inside bots/Mini Apps generally require Telegram Stars (XTR). TON/NFT transfer, compliant payment processing and delivery require separate integration, legal/age/eligibility checks. Merely displaying card numbers and collecting receipts is NOT a compliant automatic digital-goods payment system.
- Receipt approval must never be treated as proof of bank transfer: check actual bank account credit first.
- Bank names Cmartbank, Alynes Pay, UNide etc. are user-supplied labels, not verified bank identities.
- This is a functional starter, not a production-ready financial storefront. Add rate limits, CSRF considerations, persistent file storage, moderation, backups, audit logs, reverse proxy HTTPS, privacy policy and legal review before launch.
- Uploaded receipt endpoints are present, but the UI does not expose manual checkout because digital-goods payment integration is pending.

## Windows setup
1. Install Python 3.11+.
2. Open folder in VS Code.
3. Run:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env`; fill `BOT_TOKEN`, your numeric `ADMIN_ID`, and HTTPS `PUBLIC_URL` (keep token private).
5. Add bot as admin of `@Kh_savdo_news` channel. Start bot once with `/start` from admin account so it can send admin messages.
6. Start in two terminals:
   ```powershell
   .\.venv\Scripts\python.exe bot.py
   .\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000
   ```
7. Expose server through HTTPS with your own hosting/reverse proxy. Set `PUBLIC_URL` accordingly and restart bot. Configure BotFather Mini App/menu button if desired.
8. Open bot `/start`, subscribe, click `KH SHOP ni ochish`. Admin sees the Admin tab.

## Production architecture
Host bot polling and FastAPI HTTPS as separate processes; configure proper HTTPS domain and access control. Do not commit `.env`, database, or uploads to public git.
