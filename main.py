import asyncio
import datetime
import io
import getToken
import discord
from discord.ext import commands
import random
import loguru
from backend import Database
from constantes import CONSTANTS
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

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
    sujet = (" ".join(message.content.split(' ')[1:])).lower()
    print(sujet)
    if sujet == "":
        await message.channel.send(embed=embed_erreur("Arguments invalides", "La commande doit être de la forme `.new <sujet>`."))
        return
    logger.info(f"Commande !new appelée par {message.author.name} ({message.author.id}).")
    # Check if the sujet already exists
    topic = database.get_topic(sujet)
    if topic:
        await message.channel.send(embed=embed_erreur("Sujet déjà existant", f"Le sujet '{sujet}' existe déjà."))
        return
    a = await ajouter_sujet(message, userFromDb, sujet)
    

async def ajouter_sujet(message, userFromDb, sujet):
    # Envoie un embed de validation pour être sur que l'utilisateur veut ajouter le sujet
    embed = discord.Embed(
        title="Ajouter un sujet",
        description=f"Voulez-vous vraiment ajouter le sujet `{sujet.capitalize()}` ?",
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
            await message.channel.send(embed=embed_succes("Sujet ajouté", f"Le sujet '{sujet}' a été ajouté."))
            return database.get_topic(sujet)
        else:
            await message.channel.send(embed=embed_erreur("Opération annulée", "Le sujet n'a pas été ajouté."))
            return False
    except asyncio.TimeoutError:
        await message.channel.send(embed=embed_erreur("Validation expirée", "Le sujet n'a pas été ajouté."))
        return False
    
@bot.command()
async def info_sujet(message, userFromDb):
    # Parse the message to get the sujet , the message is in the form ".info <sujet>"
    # Montre tous les sujets qui ressemblent au sujet
    sujet = (" ".join(message.content.split(' ')[1:])).lower()
    if sujet == "":
        await message.channel.send(embed=embed_erreur("Arguments invalides", "La commande doit être de la forme `.info <sujet>`"))
        return
    logger.info(f"Commande !info appelée par {message.author.name} ({message.author.id}).")
    # Check if the sujet already exists
    topics = database.get_topics_levenshtein(sujet)
    if not topics:
        await message.channel.send(embed=embed_erreur("Sujet inconnu", f"Le sujet '{sujet}' n'existe pas.","Vous pouvez ajouter un sujet avec la commande `.new <sujet>`."))
        return
    embed = discord.Embed(
        title="Sujets similaires",
        description="",
        color=discord.Color.blurple()
    )
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)
    for topic in topics:
        embed.add_field(name="- " + topic[1].capitalize(), value=f"", inline=False)
    await message.channel.send(embed=embed)
    

@bot.command()
async def add_activity(message, userFromDb):
    # Le message est sous la forme ".add <sujet>, duree"
    # La duree est en minutes
    contenu = message.content.split(',')
    if len(contenu) != 2:
        await message.channel.send(embed=embed_erreur("Arguments invalides", "La commande doit être de la forme `.add <sujet>, duree`."))
        return
    sujet = contenu[0].split(' ')[1]
    duree = contenu[1].strip()
    if not duree.isdigit():
        await message.channel.send(embed=embed_erreur("Durée invalide", "La durée doit être un nombre entier."))
        return
    if int(duree) <= 0:
        await message.channel.send(embed=embed_erreur("Durée invalide", "La durée doit être un nombre entier positif."))
        return
    if int(duree) > 1440:
        await message.channel.send(embed=embed_erreur("Durée invalide", "La durée ne peut pas dépasser 1440 minutes (24 heures)."))
        return
    if int(duree) % 5 != 0:
        await message.channel.send(embed=embed_erreur("Durée invalide", "La durée doit être un multiple de 5 minutes."))
        return
    logger.info(f"Commande !add_activity appelée par {message.author.name} ({message.author.id}).")
    # Check if the sujet already exists
    topic = database.get_topic_levenshtein(sujet)
    if not topic:
        await message.channel.send(embed=embed_erreur("Sujet inconnu", f"Le sujet '{sujet}' n'existe pas.","Vous pouvez ajouter un sujet avec la commande `.new <sujet>`."))
        return
    a = await ajouter_activite(message, userFromDb, topic, duree)
    
