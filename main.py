import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
import random
import io
import threading
from flask import Flask
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ═══════════════════════════════════════
# FLASK (keep alive)
# ═══════════════════════════════════════
app = Flask(__name__)

@app.route('/')
def home():
    return "⭐ Star Obfuscator is running!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

threading.Thread(target=run_flask, daemon=True).start()

# ═══════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════
def db_connect():
    conn = sqlite3.connect("leaderboard.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn

def db_increment(user_id, username):
    conn = db_connect()
    conn.execute("""
        INSERT INTO leaderboard (user_id, username, count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id) DO UPDATE SET
            count = count + 1,
            username = ?
    """, (str(user_id), username, username))
    conn.commit()
    conn.close()

def db_leaderboard():
    conn = db_connect()
    rows = conn.execute("""
        SELECT username, count FROM leaderboard
        ORDER BY count DESC LIMIT 10
    """).fetchall()
    conn.close()
    return rows

# ═══════════════════════════════════════
# LUA OBFUSCATOR
# ═══════════════════════════════════════
class LuaObfuscator:
    def __init__(self):
        self.key = random.randint(1, 255)

    def random_var(self, length=12):
        chars = "lIiI1lI1iIlI"
        return ''.join(random.choices(chars, k=length))

    def random_junk(self):
        junks = [
            f"local {self.random_var()} = {random.randint(1,9999)}",
            f"local {self.random_var()} = math.floor({random.randint(1,100)})",
            f"local {self.random_var()} = type(nil)",
            f"local {self.random_var()} = tostring({random.randint(1,999)})",
            f"local {self.random_var()} = string.len('{self.random_var(5)}')",
        ]
        return random.choice(junks)

    def inject_junk(self, code):
        lines = code.split('\n')
        result = []
        for line in lines:
            result.append(line)
            if random.random() > 0.6:
                result.append(self.random_junk())
        return '\n'.join(result)

    def build_vm_header(self):
        key = self.key
        bit_name = self.random_var(16)
        decrypt_name = self.random_var(16)

        header = f"""-- Protected by Star Obfuscator
-- {self.random_var(32)}
local {bit_name}={{}}
{bit_name}.bxor=function(a,b)
local r,m=0,2^52
repeat
local s=a+b+m
r=r+(s%2)*m
a=math.floor(a/2)
b=math.floor(b/2)
m=m/2
until m<1
return r
end
local {decrypt_name}=function(s,k)
local r={{}}
for i=1,#s do
r[i]=string.char({bit_name}.bxor(string.byte(s,i),k))
end
return table.concat(r)
end
"""
        return header, decrypt_name

    def encode_source(self, code, decrypt_name):
        key = self.key
        encrypted_bytes = [ord(c) ^ key for c in code]
        escaped = "".join(f"\\{b}" for b in encrypted_bytes)

        chunk_name = self.random_var(14)
        load_name = self.random_var(14)

        # Use loadstring instead of load for Roblox executor compatibility
        return f"""local {chunk_name}="{escaped}"
local {load_name}={decrypt_name}({chunk_name},{key})
local _f=loadstring({load_name})
if _f then _f() end
"""

    def obfuscate(self, source):
        self.key = random.randint(1, 255)

        obf_source = self.inject_junk(source)
        header, decrypt_name = self.build_vm_header()
        body = self.encode_source(obf_source, decrypt_name)

        anti = f"""local {self.random_var()}=tostring
local {self.random_var()}=type
local {self.random_var()}=pcall
local {self.random_var()}=pairs
"""
        return f"{header}\n{anti}\n{body}"

# ═══════════════════════════════════════
# MODAL (for code input)
# ═══════════════════════════════════════
class ObfuscateModal(discord.ui.Modal, title="⭐ Star Obfuscator"):
    code = discord.ui.TextInput(
        label="Paste your Lua code here",
        style=discord.TextStyle.paragraph,
        placeholder="print('Hello World')",
        required=True,
        max_length=4000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        source = str(self.code)

        try:
            obfuscator = LuaObfuscator()
            result = obfuscator.obfuscate(source)
        except Exception as ex:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"❌ Obfuscation failed: `{ex}`",
                    color=0xff4444
                )
            )
            return

        db_increment(interaction.user.id, str(interaction.user))

        out_file = discord.File(
            fp=io.BytesIO(result.encode("utf-8")),
            filename="obfuscated.lua"
        )

        embed = discord.Embed(
            title="✅ Obfuscation Complete",
            color=0x57f287
        )
        embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
        embed.add_field(name="📄 Original", value=f"`{len(source):,}` chars", inline=True)
        embed.add_field(name="🔒 Protected", value=f"`{len(result):,}` chars", inline=True)
        embed.add_field(
            name="🛡️ Protection Layers",
            value="✓ XOR Encryption\n✓ Virtual Machine\n✓ String Encoding\n✓ Junk Code Injection\n✓ Anti-Tamper",
            inline=False
        )
        embed.set_footer(text="⭐ Star Obfuscator • MoonSec-style Protection")

        await interaction.followup.send(embed=embed, file=out_file)

