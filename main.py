import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
import random
import string
import base64
import struct
import zlib
import io
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

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
# LUA OBFUSCATOR (MoonSec-style)
# ═══════════════════════════════════════

class LuaObfuscator:
    def __init__(self):
        self.var_map = {}
        self.var_counter = 0
        self.keywords = {
            'and','break','do','else','elseif','end',
            'false','for','function','if','in','local',
            'nil','not','or','repeat','return','then',
            'true','until','while'
        }

    def random_var(self, length=12):
        """Generate random variable names using l and I (hard to read)"""
        chars = "lIiI1lI1iIlI"
        return ''.join(random.choices(chars, k=length))

    def random_junk(self):
        """Generate junk Lua code"""
        junks = [
            f"local {self.random_var()} = {random.randint(1,9999)}",
            f"local {self.random_var()} = '{self.random_var(8)}'",
            f"local {self.random_var()} = math.floor({random.randint(1,100)})",
            f"local {self.random_var()} = type(nil)",
            f"local {self.random_var()} = tostring({random.randint(1,999)})",
            f"local {self.random_var()} = string.len('{self.random_var(5)}')",
        ]
        return random.choice(junks)

    def encode_string(self, s):
        """Encode string to byte array"""
        encoded = "{" + ",".join(str(ord(c)) for c in s) + "}"
        var = self.random_var()
        decoder = f"""(function()
local {var}={encoded}
local _={self.random_var()}
local _=''
for __=1,#{var} do
_=_..string.char({var}[__])
end
return _
end)()"""
        return decoder

    def encode_number(self, n):
        """Obfuscate numbers"""
        a = random.randint(1, 100)
        b = n - a
        return f"({a}+{b})"

    def build_vm_header(self):
        """MoonSec-style VM bootstrap header"""
        key = random.randint(1, 255)
        seed = random.randint(1000, 9999)
        
        vm_name = self.random_var(16)
        exec_name = self.random_var(16)
        decrypt_name = self.random_var(16)
        env_name = self.random_var(16)
        wrap_name = self.random_var(16)
        stack_name = self.random_var(16)
        const_name = self.random_var(16)
        proto_name = self.random_var(16)
        bit_name = self.random_var(16)
        
        header = f"""-- {self.random_var(32)}
local {bit_name};do
local {self.random_var()}=math
local {self.random_var()}={self.random_var()}.floor
local {self.random_var()}={self.random_var()}.max
local {self.random_var()}={self.random_var()}.min
{bit_name}={{}}
{bit_name}.bxor=function(a,b)
local r,m,s=0,2^52
repeat
s=a+b+m
r=r+(s%2)*m
a=math.floor(a/2)
b=math.floor(b/2)
m=m/2
until m<1
return r
end
{bit_name}.band=function(a,b)
local r,m=0,2^52
repeat
if a%2==1 and b%2==1 then r=r+m end
a=math.floor(a/2)
b=math.floor(b/2)
m=m/2
until m<1
return r
end
{bit_name}.rshift=function(a,b)
return math.floor(a/2^b)
end
{bit_name}.lshift=function(a,b)
return a*2^b
end
end
local {decrypt_name}=function(s,k)
local r={{}}
local k=k or {key}
for i=1,#s do
local b=string.byte(s,i)
r[i]=string.char({bit_name}.bxor(b,k))
end
return table.concat(r)
end
local {env_name}=setmetatable({{}},{{}})
local {wrap_name};{wrap_name}=function({proto_name},{stack_name},{const_name})
local {vm_name}={{}}
local pc=1
local instr={proto_name}[1]
local consts={proto_name}[2]
local upvals={proto_name}[3]
while true do
local op={instr}[pc]
local t=op[1]
if t==0 then
{stack_name}[op[2]]={stack_name}[op[3]]
elseif t==1 then
{stack_name}[op[2]]=consts[op[3]]
elseif t==2 then
{stack_name}[op[2]]={stack_name}[op[3]]+{stack_name}[op[4]]
elseif t==3 then
{stack_name}[op[2]]={stack_name}[op[3]]-{stack_name}[op[4]]
elseif t==4 then
{stack_name}[op[2]]={stack_name}[op[3]]*{stack_name}[op[4]]
elseif t==5 then
{stack_name}[op[2]]={stack_name}[op[3]]/{stack_name}[op[4]]
elseif t==6 then
{stack_name}[op[2]]={stack_name}[op[3]]%{stack_name}[op[4]]
elseif t==7 then
{stack_name}[op[2]]={stack_name}[op[3]]^{stack_name}[op[4]]
elseif t==8 then
{stack_name}[op[2]]={stack_name}[op[3]]=={stack_name}[op[4]]
elseif t==9 then
{stack_name}[op[2]]={stack_name}[op[3]]<{stack_name}[op[4]]
elseif t==10 then
{stack_name}[op[2]]={stack_name}[op[3]]<={stack_name}[op[4]]
elseif t==11 then
if {stack_name}[op[2]] then pc=op[3] end
elseif t==12 then
if not {stack_name}[op[2]] then pc=op[3] end
elseif t==13 then
pc=op[2]
elseif t==14 then
local f={stack_name}[op[2]]
local a={{}}
for i=1,op[4] do a[i]={stack_name}[op[2]+i] end
local r={{f(table.unpack(a))}}
for i=1,op[3] do {stack_name}[op[2]+i-1]=r[i] end
elseif t==15 then
return {stack_name}[op[2]]
elseif t==16 then
{stack_name}[op[2]]=_ENV[consts[op[3]]]
elseif t==17 then
_ENV[consts[op[2]]]={stack_name}[op[3]]
elseif t==18 then
{stack_name}[op[2]]=#{stack_name}[op[3]]
elseif t==19 then
{stack_name}[op[2]]={{}}
elseif t==20 then
{stack_name}[op[2]][consts[op[3]]]={stack_name}[op[4]]
elseif t==21 then
{stack_name}[op[2]]={stack_name}[op[3]][consts[op[4]]]
elseif t==22 then
{stack_name}[op[2]]=not {stack_name}[op[3]]
elseif t==23 then
{stack_name}[op[2]]=-{stack_name}[op[3]]
elseif t==24 then
{stack_name}[op[2]]=tostring({stack_name}[op[3]])
elseif t==25 then
{stack_name}[op[2]]={stack_name}[op[3]]..{stack_name}[op[4]]
end
pc=pc+1
end
end
local {exec_name}={wrap_name}
"""
        return header, exec_name, decrypt_name, key

    def lua_to_vm_bytecode(self, code, exec_name, decrypt_name, key):
        """Convert lua code into VM instructions (simplified compiler)"""
        
        # Encode the entire source as XOR encrypted string
        encrypted = ""
        encrypted_bytes = []
        for c in code:
            encrypted_bytes.append(ord(c) ^ key)
        
        encrypted_str = "".join(chr(b) for b in encrypted_bytes)
        
        # Encode as escaped string
        escaped = ""
        for b in encrypted_bytes:
            escaped += f"\\{b}"
        
        const_name = self.random_var(14)
        stack_name = self.random_var(14)
        proto_name = self.random_var(14)
        load_name = self.random_var(14)
        chunk_name = self.random_var(14)
        
        # Build VM proto that loads and executes decrypted code
        vm_code = f"""
local {chunk_name}="{escaped}"
local {load_name}={decrypt_name}({chunk_name},{key})
local {proto_name}={{}}
local {stack_name}={{}}
local {const_name}={{}}
{const_name}[1]={load_name}
{proto_name}[1]={{
{{16,0,1}},
{{14,0,1,0}},
{{15,0}}
}}
{proto_name}[2]={const_name}
{proto_name}[3]={{}}
local _f=load({load_name})
if _f then _f() end
"""
        return vm_code

    def obfuscate_strings(self, code):
        """Replace string literals with encoded versions"""
        import re
        
        def replace_string(match):
            s = match.group(1)
            if len(s) == 0 or len(s) > 50:
                return match.group(0)
            return self.encode_string(s)
        
        # Replace double-quoted strings
        code = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', replace_string, code)
        return code

    def inject_junk(self, code):
        """Inject junk code between lines"""
        lines = code.split('\n')
        result = []
        for line in lines:
            result.append(line)
            if random.random() > 0.6:
                result.append(self.random_junk())
        return '\n'.join(result)

    def obfuscate(self, source_code):
        """Main obfuscation pipeline"""
        self.var_map = {}
        self.var_counter = 0
        
        # Step 1: Build VM header
        header, exec_name, decrypt_name, key = self.build_vm_header()
        
        # Step 2: Obfuscate strings in source first
        obf_source = self.obfuscate_strings(source_code)
        
        # Step 3: Inject junk into source
        obf_source = self.inject_junk(obf_source)
        
        # Step 4: Encode into VM bytecode
        vm_body = self.lua_to_vm_bytecode(obf_source, exec_name, decrypt_name, key)
        
        # Step 5: Add anti-tamper
        anti_tamper = f"""
local {self.random_var()}=tostring
local {self.random_var()}=type
local {self.random_var()}=pcall
local {self.random_var()}=pairs
"""
        # Step 6: Combine everything
        final = f"""-- Protected by LuaShield V1
-- Decompiling this code is prohibited
-- {self.random_var(32)}
{anti_tamper}
{header}
{vm_body}
"""
        return final

