import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import os
import random
from dotenv import load_dotenv
import sys
import re
import logging
from aiohttp import web

# ✅ CONFIGURATION DU LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('discord_bot')

# ✅ CHARGER .env
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN:
    logger.error("❌ Token non trouvé dans .env")
    sys.exit(1)

# ✅ IDs
ADMIN_ROLE_ID = 1469775933933224172

# ✅ INTENTS
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_giveaways = {}

# ✅ ON_READY avec synchronisation des commandes
@bot.event
async def on_ready():
    logger.info("="*60)
    logger.info(f"✅ BOT CONNECTÉ : {bot.user}")
    logger.info(f"📊 SERVEURS : {len(bot.guilds)}")
    logger.info("="*60)
    
    # 🔄 SYNCHRONISER LES COMMANDES SLASH
    try:
        logger.info("🔄 Synchronisation des commandes slash...")
        synced = await bot.tree.sync()
        logger.info(f"✅ {len(synced)} commandes synchronisées avec succès")
        logger.info("🎮 COMMANDES DISPONIBLES :")
        for cmd in synced:
            logger.info(f"   /{cmd.name} - {cmd.description}")
    except Exception as e:
        logger.error(f"❌ Erreur de synchronisation : {e}")
    
    logger.info("\n✅ Bot prêt à recevoir des commandes !")


# ✅ GESTION DES ERREURS DE CONNEXION
@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"❌ Erreur dans {event}: {sys.exc_info()}")


# ✅ COMMANDE TEST
@bot.tree.command(name="test", description="✅ Test le bot")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Bot fonctionne parfaitement !", ephemeral=True)


# ✅ COMMANDE HELP
@bot.tree.command(name="help", description="📖 Affiche l'aide et les commandes disponibles")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Commandes du Bot Zmacro",
        description="Voici toutes les commandes disponibles :",
        color=0x3498db
    )
    embed.add_field(name="/test", value="✅ Teste si le bot fonctionne", inline=False)
    embed.add_field(name="/help", value="📖 Affiche ce message d'aide", inline=False)
    embed.add_field(name="/ping", value="🏓 Affiche la latence du bot", inline=False)
    embed.add_field(name="/giveaway", value="🎁 Crée un giveaway (Admin uniquement)", inline=False)
    embed.set_footer(text="Bot Zmacro v2.0 | Développé avec ❤️")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ✅ COMMANDE PING
