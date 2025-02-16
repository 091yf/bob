from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import discord
from discord.ext import commands, tasks
import asyncio
import threading
import os
from dotenv import load_dotenv
import requests
import time
import traceback

print("بدء تشغيل النظام...")

# تحميل المتغيرات البيئية
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_CODE = os.getenv('ADMIN_CODE', 'S000')  # تحديث رمز التحقق الافتراضي
print(f"تم تحميل التوكن: {TOKEN}")

# إعداد Flask
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
print(f"مسار القوالب: {template_dir}")
print(f"هل المسار موجود: {os.path.exists(template_dir)}")

app = Flask(__name__, 
            template_folder=template_dir,
            static_folder='static')

app.config['SECRET_KEY'] = os.getenv('DASHBOARD_SECRET_KEY', 's7.7_secret_key_123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dashboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print("تم إعداد Flask")

# إعداد قاعدة البيانات
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

print("تم إعداد قاعدة البيانات")

# إعداد البوت
intents = discord.Intents.all()  # تفعيل جميع الصلاحيات
intents.members = True
intents.presences = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

print("تم إعداد البوت")

@tasks.loop(minutes=10)
async def keep_alive():
    """وظيفة للحفاظ على نشاط البوت"""
    print("البوت نشط...")
    if bot.guilds:
        guild = bot.guilds[0]
        try:
            async for _ in guild.bans(limit=1):
                break
        except Exception as e:
            print(f"خطأ في فحص النشاط: {str(e)}")

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')
    print('By s7.7 - جميع الحقوق محفوظة')
    await bot.change_presence(activity=discord.Game(name="By s7.7 🔥"))
    # بدء وظيفة الحفاظ على النشاط
    keep_alive.start()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # إضافة حقل للمشرف

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    with app.app_context():
        # حذف جميع الجداول
        db.drop_all()
        # إنشاء الجداول من جديد
        db.create_all()
        # إنشاء حساب المشرف
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("تم إنشاء حساب المشرف")

@app.route('/')
def root():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    bot_status = {
        'connected': bot.is_ready(),
        'guilds': len(bot.guilds) if bot.is_ready() else 0,
        'members': len(bot.guilds[0].members) if bot.is_ready() and bot.guilds else 0
    }
    
    return render_template('login.html', bot_status=bot_status)

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        if not bot.is_ready():
            print("البوت غير متصل")
            return render_template('dashboard.html', 
                                members=[], 
                                roles=[], 
                                banned_users=[], 
                                error="البوت غير متصل")
        
        if not bot.guilds:
            print("البوت غير متصل بأي سيرفر")
            return render_template('dashboard.html', 
                                members=[], 
                                roles=[], 
                                banned_users=[], 
                                error="البوت غير متصل بأي سيرفر")
        
        guild = bot.guilds[0]
        print(f"تم العثور على السيرفر: {guild.name}")
        print(f"عدد الأعضاء في السيرفر: {len(guild.members)}")
        
        # جلب الأعضاء
        members = []
        for member in guild.members:
            try:
                member_roles = [{"id": role.id, "name": role.name} 
                              for role in member.roles 
                              if role.name != "@everyone"]
                member_data = {
                    "id": member.id,
                    "name": member.name,
                    "roles": member_roles,
                    "status": str(member.status)
                }
                members.append(member_data)
                print(f"تم إضافة العضو: {member.name}")
            except Exception as e:
                print(f"خطأ في جلب معلومات العضو {member.name}: {str(e)}")
        
        # جلب الرتب
        roles = []
        for role in guild.roles:
            if role.name != "@everyone":
                roles.append({
                    "id": role.id,
                    "name": role.name,
                    "color": str(role.color)
                })
        
        # جلب المحظورين
        banned_users = []
        try:
            async def get_bans():
                return [ban async for ban in guild.bans()]
            banned_users = asyncio.run_coroutine_threadsafe(get_bans(), bot.loop).result()
            banned_users = [{"id": ban.user.id, "name": ban.user.name, "reason": ban.reason or "غير محدد"} 
                          for ban in banned_users]
        except Exception as e:
            print(f"خطأ في جلب المحظورين: {str(e)}")
        
        print(f"تم جلب {len(members)} عضو و {len(roles)} رتبة و {len(banned_users)} محظور")
        
        return render_template('dashboard.html', 
                             members=members, 
                             roles=roles, 
                             banned_users=banned_users)
                             
    except Exception as e:
        print(f"خطأ في لوحة التحكم: {str(e)}")
        print("Stack trace:", traceback.format_exc())
        return render_template('dashboard.html', 
                             members=[], 
                             roles=[], 
                             banned_users=[], 
                             error=str(e))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    print(f"طريقة الطلب: {request.method}")
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        print(f"محاولة تسجيل دخول: {username}")
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            print("تم تسجيل الدخول بنجاح")
            return redirect(url_for('dashboard'))
        print("فشل تسجيل الدخول")
        flash('اسم المستخدم أو كلمة المرور غير صحيحة')
    try:
        return render_template('login.html')
    except Exception as e:
        print(f"خطأ في عرض صفحة تسجيل الدخول: {str(e)}")
        return str(e), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    verify_code = request.form.get('verify_code')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    print(f"رمز التحقق المدخل: {verify_code}")
    print(f"رمز التحقق المتوقع: {ADMIN_CODE}")
    
    # التحقق من رمز التحقق
    if verify_code != str(ADMIN_CODE):  # تحويل ADMIN_CODE إلى نص للمقارنة
        flash('رمز التحقق غير صحيح', 'error')
        return redirect(url_for('dashboard'))
    
    # التحقق من تطابق كلمتي المرور
    if new_password != confirm_password:
        flash('كلمتا المرور غير متطابقتين', 'error')
        return redirect(url_for('dashboard'))
    
    # تحديث كلمة المرور
    user = User.query.filter_by(username=current_user.username).first()
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    flash('تم تغيير كلمة المرور بنجاح', 'success')
    return redirect(url_for('dashboard'))

@app.route('/kick_member/<member_id>', methods=['POST'])
@login_required
def kick_member(member_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'غير مصرح لك بهذا الإجراء'})
    
    try:
        guild = bot.guilds[0]
        member = guild.get_member(int(member_id))
        
        if not member:
            return jsonify({'success': False, 'error': 'لم يتم العثور على العضو'})
            
        asyncio.run_coroutine_threadsafe(member.kick(), bot.loop).result()
        return jsonify({'success': True, 'message': 'تم طرد العضو بنجاح'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mute_member/<member_id>', methods=['POST'])
@login_required
def mute_member(member_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'غير مصرح لك بهذا الإجراء'})
    
    try:
        guild = bot.guilds[0]
        member = guild.get_member(int(member_id))
        
        if not member:
            return jsonify({'success': False, 'error': 'لم يتم العثور على العضو'})
            
        muted_role = discord.utils.get(guild.roles, name="Muted")
        if not muted_role:
            muted_role = asyncio.run_coroutine_threadsafe(
                guild.create_role(name="Muted"),
                bot.loop
            ).result()
            for channel in guild.channels:
                asyncio.run_coroutine_threadsafe(
                    channel.set_permissions(muted_role, send_messages=False, speak=False),
                    bot.loop
                ).result()
                
        asyncio.run_coroutine_threadsafe(member.add_roles(muted_role), bot.loop).result()
        return jsonify({'success': True, 'message': 'تم كتم العضو بنجاح'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/ban_member/<member_id>', methods=['POST'])
@login_required
def ban_member(member_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'غير مصرح لك بهذا الإجراء'})
    
    try:
        guild = bot.guilds[0]
        member = guild.get_member(int(member_id))
        
        if not member:
            return jsonify({'success': False, 'error': 'لم يتم العثور على العضو'})
            
        asyncio.run_coroutine_threadsafe(member.ban(), bot.loop).result()
        return jsonify({'success': True, 'message': 'تم حظر العضو بنجاح'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/add_role', methods=['POST'])
@login_required
def add_role_form():
    if not current_user.is_admin:
        flash('غير مصرح لك بهذا الإجراء', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        member_id = request.form.get('member')
        role_id = request.form.get('role')
        
        guild = bot.guilds[0]
        member = guild.get_member(int(member_id))
        role = guild.get_role(int(role_id))
        
        if member and role:
            asyncio.run_coroutine_threadsafe(member.add_roles(role), bot.loop).result()
            flash('تم إضافة الرتبة بنجاح', 'success')
        else:
            flash('لم يتم العثور على العضو أو الرتبة', 'error')
            
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/remove_role', methods=['POST'])
@login_required
def remove_role():
    if not current_user.is_admin:
        flash('غير مصرح لك بهذا الإجراء', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        member_id = request.form.get('member')
        role_id = request.form.get('role')
        
        guild = bot.guilds[0]
        member = guild.get_member(int(member_id))
        role = guild.get_role(int(role_id))
        
        if member and role:
            # التحقق من أن رتبة البوت أعلى من الرتبة المراد إزالتها
            bot_member = guild.get_member(bot.user.id)
            if bot_member.top_role.position > role.position:
                asyncio.run_coroutine_threadsafe(member.remove_roles(role), bot.loop).result()
                flash('تم إزالة الرتبة بنجاح', 'success')
            else:
                flash('لا يمكن إزالة هذه الرتبة - رتبة البوت أقل من الرتبة المطلوبة', 'error')
        else:
            flash('لم يتم العثور على العضو أو الرتبة', 'error')
            
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/moderate', methods=['POST'])
@login_required
def moderate():
    if not current_user.is_admin:
        flash('غير مصرح لك بهذا الإجراء', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        member_id = request.form.get('member')
        action = request.form.get('action')
        duration = request.form.get('duration')
        
        guild = bot.guilds[0]
        member = guild.get_member(int(member_id))
        
        if not member:
            flash('لم يتم العثور على العضو', 'error')
            return redirect(url_for('dashboard'))
            
        if action == 'mute':
            # التعامل مع الكتم
            muted_role = discord.utils.get(guild.roles, name="Muted")
            if not muted_role:
                muted_role = asyncio.run_coroutine_threadsafe(
                    guild.create_role(name="Muted"),
                    bot.loop
                ).result()
                for channel in guild.channels:
                    asyncio.run_coroutine_threadsafe(
                        channel.set_permissions(muted_role, send_messages=False, speak=False),
                        bot.loop
                    ).result()
            asyncio.run_coroutine_threadsafe(member.add_roles(muted_role), bot.loop).result()
            flash('تم كتم العضو بنجاح', 'success')
            
        elif action == 'ban':
            # التعامل مع الحظر
            asyncio.run_coroutine_threadsafe(member.ban(), bot.loop).result()
            flash('تم حظر العضو بنجاح', 'success')
            
        elif action == 'kick':
            # التعامل مع الطرد
            asyncio.run_coroutine_threadsafe(member.kick(), bot.loop).result()
            flash('تم طرد العضو بنجاح', 'success')
            
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/unban', methods=['POST'])
@login_required
def unban():
    if not current_user.is_admin:
        flash('غير مصرح لك بهذا الإجراء', 'error')
        return redirect(url_for('dashboard'))
        
    try:
        user_id = request.form.get('user')
        guild = bot.guilds[0]
        
        # جلب المستخدم وفك الحظر
        banned_user = asyncio.run_coroutine_threadsafe(
            bot.fetch_user(int(user_id)),
            bot.loop
        ).result()
        
        if banned_user:
            asyncio.run_coroutine_threadsafe(
                guild.unban(banned_user),
                bot.loop
            ).result()
            flash('تم فك الحظر بنجاح', 'success')
        else:
            flash('لم يتم العثور على المستخدم', 'error')
            
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        flash(f'حدث خطأ: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/status')
def status():
    """التحقق من حالة البوت"""
    if not bot.is_ready():
        return jsonify({
            'status': 'error',
            'message': 'البوت غير متصل',
            'guilds': 0
        })
    return jsonify({
        'status': 'ok',
        'message': 'البوت متصل',
        'guilds': len(bot.guilds)
    })

def run_bot():
    try:
        print("جاري محاولة تشغيل البوت...")
        print(f"Token being used: {TOKEN[:10]}...") # طباعة جزء من التوكن للتحقق
        print("Intents enabled:", {
            "members": intents.members,
            "presences": intents.presences,
            "message_content": intents.message_content,
            "guilds": intents.guilds,
            "bans": intents.bans
        })
        bot.run(TOKEN, reconnect=True)
    except discord.LoginFailure as e:
        print(f"خطأ في تسجيل الدخول للبوت: {str(e)}")
        print("تأكد من صحة التوكن في إعدادات Render")
        print("الرجاء التحقق من:")
        print("1. صحة التوكن في إعدادات Render")
        print("2. تفعيل صلاحيات البوت في بوابة Discord Developer")
        print("3. وجود البوت في السيرفر")
    except discord.HTTPException as e:
        print(f"خطأ في الاتصال: {str(e)}")
        print("قد تكون هناك مشكلة في الاتصال بخوادم Discord")
    except Exception as e:
        print(f"خطأ غير متوقع في تشغيل البوت: {str(e)}")
        print("Stack trace:", traceback.format_exc())

def keep_web_alive():
    """وظيفة للحفاظ على نشاط الويب سيرفر"""
    while True:
        try:
            # الحصول على عنوان التطبيق من المتغيرات البيئية
            app_url = os.getenv('APP_URL', 'http://localhost:5000')
            response = requests.get(app_url)
            print(f"حالة الويب سيرفر: {response.status_code}")
        except Exception as e:
            print(f"خطأ في فحص نشاط الويب سيرفر: {str(e)}")
        time.sleep(300)  # انتظار 5 دقائق

if __name__ == '__main__':
    print("يمكنك الوصول إلى لوحة التحكم على: http://localhost:5000")
    print("بيانات الدخول:")
    print("اسم المستخدم: admin")
    print("كلمة المرور: admin123")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
else:
    # تهيئة قاعدة البيانات
    init_db()
    
    # تشغيل البوت في خلفية منفصلة
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # تشغيل وظيفة الحفاظ على نشاط الويب سيرفر في خلفية منفصلة
    web_alive_thread = threading.Thread(target=keep_web_alive, daemon=True)
    web_alive_thread.start()
    
    print("تم بدء تشغيل البوت في الخلفية")
    
    # إضافة فترة انتظار للتأكد من اتصال البوت
    time.sleep(5)
    if not bot.is_ready():
        print("تحذير: البوت لم يتصل بعد")
    else:
        print(f"البوت متصل بنجاح كـ {bot.user.name}")
        if bot.guilds:
            print(f"متصل بـ {len(bot.guilds)} سيرفر")
            print(f"السيرفر الأول: {bot.guilds[0].name}")
            print(f"عدد الأعضاء: {len(bot.guilds[0].members)}")
    
    application = app 