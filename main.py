import asyncio
import getToken
import discord
from discord.ext import commands
import random
import loguru
from backend import Database
from constantes import CONSTANTS

# Create a Discord client instance and set the command prefix
intents = discord.Intents.all()
client = discord.Client(intents=intents)
logger = loguru.logger
database = Database('moshi.db')

bot = commands.Bot(command_prefix='.', intents=intents)

# Dictionnaire pour suivre les verrous par utilisateur
user_locks = {}

async def execute_command(command, message, userFromDb):
    if userFromDb[0] in user_locks:
        await message.channel.send("Vous avez déjà une commande en cours d'exécution.")
        return

    # Créer un verrou pour l'utilisateur
    user_locks[userFromDb[0]] = asyncio.Lock()
    try:
        # Attendre l'acquisition du verrou
        async with user_locks[userFromDb[0]]:
            await command(message, userFromDb)
    finally:
        # Assurez-vous de libérer le verrou après l'exécution de la commande
        del user_locks[userFromDb[0]]


@bot.event
async def on_ready():
    logger.info(f'{bot.user} est bien connecté!')
    database.create_tables()
    description_du_bot = ".help"
    await bot.change_presence(activity=discord.Game(name=description_du_bot))

@bot.event
async def on_message(message):
    contenu = message.content
    auteur = message.author
    if auteur == bot.user: # Check if the message is from the bot
        return
    if not(contenu.startswith('.')):
        return
    database.insert_user(auteur.id, auteur.name)
    userFromDb = database.getUser(auteur.id)
    if not userFromDb:
        logger.error(f"Erreur lors de la récupération de l'utilisateur {message.author.name} ({message.author.id}).")
        return
    contenu = contenu[1:].lower()
    for cmd, func in commands.items():
        if contenu.startswith(cmd):
            await execute_command(func, message, userFromDb)
            break


@bot.command()
async def new(message, userFromDb):
    # Parse the message to get the sujet
    sujet = message.content.split(' ')[1]
    logger.info(f"Commande !new appelée par {message.author.name} ({message.author.id}).")
    # Check if the sujet already exists
    topic = database.get_topic(sujet)
    if topic:
        await message.channel.send(f"Le sujet '{sujet}' existe déjà.")
        return
    a = await ajouter_sujet(message, userFromDb, sujet)
    

async def ajouter_sujet(message, userFromDb, sujet):
    # Envoie un embed de validation pour être sur que l'utilisateur veut ajouter le sujet
    embed = discord.Embed(
        title="Ajouter un sujet",
        description=f"Voulez-vous vraiment ajouter le sujet `{sujet}` ?",
        color=discord.Color.blurple()
    )
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)
    embed.set_footer(text="✅ : confirmer ❌ : annuler.")
    sent_message = await message.channel.send(embed=embed)
    await sent_message.add_reaction("✅")
    await sent_message.add_reaction("❌")
    def check(reaction, user):
        return user == message.author and str(reaction.emoji) in ["✅", "❌"]
    try:
        reaction, _ = await bot.wait_for("reaction_add", timeout=35, check=check)
        if str(reaction.emoji) == "✅":
            database.insert_topic(sujet)
            await message.channel.send(f"Le sujet '{sujet}' a été ajouté avec succès.")
            return database.get_topic(sujet)
        else:
            await message.channel.send("Opération annulée.")
            return False
    except asyncio.TimeoutError:
        await message.channel.send("La validation a expiré. Opération annulée.")
        return False
    
@bot.command()
async def info_sujet(message, userFromDb):
    pass

@bot.command()
async def list_command(message, userFromDb):
    logger.info(f"Commande !list_command appelée par {message.author.name} ({message.author.id}).")

    commands = list(CONSTANTS['DESCRIPTION_COMMANDES'].items())
    num_commands = len(commands)
    num_pages = (num_commands - 1) // 5 + 1  # Calcul du nombre total de pages
    
    current_page = 0  # Page actuelle, commençant à zéro

    # Fonction pour envoyer ou éditer la page actuelle
    async def send_or_edit_page(sent_message=None):
        start_index = current_page * 5
        end_index = min((current_page + 1) * 5, num_commands)
        
        embed = discord.Embed(
            title=f"Liste des commandes disponibles {current_page + 1}/{num_pages} :",
            description="",
            color=discord.Color.blurple()
        )
        for key, value in commands[start_index:end_index]:
            embed.add_field(name=key, value=value, inline=False)
        embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)

        if sent_message:  # S'il existe un message à éditer
            await sent_message.edit(embed=embed)
        else:  # Sinon, envoyer un nouveau message
            sent_message = await message.channel.send(embed=embed)
        return sent_message
    
    # Envoyer la première page
    sent_message = await send_or_edit_page()
    
    # Ajouter des réactions si nécessaire
    if num_pages > 1:
        await sent_message.add_reaction("⬅️")  # Réaction pour aller à la page précédente
        await sent_message.add_reaction("➡️")  # Réaction pour aller à la page suivante

    # Fonction pour gérer les réactions
    def check(reaction, user):
        return user == message.author and str(reaction.emoji) in ["⬅️", "➡️"]

    while True:
        try:
            reaction, _ = await bot.wait_for("reaction_add", timeout=5, check=check)
            
            # Gérer la réaction pour passer à la page précédente
            if str(reaction.emoji) == "⬅️":
                if current_page > 0:
                    current_page -= 1
                    sent_message = await send_or_edit_page(sent_message)

            # Gérer la réaction pour passer à la page suivante
            elif str(reaction.emoji) == "➡️":
                if current_page < num_pages - 1:
                    current_page += 1
                    sent_message = await send_or_edit_page(sent_message)

        except asyncio.TimeoutError:
            break  # Arrêter la pagination en cas de timeout

commands = {
    "h" : list_command, # Commande d'aide
    "ne" : new, # Commande pour ajouter un sujet
    "i" : info_sujet, # Commande pour voir un sujet
}

# Run the bot with the token
bot.run(getToken.getToken())
