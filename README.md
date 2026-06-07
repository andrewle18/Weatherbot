# 🌤️ Bot Thời Tiết Telegram

## Deploy lên Railway (miễn phí)

### Bước 1: Upload code lên GitHub
1. Tạo repo mới tại github.com
2. Upload toàn bộ thư mục này lên

### Bước 2: Deploy Railway
1. Vào railway.app → Login bằng GitHub
2. "New Project" → "Deploy from GitHub repo"
3. Chọn repo vừa tạo

### Bước 3: Thêm biến môi trường
Trong Railway dashboard → Variables → thêm:
- `TELEGRAM_TOKEN` = token từ BotFather
- `OWM_API_KEY` = key từ openweathermap.org

### Bước 4: Deploy!
Railway tự động build và chạy. Bot sẽ online trong ~2 phút.

## Cách dùng bot
- Gõ tên thành phố: `Hanoi`, `Ho Chi Minh`
- `/weather Da Nang` — thời tiết hiện tại
- `/forecast Hue` — dự báo 3 ngày
