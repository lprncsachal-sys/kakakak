import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import os
import random
from dotenv import load_dotenv
import sys
import re
import time

# ✅ CHARGER .env
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN:
    print("❌ Token non trouvé dans .env")
    sys.exit(1)

# ✅ IDs
ADMIN_ROLE_ID = 1469775933933224172

# ✅ INTENTS
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_giveaways = {}

# ✅ ON_READY
@bot.event
async def on_ready():
    print(f"\n{'='*60}")
    print(f"✅ BOT CONNECTÉ : {bot.user}")
    print(f"📊 SERVEURS : {len(bot.guilds)}")
    print(f"{'='*60}\n")
    print("🎮 COMMANDES DISPONIBLES :")
    print("   /test - Test le bot")
    print("   /help - Affiche l'aide")
    print("   /ping - Latence du bot")
    print("   /giveaway - Crée un giveaway (Admin)")
    print()


# ✅ COMMANDE TEST
@bot.tree.command(name="test", description="✅ Test le bot")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Bot marche !", ephemeral=True)


# ✅ COMMANDE HELP
@bot.tree.command(name="help", description="📖 Aide")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 Commandes", color=0x3498db)
    embed.add_field(name="/test", value="Test le bot", inline=False)
    embed.add_field(name="/help", value="Affiche ce message", inline=False)
    embed.add_field(name="/ping", value="Latence du bot", inline=False)
    embed.add_field(name="/giveaway", value="Crée un giveaway (Admin)", inline=False)
    embed.set_footer(text="Bot Zmacro v1")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ✅ COMMANDE PING
@bot.tree.command(name="ping", description="🏓 Latence")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong ! {latency}ms", ephemeral=True)


# ✅ COMMANDE GIVEAWAY
@bot.tree.command(name="giveaway", description="🎁 Créer un giveaway")
async def giveaway(interaction: discord.Interaction):
    # Vérifier permission
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if not role or role not in interaction.user.roles:
        await interaction.response.send_message("❌ Pas de permission !", ephemeral=True)
        return
    
    await interaction.response.send_message(
        "🎁 **Giveaway Setup**\nRépondez aux questions dans le chat :",
        ephemeral=True
    )
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel
    
    try:
        # Q1 - Nom
        await interaction.followup.send("**1️⃣ Nom du giveaway ?**", ephemeral=True)
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        name = msg.content
        
        # Q2 - Description
        await interaction.followup.send("**2️⃣ Description (ce qu'on gagne) ?**", ephemeral=True)
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        desc = msg.content
        
        # Q3 - Durée
        await interaction.followup.send("**3️⃣ Durée ? (1h, 30m, 2d)**", ephemeral=True)
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        duration_str = msg.content.strip().lower()
        
        duration = parse_duration(duration_str)
        if not duration:
            await interaction.followup.send("❌ Format invalide !", ephemeral=True)
            return
        
        # Q4 - Nombre gagnants
        await interaction.followup.send("**4️⃣ Nombre de gagnants ? (1-10)**", ephemeral=True)
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        try:
            winners = int(msg.content)
            if not (1 <= winners <= 10):
                raise ValueError
        except ValueError:
            await interaction.followup.send("❌ Nombre invalide !", ephemeral=True)
            return
        
        # Q5 - Salon
        await interaction.followup.send("**5️⃣ Salon du giveaway ? (Mentionne-le)**", ephemeral=True)
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        
        if not msg.channel_mentions:
            await interaction.followup.send("❌ Salon non trouvé !", ephemeral=True)
            return
        
        channel = msg.channel_mentions[0]
        
        # Créer le giveaway
        end_time = datetime.now() + duration
        
        embed = discord.Embed(
            title=f"🎉 {name}",
            description=f"{desc}\n\n**Réagissez avec 🎉 pour participer !**\n\n🏆 Gagnants : {winners}\n⏰ Fin : <t:{int(end_time.timestamp())}:R>",
            color=discord.Color.gold()
        )
        
        gaway_msg = await channel.send(embed=embed)
        await gaway_msg.add_reaction("🎉")
        
        active_giveaways[gaway_msg.id] = {
            'name': name,
            'channel_id': channel.id,
            'winners': winners
        }
        
        await interaction.followup.send(f"✅ Giveaway créé dans {channel.mention} !", ephemeral=True)
        
        # Attendre la fin
        await asyncio.sleep(duration.total_seconds())
        await end_giveaway(gaway_msg.id)
        
    except asyncio.TimeoutError:
        await interaction.followup.send("⏰ Temps écoulé !", ephemeral=True)


def parse_duration(s: str) -> timedelta | None:
    m = re.match(r'^(\d+)([mhd])$', s)
    if not m:
        return None
    val, unit = int(m.group(1)), m.group(2)
    if unit == 'm': return timedelta(minutes=val)
    if unit == 'h': return timedelta(hours=val)
    if unit == 'd': return timedelta(days=val)
    return None


async def end_giveaway(msg_id: int):
    if msg_id not in active_giveaways:
        return
    
    gaway = active_giveaways[msg_id]
    try:
        channel = bot.get_channel(gaway['channel_id'])
        msg = await channel.fetch_message(msg_id)
        
        reaction = discord.utils.get(msg.reactions, emoji='🎉')
        if not reaction:
            await channel.send("❌ Aucun gagnant !")
            return
        
        users = [u async for u in reaction.users() if not u.bot]
        if not users:
            await channel.send("❌ Aucun gagnant !")
            return
        
        winners = random.sample(users, min(gaway['winners'], len(users)))
        
        embed = discord.Embed(
            title=f"🎉 Giveaway terminé : {gaway['name']}",
            description="\n".join([f"🏆 {w.mention}" for w in winners]),
            color=discord.Color.green()
        )
        
        await channel.send(" ".join([w.mention for w in winners]), embed=embed)
        del active_giveaways[msg_id]
        
    except Exception as e:
        print(f"❌ Erreur giveaway : {e}")


# ✅ LANCER
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE DU BOT ZMACRO...")
    print("="*60)
    print(f"\n⏳ Attente avant connexion (évite le rate limit)...\n")
    
    # ✅ ATTENDRE 5 SECONDES AVANT DE SE CONNECTER
    time.sleep(5)
    
    print("📡 Connexion à Discord...\n")
    bot.run(TOKEN)
