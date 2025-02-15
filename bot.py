import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

print("بدء تشغيل البوت...")

# تحميل المتغيرات البيئية
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# إعداد Intents
intents = discord.Intents.all()
intents.message_content = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents)

# قائمة لتخزين المستخدمين المؤقتين
temp_bans = {}
temp_mutes = {}

@bot.event
async def on_ready():
    print(f'{bot.user} is ready and online!')
    print('By s7.7 - جميع الحقوق محفوظة')
    await bot.change_presence(activity=discord.Game(name="By s7.7 🔥"))

@bot.command()
@commands.has_permissions(administrator=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    """إضافة رتبة لعضو"""
    try:
        await member.add_roles(role)
        await ctx.send(f'تم إضافة رتبة {role.name} للعضو {member.name}')
    except Exception as e:
        await ctx.send(f'حدث خطأ: {str(e)}')

@bot.command()
@commands.has_permissions(administrator=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    """إزالة رتبة من عضو"""
    try:
        await member.remove_roles(role)
        await ctx.send(f'تم إزالة رتبة {role.name} من العضو {member.name}')
    except Exception as e:
        await ctx.send(f'حدث خطأ: {str(e)}')

@bot.command()
@commands.has_permissions(administrator=True)
async def nuke(ctx, channel: discord.TextChannel = None):
    """حذف جميع الرسائل في القناة"""
    channel = channel or ctx.channel
    new_channel = await channel.clone()
    await channel.delete()
    await new_channel.send('تم تنظيف القناة بنجاح!')

@bot.command()
@commands.has_permissions(administrator=True)
async def mute(ctx, member: discord.Member, duration: int = None):
    """كتم عضو"""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, speak=False, send_messages=False)
    
    await member.add_roles(muted_role)
    if duration:
        temp_mutes[member.id] = datetime.now() + timedelta(minutes=duration)
        await ctx.send(f'تم كتم {member.name} لمدة {duration} دقيقة')
        await asyncio.sleep(duration * 60)
        if member.id in temp_mutes:
            await member.remove_roles(muted_role)
            del temp_mutes[member.id]
    else:
        await ctx.send(f'تم كتم {member.name}')

@bot.command()
@commands.has_permissions(administrator=True)
async def unmute(ctx, member: discord.Member):
    """إلغاء كتم عضو"""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        if member.id in temp_mutes:
            del temp_mutes[member.id]
        await ctx.send(f'تم إلغاء كتم {member.name}')
    else:
        await ctx.send(f'{member.name} غير مكتوم')

@bot.command()
@commands.has_permissions(administrator=True)
async def tempban(ctx, member: discord.Member, duration: int):
    """حظر مؤقت لعضو"""
    await member.ban(reason=f"Temporary ban for {duration} minutes")
    temp_bans[member.id] = datetime.now() + timedelta(minutes=duration)
    await ctx.send(f'تم حظر {member.name} لمدة {duration} دقيقة')
    await asyncio.sleep(duration * 60)
    if member.id in temp_bans:
        await ctx.guild.unban(member)
        del temp_bans[member.id]
        await ctx.send(f'تم إلغاء حظر {member.name}')

@bot.command()
@commands.has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    """طرد عضو"""
    await member.kick(reason=reason)
    await ctx.send(f'تم طرد {member.name}')

def run_bot():
    try:
        print("جاري محاولة الاتصال...")
        bot.run(TOKEN, log_handler=None)
    except discord.errors.LoginFailure as e:
        print(f"خطأ في تسجيل الدخول: {str(e)}")
    except Exception as e:
        print(f"خطأ غير متوقع: {str(e)}") 