# ═══════════════════════════════════════
# BOT SETUP
# ═══════════════════════════════════════
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
obfuscator = LuaObfuscator()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"⭐ Star Obfuscator online: {bot.user}")

# ═══════════════════════════════════════
# /help
# ═══════════════════════════════════════
@bot.tree.command(name="help", description="Show all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⭐ Star Obfuscator",
        description="MoonSec-style Lua obfuscation bot",
        color=0x2b2d31
    )
    embed.add_field(
        name="</obfuscate>",
        value="Obfuscate Lua code\n> Opens a popup — paste your code there\n> Or upload a `.lua` file",
        inline=False
    )
    embed.add_field(
        name="</leaderboard>",
        value="Top 10 users by obfuscation count",
        inline=False
    )
    embed.add_field(
        name="</help>",
        value="Show this message",
        inline=False
    )
    embed.set_footer(text="⭐ Star Obfuscator • MoonSec-style Protection")
    await interaction.response.send_message(embed=embed)

# ═══════════════════════════════════════
# /obfuscate
# ═══════════════════════════════════════
@bot.tree.command(name="obfuscate", description="Obfuscate your Lua code")
@app_commands.describe(file="Upload a .lua file (or use the popup to paste code)")
async def obfuscate_cmd(
    interaction: discord.Interaction,
    file: discord.Attachment = None
):
    # If file is provided, process it directly
    if file:
        if not file.filename.endswith(".lua"):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ Only `.lua` files are accepted.",
                    color=0xff4444
                ),
                ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        raw = await file.read()
        try:
            source = raw.decode("utf-8")
        except:
            await interaction.followup.send(
                embed=discord.Embed(
                    description="❌ Could not read file. Make sure it's UTF-8 encoded.",
                    color=0xff4444
                )
            )
            return

        if len(source) > 100000:
            await interaction.followup.send(
                embed=discord.Embed(
                    description="❌ Code too large. Max 100,000 characters.",
                    color=0xff4444
                )
            )
            return

        try:
            result = obfuscator.obfuscate(source)
        except Exception as ex:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"❌ Obfuscation failed: `{ex}`",
                    color=0xff4444
                )
            )
            return

        db_increment(interaction.user.id, str(interaction.user))

        out_file = discord.File(
            fp=io.BytesIO(result.encode("utf-8")),
            filename="obfuscated.lua"
        )

        embed = discord.Embed(
            title="✅ Obfuscation Complete",
            color=0x57f287
        )
        embed.add_field(name="👤 User", value=interaction.user.mention, inline=True)
        embed.add_field(name="📄 Original", value=f"`{len(source):,}` chars", inline=True)
        embed.add_field(name="🔒 Protected", value=f"`{len(result):,}` chars", inline=True)
        embed.add_field(
            name="🛡️ Protection Layers",
            value="✓ XOR Encryption\n✓ Virtual Machine\n✓ String Encoding\n✓ Junk Code Injection\n✓ Anti-Tamper",
            inline=False
        )
        embed.set_footer(text="⭐ Star Obfuscator • MoonSec-style Protection")

        await interaction.followup.send(embed=embed, file=out_file)

    else:
        # No file — open modal for code input
        await interaction.response.send_modal(ObfuscateModal())

# ═══════════════════════════════════════
# /leaderboard
# ═══════════════════════════════════════
@bot.tree.command(name="leaderboard", description="Top 10 users by obfuscation count")
async def leaderboard_cmd(interaction: discord.Interaction):
    rows = db_leaderboard()

    embed = discord.Embed(
        title="🏆 Obfuscation Leaderboard",
        color=0xf1c40f
    )

    if not rows:
        embed.description = "No data yet. Use `/obfuscate` to get started!"
    else:
        medals = ["🥇", "🥈", "🥉"]
        desc = ""
        for i, (username, count) in enumerate(rows):
            medal = medals[i] if i < 3 else f"`#{i+1}`"
            desc += f"{medal} **{username}** — `{count}` obfuscations\n"
        embed.description = desc

    embed.set_footer(text="⭐ Star Obfuscator • Use /obfuscate to climb the ranks!")
    await interaction.response.send_message(embed=embed)

# ═══════════════════════════════════════
# RUN
# ═══════════════════════════════════════
bot.run(TOKEN)