@bot.command()
async def ajouter_activite(message, userFromDb, topic, duree):
    # Envoie un embed de validation pour être sur que l'utilisateur veut ajouter l'activité
    transition = "de l'" if topic[1][0] in "aeiou" else "du"
    transition = "des" if topic[1][-1] == "s"  else transition
    embed = discord.Embed(
        title="Ajouter une activité",
        description=f"Avez-vous passé `{duree} minutes` à effectuer {transition} `{topic[1]}` ? ",
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
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            r = database.insert_activity(date,duree,topic[0], userFromDb[1])
            await message.channel.send(embed=embed_succes("Activité ajoutée", f"Vous avez passé {duree} minutes à effectuer {transition} '{topic[1]}'."))
            return r
        else:
            await message.channel.send(embed=embed_erreur("Opération annulée", "L'activité n'a pas été ajoutée."))
            return False
    except asyncio.TimeoutError:
        await message.channel.send(embed=embed_erreur("Validation expirée", "L'activité n'a pas été ajoutée."))
        return False

@bot.command()
async def daily(message, userFromDb):
    date_debut = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
    await graphe_activites(message, userFromDb, date_debut, "de la journée")

@bot.command()
async def weekly(message, userFromDb):
    date_debut = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    await graphe_activites(message, userFromDb, date_debut, "de la semaine dernière")

@bot.command()
async def monthly(message, userFromDb):
    date_debut = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    await graphe_activites(message, userFromDb, date_debut, "du mois dernier")
    
@bot.command()
async def last_days(message, userFromDb):
    # Parse the message to get the number of days
    nombre = message.content.split(' ')[1]
    try:
        nombre = int(nombre)
    except ValueError:
        await message.channel.send(embed=embed_erreur("Nombre invalide", "Le nombre de jours doit être un entier."))
        return
    if nombre <= 0:
        await message.channel.send(embed=embed_erreur("Nombre invalide", "Le nombre de jours doit être un entier positif."))
        return
    date_debut = (datetime.datetime.now() - datetime.timedelta(days=nombre)).strftime("%Y-%m-%d %H:%M:%S")
    await graphe_activites(message, userFromDb, date_debut, f"des {nombre} derniers jours")

@bot.command()
async def graphe_activites(message, userFromDb, date_debut, libelle=""):
    # Retourne un graphe des activités de l'utilisateur à partir de la date de début
    activites = database.get_activities(userFromDb[1], date_debut)
    print(activites)
    if not activites:
        await message.channel.send(embed=embed_erreur("Aucune activité", "Aucune activité trouvée pour cet utilisateur à partir de la date spécifiée."))
        return
    duree_par_activite = {}
    for activite in activites:
        if activite[6] not in duree_par_activite:
            print(activite[3], " n'existe pas dans le dictionnaire")
            duree_par_activite[activite[6]] = 0
        print(duree_par_activite, activite[6], activite[2])
        duree_par_activite[activite[6]] += activite[2]
        print(duree_par_activite, activite[6], activite[2])
    # Créer un graphique à barres pour les activités
    print(duree_par_activite)
    if duree_par_activite == {}:
        await message.channel.send(embed=embed_erreur("Aucune activité", "Aucune activité trouvée pour cet utilisateur à partir de la date spécifiée."))
        return
    plt.figure(figsize=(10, 6))
    # On capitalize tous les nom des sujets
    duree_par_activite = {key.capitalize(): value for key, value in duree_par_activite.items()}
    bars = plt.barh(list(duree_par_activite.keys()), list(duree_par_activite.values()), color='#452fd6')
    plt.xlabel("Durée (minutes)", labelpad=10, fontsize=12, fontweight='bold', color='#333333')
    plt.ylabel("Sujet", labelpad=10, fontsize=12, fontweight='bold', color='#333333')
    plt.title("Activités " + libelle)
    plt.xticks(rotation=15)
    plt.tight_layout()
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 1 if width < 35 else width - 15, bar.get_y() + bar.get_height()/2, 
                f'{bar.get_width()} min', 
                va='center', ha='left', 
                fontsize=10, fontweight='bold', color='black')
        # Changement de la couleur des barres en fonction de la durée
        color = get_color(bar.get_width())
        bar.set_color(color)
        bar.set_edgecolor('#444444')

        
        
    
    # Sauvegarder le graphique dans un objet BytesIO
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()  # Fermer la figure pour libérer la mémoire

    # Envoyer le fichier image sur Discord
    file = discord.File(buf, filename='graph.png')
    embed = discord.Embed(
        title="Activités " + libelle,
        description="",
        color=discord.Color.blurple()
    )
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)
    embed.set_image(url="attachment://graph.png")
    await message.channel.send(file=file, embed=embed)


