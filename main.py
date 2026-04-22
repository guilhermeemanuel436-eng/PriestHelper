import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
import os
import re
import aiohttp
import datetime
from datetime import time
from dotenv import load_dotenv
load_dotenv()

# ===== INTENTS =====
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guild_messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== EVENTO =====
@bot.event
async def on_ready():
    await bot.tree.sync()

    atividade = discord.CustomActivity(
        name="/info | 📄"
    )

    print(f"Bot ligado! 💭🗨💬")

    await bot.change_presence(
        status=discord.Status.online,
        activity=atividade
    )

    if not enviar_liturgia_automatica.is_running():
        enviar_liturgia_automatica.start()
    
# ===== COR DA LITURGIA =====
def cor_embed(cor_liturgica: str) -> int:
    cores = {
        "Verde": 0x2ecc71,
        "Roxo": 0x8e44ad,
        "Vermelho": 0xe74c3c,
        "Branco": 0xecf0f1,
        "Rosa": 0xfd79a8,
        "Preto": 0x2d3436
    }
    return cores.get(cor_liturgica, 0x3498db)

# ===== DIVIDIR TEXTO GRANDE EM PARTES =====
def dividir_texto(texto: str, tamanho: int = 1024):
    return [texto[i:i+tamanho] for i in range(0, len(texto), tamanho)]

# ===== ADICIONAR LEITURAS AO EMBED (ROBUSTO) =====
def adicionar_leituras(embed, titulo, lista_leituras, emoji):
    for leitura in lista_leituras:
        partes = dividir_texto(leitura["texto"])

        # Garante que sempre exista pelo menos uma parte
        if not partes:
            partes = ["(Texto indisponível)"]

        # Primeiro campo COM título
        embed.add_field(
            name=f"{emoji} {titulo} ({leitura['referencia']})",
            value=partes[0],
            inline=False
        )

        # Campos seguintes SEM repetir título
        for parte in partes[1:]:
            embed.add_field(
                name="\u200b",
                value=parte,
                inline=False
            )

# ===== SLASH COMMAND =====
@bot.tree.command(name="liturgia", description="Mostra a liturgia completa do dia")
@app_commands.describe(data="Data no formato DD-MM-YYYY (opcional)")
async def liturgia(
    interaction: discord.Interaction,
    data: str | None = None
):
    # ===== VALIDAR DATA =====
    if data:
        if not re.fullmatch(r"\d{2}-\d{2}-\d{4}", data):
            await interaction.response.send_message(
                "⚠️ Formato inválido.\nUse **DD-MM-YYYY** (ex: 03-01-2026).",
                ephemeral=True
            )
            return
        url = f"https://liturgia.up.railway.app/v2/{data}"
    else:
        url = "https://liturgia.up.railway.app/v2/"

    # ===== CHAMADA DA API =====
    try:
        resposta = requests.get(url, timeout=10)
        resposta.raise_for_status()
        dados = resposta.json()

    except requests.RequestException:
        await interaction.response.send_message(
            "*Não consegui acessar a liturgia agora ou a data errada pode estar errada.*",
            ephemeral=True
        )
        return

    # ===== DADOS PRINCIPAIS =====
    liturgia_nome = dados["liturgia"]
    cor = dados["cor"]
    leituras = dados["leituras"]
    data = dados.get("data", "Data não informada")

    # ===== EMBED =====
    embed = discord.Embed(
        title=f"📅 Liturgia de {data}",
        description=f"📖 **{liturgia_nome}**\n🎨 Cor litúrgica: **{cor}**",
        color=cor_embed(cor)
    )

    # ===== ORDEM LITÚRGICA REAL =====
    adicionar_leituras(
        embed,
        "Primeira Leitura",
        leituras.get("primeiraLeitura", []),
        "📕"
    )

    adicionar_leituras(
        embed,
        "Salmo",
        leituras.get("salmo", []),
        "🎵"
    )

    adicionar_leituras(
        embed,
        "Segunda Leitura",
        leituras.get("segundaLeitura", []),
        "📘"
    )

    adicionar_leituras(
        embed,
        "Evangelho",
        leituras.get("evangelho", []),
        "✝️"
    )

    embed.set_footer(text="Fonte: liturgia.up.railway.app")

    await interaction.response.send_message(embed=embed)