@bot.tree.command(name="ping", description="🏓 Affiche la latence du bot")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    
    # Déterminer la qualité de la connexion
    if latency < 100:
        status = "🟢 Excellente"
    elif latency < 200:
        status = "🟡 Bonne"
    elif latency < 500:
        status = "🟠 Moyenne"
    else:
        status = "🔴 Lente"
    
    embed = discord.Embed(
        title="🏓 Pong !",
        description=f"**Latence :** {latency}ms\n**Statut :** {status}",
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ✅ COMMANDE GIVEAWAY AMÉLIORÉE
@bot.tree.command(name="giveaway", description="🎁 Créer un giveaway interactif")
async def giveaway(interaction: discord.Interaction):
    # Vérifier permission
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if not role or role not in interaction.user.roles:
        embed = discord.Embed(
            title="❌ Accès refusé",
            description="Vous n'avez pas la permission de créer des giveaways.\nRôle requis : Admin",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.send_message(
        "🎁 **Configuration du Giveaway**\nRépondez aux questions suivantes dans le chat :",
        ephemeral=True
    )
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel
    
    try:
        # Q1 - Nom
        await interaction.followup.send("**1️⃣ Quel est le nom du giveaway ?**", ephemeral=True)
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        name = msg.content
        await msg.delete()  # Nettoyer le message
        
        # Q2 - Description
        await interaction.followup.send("**2️⃣ Que peut-on gagner ? (description)**", ephemeral=True)
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        desc = msg.content
        await msg.delete()
        
        # Q3 - Durée
        await interaction.followup.send(
            "**3️⃣ Durée du giveaway ?**\n"
            "Formats acceptés : `30s`, `5m`, `2h`, `1d`\n"
            "Exemples : `1h`, `30m`, `2d`",
            ephemeral=True
        )
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        duration_str = msg.content.strip().lower()
        await msg.delete()
        
        duration = parse_duration(duration_str)
        if not duration:
            await interaction.followup.send("❌ Format de durée invalide ! Utilisez : 30s, 5m, 2h, 1d", ephemeral=True)
            return
        
        # Q4 - Nombre gagnants
        await interaction.followup.send("**4️⃣ Nombre de gagnants ? (1-10)**", ephemeral=True)
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        try:
            winners = int(msg.content)
            await msg.delete()
            if not (1 <= winners <= 10):
                raise ValueError
        except ValueError:
            await interaction.followup.send("❌ Nombre invalide ! Entrez un nombre entre 1 et 10.", ephemeral=True)
            return
        
        # Q5 - Salon
        await interaction.followup.send("**5️⃣ Dans quel salon créer le giveaway ?** (Mentionnez-le avec #)", ephemeral=True)
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        
        if not msg.channel_mentions:
            await interaction.followup.send("❌ Aucun salon mentionné ! Utilisez # pour mentionner un salon.", ephemeral=True)
            return
        
        channel = msg.channel_mentions[0]
        await msg.delete()
        
        # Créer le giveaway
        end_time = datetime.now() + duration
        
        embed = discord.Embed(
            title=f"🎉 {name}",
            description=f"**{desc}**\n\n"
                       f"Réagissez avec 🎉 pour participer !\n\n"
                       f"🏆 **Nombre de gagnants :** {winners}\n"
                       f"⏰ **Se termine :** <t:{int(end_time.timestamp())}:R>\n"
                       f"👤 **Organisé par :** {interaction.user.mention}",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"ID: {random.randint(1000, 9999)} | Bonne chance !")
        embed.timestamp = datetime.now()
        
        gaway_msg = await channel.send(embed=embed)
        await gaway_msg.add_reaction("🎉")
        
        active_giveaways[gaway_msg.id] = {
            'name': name,
            'channel_id': channel.id,
            'winners': winners,
            'host': interaction.user.id
        }
        
        confirmation_embed = discord.Embed(
            title="✅ Giveaway créé avec succès !",
            description=f"📍 **Salon :** {channel.mention}\n"
                       f"🎁 **Nom :** {name}\n"
                       f"⏰ **Durée :** {duration_str}\n"
                       f"🏆 **Gagnants :** {winners}",
            color=0x2ecc71
        )
        await interaction.followup.send(embed=confirmation_embed, ephemeral=True)
        
        logger.info(f"🎁 Giveaway créé par {interaction.user} dans #{channel.name}")
        
        # Attendre la fin
        await asyncio.sleep(duration.total_seconds())
        await end_giveaway(gaway_msg.id)
        
    except asyncio.TimeoutError:
        await interaction.followup.send("⏰ Temps écoulé ! Configuration annulée.", ephemeral=True)
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création du giveaway : {e}")
        await interaction.followup.send(f"❌ Une erreur s'est produite : {e}", ephemeral=True)


def parse_duration(s: str) -> timedelta | None:
    """Parse une durée au format 30s, 5m, 2h, 1d"""
    m = re.match(r'^(\d+)([smhd])$', s)
    if not m:
        return None
    val, unit = int(m.group(1)), m.group(2)
    if unit == 's': return timedelta(seconds=val)
    if unit == 'm': return timedelta(minutes=val)
    if unit == 'h': return timedelta(hours=val)
    if unit == 'd': return timedelta(days=val)
    return None


async def end_giveaway(msg_id: int):
    """Termine un giveaway et annonce les gagnants"""
    if msg_id not in active_giveaways:
        return
    
    gaway = active_giveaways[msg_id]
    try:
        channel = bot.get_channel(gaway['channel_id'])
        if not channel:
            logger.error(f"❌ Salon introuvable pour le giveaway {msg_id}")
            return
            
        msg = await channel.fetch_message(msg_id)
        
        reaction = discord.utils.get(msg.reactions, emoji='🎉')
        if not reaction:
            embed = discord.Embed(
                title="❌ Giveaway terminé",
                description=f"**{gaway['name']}**\n\nAucune participation ! Aucun gagnant.",
                color=0xe74c3c
            )
            await channel.send(embed=embed)
            del active_giveaways[msg_id]
            return
        
        users = [u async for u in reaction.users() if not u.bot]
        if not users:
            embed = discord.Embed(
                title="❌ Giveaway terminé",
                description=f"**{gaway['name']}**\n\nAucun participant valide ! Aucun gagnant.",
                color=0xe74c3c
            )
            await channel.send(embed=embed)
            del active_giveaways[msg_id]
            return
        
        winners = random.sample(users, min(gaway['winners'], len(users)))
        
        # Embed des gagnants
        winners_text = "\n".join([f"🏆 {w.mention}" for w in winners])
        embed = discord.Embed(
            title=f"🎉 Giveaway terminé !",
            description=f"**{gaway['name']}**\n\n**Gagnant(s) :**\n{winners_text}\n\n"
                       f"Félicitations ! 🎊",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"{len(users)} participant(s) au total")
        embed.timestamp = datetime.now()
        
        await channel.send(" ".join([w.mention for w in winners]), embed=embed)
        
        # Mettre à jour le message original
        original_embed = msg.embeds[0]
        original_embed.color = discord.Color.red()
        original_embed.description = f"~~{original_embed.description}~~\n\n**✅ TERMINÉ**"
        await msg.edit(embed=original_embed)
        
        del active_giveaways[msg_id]
        logger.info(f"🎊 Giveaway terminé : {gaway['name']} - {len(winners)} gagnant(s)")
        
    except discord.NotFound:
        logger.error(f"❌ Message de giveaway introuvable : {msg_id}")
        del active_giveaways[msg_id]
    except Exception as e:
        logger.error(f"❌ Erreur lors de la fin du giveaway {msg_id} : {e}")


# ✅ SERVEUR HTTP POUR RENDER (satisfait le health check)
async def health_check(request):
    """Endpoint pour le health check de Render"""
    return web.Response(text="✅ Bot is running", status=200)

async def start_web_server():
    """Lance un mini serveur HTTP pour Render"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    port = int(os.getenv('PORT', 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 Serveur HTTP démarré sur le port {port}")


# ✅ LANCER LE BOT AVEC GESTION D'ERREURS
async def main():
    """Fonction principale avec gestion des erreurs"""
    logger.info("\n" + "="*60)
    logger.info("🚀 DÉMARRAGE DU BOT ZMACRO...")
    logger.info("="*60)
    
    # 🌐 Lancer le serveur HTTP (pour Render)
    asyncio.create_task(start_web_server())
    
    # ⏳ VRAI DÉLAI AVANT CONNEXION (évite rate limiting)
    delay = 5
    logger.info(f"⏳ Attente de {delay}s avant connexion (évite le rate limit)...")
    await asyncio.sleep(delay)
    
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"📡 Tentative de connexion à Discord... ({retry_count + 1}/{max_retries})")
            await bot.start(TOKEN)
            break  # Si succès, sortir de la boucle
            
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limited
                retry_after = int(e.response.headers.get('Retry-After', 60))
                logger.warning(f"⚠️  Rate limit détecté ! Attente de {retry_after}s...")
                await asyncio.sleep(retry_after)
                retry_count += 1
            else:
                logger.error(f"❌ Erreur HTTP : {e}")
                raise
                
        except discord.LoginFailure:
            logger.error("❌ Token invalide ! Vérifiez votre DISCORD_BOT_TOKEN dans .env")
            sys.exit(1)
            
        except Exception as e:
            logger.error(f"❌ Erreur inattendue : {e}")
            if retry_count < max_retries - 1:
                wait_time = min(2 ** retry_count * 10, 300)  # Backoff exponentiel max 5min
                logger.info(f"🔄 Nouvelle tentative dans {wait_time}s...")
                await asyncio.sleep(wait_time)
                retry_count += 1
            else:
                logger.error("❌ Nombre maximum de tentatives atteint. Arrêt du bot.")
                raise
    
    if retry_count >= max_retries:
        logger.error("❌ Impossible de se connecter après plusieurs tentatives.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Arrêt du bot par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur fatale : {e}")
        sys.exit(1)
