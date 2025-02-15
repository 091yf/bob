from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import discord
from discord.ext import commands
import asyncio
import threading
from functools import wraps
import os
from dotenv import load_dotenv

print("بدء تشغيل النظام...")

# تحميل المتغيرات البيئية
load_dotenv()

# تعريف المتغيرات من الملف البيئي
TOKEN = os.getenv('DISCORD_TOKEN')
DASHBOARD_SECRET_KEY = os.getenv('DASHBOARD_SECRET_KEY', 's7.7_secret_key_123')
PORT = int(os.getenv('PORT', 5000))

print(f"المنفذ المستخدم: {PORT}")

app = Flask(__name__)
app.config['SECRET_KEY'] = DASHBOARD_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# إعداد Discord client
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')
    print('By s7.7 - جميع الحقوق محفوظة')
    await bot.change_presence(activity=discord.Game(name="By s7.7 🔥"))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin',
                        password_hash=generate_password_hash('admin123'))
            db.session.add(admin)
            db.session.commit()
            print("تم إنشاء حساب المشرف")

@app.route('/')
@login_required
def index():
    try:
        if not bot.guilds:
            return render_template('dashboard.html', members=[], roles=[], banned_users=[], error="البوت غير متصل بأي سيرفر")
        
        guild = bot.guilds[0]
        members = [{"id": member.id, "name": member.name, "roles": [{"id": role.id, "name": role.name} for role in member.roles]} for member in guild.members]
        roles = [{"id": role.id, "name": role.name} for role in guild.roles]
        
        banned_users = []
        try:
            async def get_bans():
                return [ban async for ban in guild.bans()]
            banned_users = run_async(get_bans())
            banned_users = [{"id": ban.user.id, "name": ban.user.name, "reason": ban.reason} for ban in banned_users]
        except Exception as e:
            print(f"خطأ في جلب المحظورين: {str(e)}")
        
        return render_template('dashboard.html', members=members, roles=roles, banned_users=banned_users)
    except Exception as e:
        print(f"خطأ: {str(e)}")
        return render_template('dashboard.html', members=[], roles=[], banned_users=[], error=str(e))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/unban', methods=['POST'])
@login_required
def unban():
    user_id = request.form.get('user')
    try:
        guild = bot.guilds[0]
        async def do_unban():
            user = await bot.fetch_user(int(user_id))
            if user:
                await guild.unban(user)
                return user
            return None
        
        user = run_async(do_unban())
        if user:
            flash(f'تم فك الحظر عن المستخدم {user.name}', 'success')
        else:
            flash('لم يتم العثور على المستخدم', 'error')
    except discord.NotFound:
        flash('لم يتم العثور على المستخدم', 'error')
    except discord.Forbidden:
        flash('ليس لدي الصلاحيات الكافية لفك الحظر', 'error')
    except Exception as e:
        print(f"خطأ في فك الحظر: {str(e)}")
        flash(f'حدث خطأ: {str(e)}', 'error')
    return redirect(url_for('index'))

def run_dashboard():
    init_db()
    print(f"بدء تشغيل لوحة التحكم على المنفذ {PORT}")
    app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    run_dashboard() 