@tasks.loop(time=time(18, 0))
async def enviar_liturgia_automatica():
    canal = bot.get_channel(1448836352761135268)

    if not canal:
        return

    try:
        resposta = requests.get("https://liturgia.up.railway.app/v2/", timeout=10)
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.RequestException:
        await canal.send("⚠️ Não consegui entregar a liturgia diária hoje.")
        return

    liturgia_nome = dados["liturgia"]
    cor = dados["cor"]
    leituras = dados["leituras"]
    data_api = dados.get("data", "Data não informada")

    embed = discord.Embed(
        title=f"📅 Liturgia Diária",
        description=f"📖 **{liturgia_nome}**\n🎨 Cor litúrgica: **{cor}**",
        color=cor_embed(cor)
    )

    adicionar_leituras(embed, "Primeira Leitura", leituras.get("primeiraLeitura", []), "📕")
    adicionar_leituras(embed, "Salmo", leituras.get("salmo", []), "🎵")
    adicionar_leituras(embed, "Segunda Leitura", leituras.get("segundaLeitura", []), "📘")
    adicionar_leituras(embed, "Evangelho", leituras.get("evangelho", []), "✝️")

    embed.set_footer(text="Fonte: liturgia.up.railway.app")

    await canal.send(embed=embed)

DEBATE_CHANNEL_ID = 1471648502567145627 # canal do automod
LOG_CHANNEL_ID = 1441541810454528064  # canal de advertências
MOD_ROLE_ID = 1328141161101267006 # id do moderador (permissão total)
ADMIN_ROLE_ID = 1468779653647962296 #id do mod que nn pode banir outros menbros

@bot.tree.command(name="capitulo", description="Mostra um capítulo inteiro da Bíblia")
@app_commands.describe(
    livro="Nome do livro (ex: João, Eclesiástico, Provérbios, Apocalipse, Jeremias e etc...)",
    capitulo="Número do capítulo"
)
async def capitulo(
    interaction: discord.Interaction,
    livro: str,
    capitulo: int
):
    await interaction.response.defer()

    url = f"https://bible-api.com/{livro}+{capitulo}?translation=almeida"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resposta:
            if resposta.status == 200:
                dados = await resposta.json()
            else:
                dados = None

    if not dados or "text" not in dados:
        await interaction.followup.send("*Não encontrei esse capítulo.*")
        return

    texto = dados["text"]
    partes = dividir_texto(texto, 1024)

    embed = discord.Embed(
        title=f"📖 {livro} {capitulo}",
        color=discord.Color.gold()
    )

    for i, parte in enumerate(partes):
        embed.add_field(
            name=f"Trecho: {i+1}",
            value=parte,
            inline=False
        )

    embed.set_footer(text=f"Bíblia - {livro} - Tradução Almeida")

    await interaction.followup.send(embed=embed)

PALAVRAS_PROIBIDAS = [
    r"\bfdp\b",
    r"\bretardado\b",
    r"\bretardada\b",
    r"\bimbecil\b",
    r"\bburro\b",
    r"\bburra\b",
    r"\bidio?ta\b",
    r"\banimal\b",
    r"\botario\b",
    r"\botária\b",
    r"filho da puta",
    r"filha da puta",
    r"desgraçad[oa]",
    r"arrombado",
    r"arrombada",
    r"corno",
    r"corna",
    r"porra",
    r"vai tomar no cu",
    r"vai se foder",
    r"\bvsf\b",
    r"caralho",
    r"\bcrlh\b",
    r"\btmnc\b",
    r"\bvtmnc\b",
    r"\bvsfd\b",
    r"foda[- ]?se",
    r"\bfds\b",
    r"cacete",
    r"puta que pariu",
    r"vai tomar no rabo",
    r"\bpqp\b",
    r"\bcu\b",
    r"brioco",
    r"piroca",
    r"pirocudo",
    r"buceta",
    r"bucetinha",
    r"bucetão",
    r"chibiu",
    r"xebiu",
    r"xibiu",
    r"pau no cu",
    r"pica",
    r"rola",
    r"pinto",
    r"pênis",
    r"penis",
    r"goza",
    r"gozei",
    r"gozada",
    r"fuder",
    r"fudi",
    r"fudeu",
    r"fudendo",
    r"fudida",
    r"fudido",
    r"gostoso",
    r"gostosa",
    r"xvideos?",
    r"xhamster",
    r"pornhub",
    r"redtube",
    r"youporn",
    r"xnxx",
    r"nigger",
    r"nigga",
    r"preto de merda",
    r"negro de merda",
    r"macaco de merda",
    r"filho da puta preto",
    r"filho da puta negro",
    r"filho da puta macaco",
    r"\bcabaço\b",
    r"\bcuz[aã]o\b",
    r"\bmerda\b",
    r"\bmerdinha\b",
    r"\bputinha\b",
    r"\bvagabundo\b",
    r"\bvagabunda\b",
    r"\bvadia\b",
    r"\brapariga\b",
    r"\bcorno manso\b",
    r"\bcorno do caralho\b",
    r"\bmaconheiro\b",
    r"puta",
]

