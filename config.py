import os
from dotenv import load_dotenv

# تحميل الملف .env
load_dotenv()

# طباعة مسار الملف الحالي للتأكد
print(f"Current directory: {os.getcwd()}")
print(f"Env file exists: {os.path.exists('.env')}")

# Discord Bot Token
TOKEN = os.getenv('DISCORD_TOKEN')
print(f"Loaded token: {TOKEN}")

# Dashboard Settings
DASHBOARD_SECRET_KEY = os.getenv('DASHBOARD_SECRET_KEY', 'your-secret-key')
DASHBOARD_HOST = os.getenv('DASHBOARD_HOST', '0.0.0.0')
DASHBOARD_PORT = int(os.getenv('PORT', 5000))  # تغيير اسم المتغير ليتوافق مع bot-hosting.net

# Database Settings
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
SQLALCHEMY_DATABASE_URI = DATABASE_URL
SQLALCHEMY_TRACK_MODIFICATIONS = False 