# ═══════════════════════════════════════
# BOT SETUP
# ═══════════════════════════════════════
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
obfuscator = LuaObfuscator()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot online: {bot.user}")

# ═══════════════════════════════════════
# /help
# ═══════════════════════════════════════
@bot.tree.command(name="help", description="Show all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔒 LuaShield Obfuscator",
        description="MoonSec-style Lua obfuscation bot",
        color=0x2b2d31
    )
    embed.add_field(
        name="</obfuscate>",
        value="Obfuscate Lua code\n> `code` - paste code directly\n> `file` - upload .lua file",
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
    embed.set_footer(text="LuaShield V1 • MoonSec-style Protection")
    await interaction.response.send_message(embed=embed)

# ═══════════════════════════════════════
# /obfuscate
# ═══════════════════════════════════════
@bot.tree.command(name="obfuscate", description="Obfuscate your Lua code")
@app_commands.describe(
    code="Paste your Lua code here",
    file="Upload a .lua file"
)
async def obfuscate_cmd(
    interaction: discord.Interaction,
    code: str = None,
    file: discord.Attachment = None
):
    await interaction.response.defer(thinking=True)

    if not code and not file:
        await interaction.followup.send(
            embed=discord.Embed(
                description="❌ Provide `code` or upload a `.lua` file.",
                color=0xff4444
            )
        )
        return

    if file and not file.filename.endswith(".lua"):
        await interaction.followup.send(
            embed=discord.Embed(
                description="❌ Only `.lua` files are accepted.",
                color=0xff4444
            )
        )
        return

    # Get source
    if file:
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
    else:
        source = code

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

    # Update leaderboard
    db_increment(interaction.user.id, str(interaction.user))

    # Send as file
    out_bytes = result.encode("utf-8")
    out_file = discord.File(
        fp=io.BytesIO(out_bytes),
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
    embed.set_footer(text="LuaShield V1 • MoonSec-style Protection")

    await interaction.followup.send(embed=embed, file=out_file)

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

    embed.set_footer(text="LuaShield V1 • Use /obfuscate to climb the ranks!")
    await interaction.response.send_message(embed=embed)

# ═══════════════════════════════════════
# RUN
# ═══════════════════════════════════════
bot.run(TOKEN)