@bot.event
async def on_message(message: discord.Message):

    log_channel = message.guild.get_channel(LOG_CHANNEL_ID)
    mod_role = message.guild.get_role(MOD_ROLE_ID)
    admin_role = message.guild.get_role(ADMIN_ROLE_ID)

    if message.author.bot:
        return

    if not message.guild:
        return

    # Verifica se está dentro de uma thread
    if not isinstance(message.channel, discord.Thread):
        return

    # Verifica se a thread pertence ao fórum desejado
    if message.channel.parent_id != DEBATE_CHANNEL_ID:
        return

    conteudo = message.content.lower()

    for padrao in PALAVRAS_PROIBIDAS:
        if re.search(padrao, conteudo):
            await message.delete()

            aviso = await message.channel.send(
                f"**{message.author.mention}, Cuidado com as palavras!**"
            )
            await aviso.delete(delay=60)

            embed = discord.Embed(
                title="**Advertência Automática**",
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(
                name="**Usuário**",
                value=f"{message.author} ({message.author.id})",
                inline=False
            )
            embed.add_field(
                name="**Canal**",
                value=message.channel.mention,
                inline=False
            )
            embed.add_field(
                name="**Palavra / Frase**",
                value=f"`{padrao}`",
                inline=False
            )
            embed.add_field(
                name="**Mensagem original**",
                value=message.content[:1000],
                inline=False
            )
            mencoes = []

            if mod_role:
                mencoes.append(mod_role.mention)

            if admin_role:
                mencoes.append(admin_role.mention)

            await log_channel.send(
                content=" ".join(mencoes) if mencoes else None,
                embed=embed
            )
            break

    await bot.process_commands(message)

@bot.tree.command(name="info", description="Informações sobre o bot")
async def info(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"⛪  Informações sobre {bot.user.name}",
        description="Foi desenvolvido com o intuito de ajudar na gestão de liturgias e moderar discussões em servidores além de outras funções extras.",
        color=discord.Color.yellow()
    )
    embed.add_field(
        name="📘  Liturgia",
        value="O bot tem acesso a liturgia via api, use o comando `/liturgia` para obter a liturgia completa do dia ou de uma data específica, além disso, o bot manda a liturgia diária automaticamente as 3:00h",
        inline=False
    )
    embed.add_field(
        name="🕵️‍♂️  Automod",
        value="O bot monitora mensagens em threads do canal de debates e remove mensagens com palavras proibidas, enviando um aviso ao usuário e registrando a infração no canal de logs.",
        inline=False
    )

    embed.add_field(
        name="📗  Bíblia",
        value="Entrega capítulos da Bíblia por meio da api organizados em trechos, use o comando `/biblia` para ver um capítulo inteiro do livro bíblico selecionado.",
        inline=False
    )
    embed.add_field(
        name="🤍 Divina Misericórdia",
        value="Mini manual de como se rezar o Terço da Divina Miserícordia",
        inline=False
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="terço-da-misericórdia", description="comando que guia o terço da divina misericórdia")
async def terço_misericordia(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Terço da Divina Misericórdia ✝👑",
        description=(
            "*'O Terço é o flagelo do diabo'* - Papa Adriano VI\n\n"
            "**Palavras de Jesus a Santa Faustina:**\n"
            "As almas que rezarem este Terço serão envolvidas pela Minha misericórdia durante a sua vida "
            "e de modo particular na hora da morte. Quando recitam esse Terço junto a um agonizante, "
            "aplaca-se a ira de Deus, a misericórdia insondável envolve a alma."
        ),
        color=discord.Color.red()
    )

    embed.add_field(
        name="📿 Pai Nosso",
        value=(
            "Pai Nosso que estais nos Céus,\n"
            "santificado seja o vosso Nome,\n"
            "venha a nós o vosso Reino,\n"
            "seja feita a vossa vontade\n"
            "assim na terra como no Céu.\n"
            "O pão nosso de cada dia nos dai hoje,\n"
            "perdoai as nossas ofensas\n"
            "assim como nós perdoamos a quem nos tem ofendido,\n"
            "e não nos deixeis cair em tentação,\n"
            "mas livrai-nos do mal. Amém."
        ),
        inline=False
    )

    embed.add_field(
        name="🙏 Ave Maria",
        value=(
            "Ave Maria, cheia de graça,\n"
            "o Senhor é convosco,\n"
            "bendita sois vós entre as mulheres,\n"
            "e bendito é o fruto do vosso ventre, Jesus.\n"
            "Santa Maria, Mãe de Deus,\n"
            "rogai por nós pecadores,\n"
            "agora e na hora de nossa morte. Amém."
        ),
        inline=False
    )

    embed.add_field(
        name="✝️ Creio em Deus Pai",
        value=(
            "Creio em Deus Pai todo-poderoso,\n"
            "Criador do céu e da terra;\n"
            "e em Jesus Cristo, seu único Filho, nosso Senhor,\n"
            "que foi concebido pelo poder do Espírito Santo,\n"
            "nasceu da Virgem Maria,\n"
            "padeceu sob Pôncio Pilatos,\n"
            "foi crucificado, morto e sepultado,\n"
            "desceu à mansão dos mortos,\n"
            "ressuscitou ao terceiro dia,\n"
            "subiu aos céus,\n"
            "está sentado à direita de Deus Pai todo-poderoso,\n"
            "donde há de vir a julgar os vivos e os mortos.\n"
            "Creio no Espírito Santo,\n"
            "na Santa Igreja Católica,\n"
            "na comunhão dos santos,\n"
            "na remissão dos pecados,\n"
            "na ressurreição da carne,\n"
            "na vida eterna. Amém."
        ),
        inline=False
    )

    embed.add_field(
        name="📿 Nas contas do Pai Nosso — O que rezar?",
        value=(
            "Em cada conta grande (Pai Nosso), reze:\n"
            "**'Pai Eterno, ofereço-vos o Corpo e o Sangue, a Alma e a Divindade "
            "de vosso Filho muito amado, Nosso Senhor Jesus Cristo, "
            "em expiação dos nossos pecados e dos do mundo inteiro.'**\n\n"
            "Em cada conta pequena (Ave Maria), reze **10x**:\n"
            "**'Pela Sua dolorosa Paixão, tende misericórdia de nós e do mundo inteiro.'**\n\n"
            "Para encerrar cada dezena e ao fim do Terço, reze **3x**:\n"
            "**'Santo Deus, Santo Forte, Santo Imortal, tende piedade de nós e do mundo inteiro.'**"
        ),
        inline=False
    )

    embed.set_footer(text=(
        "No início reza-se o Pai Nosso, a Ave Maria e o Creio em Deus Pai. "
        "Nas contas do Pai Nosso: ofereça o Corpo, Sangue, Alma e Divindade de Jesus ao Pai Eterno. "
        "Nas contas da Ave Maria (10x): 'Pela Sua dolorosa Paixão, tende misericórdia de nós e do mundo inteiro.'"
    ))

    embed.set_image(url="https://i.pinimg.com/originals/07/d4/29/07d429f86c2abd819f4fbeef56826537.jpg")

    embed.set_thumbnail(url="https://th.bing.com/th/id/R.128794d98f314b2f632b41e4a0a2bf06?rik=QHFksVPw8mN3%2fQ&pid=ImgRaw&r=0")

    await interaction.response.send_message(embed=embed)

bot.run(os.getenv("DISCORD_TOKEN"))