def get_color(value, min_value=0, max_value=70):
    """
    Returns a color based on the value, interpolating between light red, orange, and light green.

    Parameters:
    value (float): The value to map to a color.
    min_value (float): The minimum value for the color scale.
    max_value (float): The maximum value for the color scale.

    Returns:
    str: The color in hexadecimal format.
    """
    norm = mcolors.Normalize(vmin=min_value, vmax=max_value)
    colors = ['#B52727', '#A6C67E', '#1CC747']  # Light red, orange, light green
    cmap = mcolors.LinearSegmentedColormap.from_list("", colors)
    return mcolors.to_hex(cmap(norm(value)))


@bot.command()
async def historique(message, userFromDb):
    # Parse the subject, the message is in the form ".historique <sujet>"
    # Get the activities of the user for the subject
    # Show a graph of the activities by date for the subject
    sujet = message.content.split(' ')
    if len(sujet) != 2:
        await message.channel.send(embed=embed_erreur("Arguments invalides", "La commande doit être de la forme `.historique <sujet>`"))
        return
    sujet = sujet[1]
    topic = database.get_topic_levenshtein(sujet)
    if not topic:
        await message.channel.send(embed=embed_erreur("Sujet inconnu", f"Le sujet '{sujet}' n'existe pas.","Vous pouvez ajouter un sujet avec la commande `.new <sujet>`."))
        return
    activites = database.get_activities_by_topic(userFromDb[1], topic[0])
    print(activites)
    if not activites:
        await message.channel.send(embed=embed_erreur("Aucune activité", f"Aucune activité trouvée pour le sujet '{topic[1]}'."))
        return
    duree_par_date = {}
    for activite in activites:
        date = activite[1].split(' ')[0]
        if date not in duree_par_date:
            duree_par_date[date] = 0
        duree_par_date[date] += activite[2]
    # Créer un graphique à barres pour les activités
    plt.figure(figsize=(10, 6))
    plt.barh(list(duree_par_date.keys()), list(duree_par_date.values()), color='#452fd6',edgecolor='black')
    plt.xlabel("Durée (minutes)", labelpad=10, fontsize=12, fontweight='bold', color='#333333')
    plt.ylabel("Date", labelpad=10, fontsize=12, fontweight='bold', color='#333333')
    plt.title(f"Activités {topic[1]}")
    plt.xticks(rotation=15)
    plt.tight_layout()
    
    # Sauvegarder le graphique dans un objet BytesIO
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()  # Fermer la figure pour libérer la mémoire
    
    # Envoyer le fichier image sur Discord
    file = discord.File(buf, filename='graph.png')
    embed = discord.Embed(
        title=f"Activités {topic[1]}",
        description="",
        color=discord.Color.blurple()
    )
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)
    embed.set_image(url="attachment://graph.png")
    await message.channel.send(file=file, embed=embed)
    

def embed_succes(titre, description):
    return embed(titre, description, discord.Color.green())

def embed_erreur(titre, description,footer=None):
    return embed(titre, description, discord.Color.red(), footer=footer if footer else None)

def embed(titre="", description="", couleur=discord.Color.blurple(), author=None, footer=None):
    embed = discord.Embed(
        title=titre,
        description=description,
        color=couleur
    )
    if footer is not None:
        embed.set_footer(text=footer)
    if author is None:
        embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url)
    else:
        embed.set_author(name=author.name, icon_url=author.avatar.url)
    return embed
    

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
    "hel" : list_command, # Commande d'aide
    "ne" : new, # Commande pour ajouter un sujet
    "i" : info_sujet, # Commande pour voir un sujet
    "ad": add_activity, # Commande pour ajouter une activité
    "da": daily, # Commande pour voir les activités de la journée
    "we": weekly, # Commande pour voir les activités de la semaine
    "mo": monthly, # Commande pour voir les activités du mois
    "la": last_days, # Commande pour voir les activités des derniers jours
    "his": historique, # Commande pour voir l'historique d'un sujet
}

# Run the bot with the token
bot.run(getToken.getToken())
