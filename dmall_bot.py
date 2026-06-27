import asyncio
import json
import os
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix="+", intents=intents, help_command=None)

OWNER_ID = 1471476071290634305
DISCORD_API = "https://discord.com/api/v10"
SUPPORT_INVITE = "Nx3EFxg5eM"
SUPPORT_GUILD_ID: int | None = None
BLUE = 1
GREEN = 3
GRAY = 2
RED = 4
COMPONENTS_V2 = 32768
EPHEMERAL = 64
VIEWS_READY = False
DMALL_RUNNING = False
DMALL_STOP = False
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

config = {
    "tokens": [], "token_infos": [], "message": None, "embed": None,
    "button_label": None, "button_url": None, "ignored_ids": [],
    "status_filter": ["online", "idle", "dnd", "offline"],
    "selected_token_index": 0, "target_ids": [], "member_count": 0,
    "panel_message_id": None, "panel_channel_id": None, "panel_owner_id": None,
    "stats_total_sent": 0, "stats_total_failed": 0,
    "stats_total_sessions": 0, "stats_unique_users": [], "stats_panel_users": [],
    "premium_users": [],
    "saved_presence": None,
}

ACTIVITY_TYPES = {
    "joue": discord.ActivityType.playing, "regarde": discord.ActivityType.watching,
    "ecoute": discord.ActivityType.listening, "stream": discord.ActivityType.streaming,
}
ACTIVITY_TYPE_IDS = {"joue": 0, "regarde": 3, "ecoute": 2, "stream": 1}

PERSIST_KEYS = [
    "tokens", "token_infos", "message", "embed", "button_label", "button_url",
    "ignored_ids", "status_filter", "selected_token_index", "target_ids", "member_count",
    "panel_message_id", "panel_channel_id", "panel_owner_id",
    "stats_total_sent", "stats_total_failed", "stats_total_sessions", "stats_unique_users", "stats_panel_users",
    "premium_users", "saved_presence",
]

def save_config() -> None:
    data = {k: config[k] for k in PERSIST_KEYS}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_config() -> None:
    if not os.path.exists(CONFIG_FILE):
        return
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in PERSIST_KEYS:
            if k in data:
                config[k] = data[k]
    except Exception:
        pass

def text_component(content): return {"type": 10, "content": content}
def separator(): return {"type": 14, "divider": True, "spacing": 1}
def button(label, style, custom_id): return {"type": 2, "label": label, "style": style, "custom_id": custom_id}
def link_button(label, url): return {"type": 2, "label": label, "style": 5, "url": url}
def action_row(*items): return {"type": 1, "components": list(items)}
def short_text(value, empty, limit=90):
    if not value: return empty
    return value[:limit] + "..." if len(value) > limit else value

def get_member_from_id(user_id: int):
    for guild in bot.guilds:
        m = guild.get_member(user_id)
        if m: return m
    return None

def set_target_ids(ids):
    filtered = [i for i in ids if i not in config["ignored_ids"]]
    config["target_ids"] = filtered
    config["member_count"] = len(filtered)
    save_config()

def build_token_text() -> str:
    if not config["tokens"]: return "Aucun token ajouté"
    lines = []
    for i, info in enumerate(config["token_infos"], 1):
        name = info.get("name", f"Bot {i}")
        bid = info.get("id")
        if bid:
            invite = f"https://discord.com/oauth2/authorize?client_id={bid}&scope=bot&permissions=8"
            lines.append(f"`{i}.` **{name}** • [Inviter]({invite})")
        else:
            lines.append(f"`{i}.` **{name}**")
    for i in range(len(config["token_infos"]) + 1, len(config["tokens"]) + 1):
        lines.append(f"`{i}.` **Bot inconnu**")
    return "\n".join(lines)

def build_panel_components() -> list:
    token_text = build_token_text()
    message_text = short_text(config["message"], "Aucun message texte défini")
    embed_text = "Embed configuré" if config["embed"] else "Aucun embed défini"
    return [
        text_component("## > **Support** : https://discord.gg/W3ZtAhJ2yy"),
        {
        "type": 17, "accent_color": 0x757A86,
        "components": [
            text_component("## `💎` 〃 Configuration du FluxBot\n**__Utilisez les boutons ci-dessous pour configurer votre Dmall.__**"),
            separator(),
            text_component(f"🤖 **Tokens** — {token_text}"),
            action_row(button("🤖 Ajouter Token", BLUE, "add_token_btn")),
            separator(),
            text_component(f"📝 **Message à envoyer**\n```{message_text}```\n✏️ **Embed**\n```{embed_text}```"),
            action_row(button("📝 Définir le message", GREEN, "open_message_config_btn")),
            separator(),
            text_component(f"👥 **User IDs — Total : {config['member_count']} ID**　　👥 **User IDs à Ignorer — Total : {len(config['ignored_ids'])} ID**"),
            action_row(button("⚙️ Options DM", GRAY, "dm_options_btn")),
            separator(),
            action_row(button("⭐ Définir le statut", BLUE, "set_status_btn"), button("🚀 Dmall", RED, "dmall_execute_btn")),
            separator(),
            text_component("-# FluxBot • Crée par **mazuu.bs**"),
        ],
    }]

def build_message_config_components() -> list:
    return [{"type": 17, "accent_color": 0x5865F2, "components": [
        text_component("## :pencil: 〃 Définir le Message à Envoyer\nChoisissez une méthode :"),
        separator(),
        text_component(":one: **Message texte simple**"),
        action_row(button("✏️ Saisir un message", BLUE, "simple_message_btn")),
        separator(),
        text_component(":two: **Embed personnalisé**"),
        action_row(button("📝 Embed JSON", BLUE, "embed_json_btn"), button("🎨 Embed Builder", GRAY, "embed_builder_btn")),
        separator(),
        text_component("**:bulb: Variables :**\n`{user}` → mention du membre\n`{user.id}` → id du membre\n`{timestamp}` → date/heure exact"),
        separator(),
        action_row(button("Aperçu", GRAY, "preview_message_btn"), button("Reset", RED, "reset_message_btn")),
    ]}]

def build_dm_options_components() -> list:
    return [{"type": 17, "accent_color": 0x5865F2, "components": [
        text_component("## ⚙️ 〃 Options de DM\n**__Choisissez une option pour configurer votre liste de cibles.__**"),
        separator(),
        text_component("**1️⃣ Ajouter des IDs**\n```Permet d'ajouter un ou plusieurs IDs manuellement.```"),
        action_row(button("1️⃣ Ajouter des IDs", BLUE, "dmopt_add_ids")),
        separator(),
        text_component("**2️⃣ Fetch des membres**\n```Récupère tous les membres d'un serveur via un de vos bots ajoutés.```"),
        action_row(button("2️⃣ Fetch des membres", BLUE, "dmopt_fetch_members")),
        separator(),
        text_component("**3️⃣ Fetch par rôles**\n```Récupère les membres ayant certains rôles (bot principal uniquement).```"),
        action_row(button("3️⃣ Fetch par rôles", GRAY, "dmopt_fetch_roles")),
        separator(),
        text_component("**4️⃣ Fetch Vocal**\n```Récupère les membres en vocal ou non (bot principal uniquement).```"),
        action_row(button("4️⃣ Fetch Vocal", GRAY, "dmopt_fetch_vocal")),
        separator(),
        text_component(f"**5️⃣ Autres**\n```👥 {config['member_count']} ID(s) chargé(s) • 🚫 {len(config['ignored_ids'])} ignoré(s)```"),
        action_row(button("5️⃣ Autres", GRAY, "dmopt_autres")),
        separator(),
        text_component("-# FluxBot • Crée par **mazuu.bs**"),
    ]}]

def bot_headers(token=None):
    return {"Authorization": f"Bot {token or os.environ.get('DISCORD_TOKEN', os.environ.get('TOKEN', ''))}", "Content-Type": "application/json"}

async def send_panel_v2(channel_id: int) -> dict:
    async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
        async with session.post(f"{DISCORD_API}/channels/{channel_id}/messages",
            json={"flags": COMPONENTS_V2, "components": build_panel_components()},
            headers=bot_headers()) as r:
            data = await r.json()
            if r.status >= 400: raise RuntimeError(f"Erreur {r.status}: {data}")
            return data

async def refresh_panel() -> None:
    if not config["panel_message_id"] or not config["panel_channel_id"]: return
    async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
        async with session.patch(
            f"{DISCORD_API}/channels/{config['panel_channel_id']}/messages/{config['panel_message_id']}",
            json={"flags": COMPONENTS_V2, "components": build_panel_components()},
            headers=bot_headers()
        ) as r:
            pass

async def get_token_bot_info(token: str):
    async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
        async with session.get(f"{DISCORD_API}/users/@me", headers=bot_headers(token)) as r:
            if r.status != 200: return None
            data = await r.json()
            uid = data.get("id")
            name = data.get("global_name") or data.get("username") or "Bot inconnu"
            disc = data.get("discriminator")
            if disc and disc != "0": name = f"{name}#{disc}"
            return {"id": uid, "name": name}

async def enable_privileged_intents(token: str) -> tuple[bool, str]:
    intent_flags = (1 << 12) | (1 << 14) | (1 << 18)
    headers_bot = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    user_token = os.environ.get("DISCORD_USER_TOKEN", "")
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.get(
                f"{DISCORD_API}/applications/@me",
                headers=headers_bot,
            ) as r:
                body = await r.json()
                if r.status != 200:
                    print(f"[INTENTS] GET error {r.status}: {body}")
                    return False, f"{r.status}: {body}"
                app_id = body.get("id")
                current_flags = body.get("flags", 0)
                print(f"[INTENTS] app_id={app_id} flags actuels={current_flags}")
            new_flags = current_flags | intent_flags
            if user_token:
                headers_user = {"Authorization": user_token, "Content-Type": "application/json"}
                async with session.patch(
                    f"{DISCORD_API}/applications/{app_id}",
                    json={"flags": new_flags},
                    headers=headers_user,
                ) as r2:
                    body2 = await r2.json()
                    flags_result = body2.get("flags")
                    print(f"[INTENTS] PATCH(user) → {r2.status} | flags après={flags_result}")
                    if r2.status == 200 and flags_result and (flags_result & intent_flags) == intent_flags:
                        print(f"[INTENTS] Succès !")
                        return True, ""
                    return False, f"{r2.status}: {body2}"
            else:
                print("[INTENTS] DISCORD_USER_TOKEN non défini")
                return False, "DISCORD_USER_TOKEN manquant"
    except Exception as e:
        print(f"[INTENTS] Exception : {e}")
        return False, str(e)

async def send_ephemeral_components(interaction, components):
    payload = {"type": 4, "data": {"flags": EPHEMERAL | COMPONENTS_V2, "components": components}}
    async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
        async with session.post(f"{DISCORD_API}/interactions/{interaction.id}/{interaction.token}/callback", json=payload) as r:
            if r.status >= 400:
                err = await r.text()
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ {err}", ephemeral=True)

def apply_variables(value, member):
    if value is None: return None
    return value.replace("{user}", member.mention).replace("{user.id}", str(member.id)).replace("{timestamp}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

def build_embed_for_member(member):
    if not config["embed"]: return None
    ed = json.loads(json.dumps(config["embed"]))
    for k in ("title", "description", "url"):
        if k in ed and isinstance(ed[k], str): ed[k] = apply_variables(ed[k], member)
    for f in ed.get("fields", []):
        if isinstance(f, dict):
            for k in ("name", "value"):
                if k in f and isinstance(f[k], str): f[k] = apply_variables(f[k], member)
    return ed

def build_dm_payload(member):
    p = {}
    c = apply_variables(config["message"], member)
    e = build_embed_for_member(member)
    if c: p["content"] = c
    if e: p["embeds"] = [e]
    if config["button_label"] and config["button_url"]:
        p["components"] = [action_row(link_button(config["button_label"], config["button_url"]))]
    return p

def apply_variables_by_id(value, user_id):
    """Applique les variables {user}, {user.id}, {timestamp} sans objet member."""
    if value is None: return None
    mention = f"<@{user_id}>"
    return (
        value
        .replace("{user}", mention)
        .replace("{user.id}", str(user_id))
        .replace("{timestamp}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    )

def build_embed_for_id(user_id):
    """Construit l'embed en remplaçant les variables via l'ID (quand le membre n'est pas en cache)."""
    if not config["embed"]: return None
    ed = json.loads(json.dumps(config["embed"]))
    for k in ("title", "description", "url"):
        if k in ed and isinstance(ed[k], str): ed[k] = apply_variables_by_id(ed[k], user_id)
    for f in ed.get("fields", []):
        if isinstance(f, dict):
            for k in ("name", "value"):
                if k in f and isinstance(f[k], str): f[k] = apply_variables_by_id(f[k], user_id)
    return ed

def build_dm_payload_for_id(user_id):
    m = get_member_from_id(user_id)
    if m: return build_dm_payload(m)
    # Membre pas en cache — on applique quand même les variables avec l'ID
    p = {}
    c = apply_variables_by_id(config["message"], user_id)
    e = build_embed_for_id(user_id)
    if c: p["content"] = c
    if e: p["embeds"] = [e]
    if config["button_label"] and config["button_url"]:
        p["components"] = [action_row(link_button(config["button_label"], config["button_url"]))]
    return p

# ─── Statut via Gateway pour les tokens ajoutés ──────────────────────────────

async def set_token_status_via_gateway(token: str, activity_type_id: int, activity_name: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DISCORD_API}/gateway", headers=bot_headers(token)) as r:
                if r.status != 200: return False
                gw_url = (await r.json()).get("url", "wss://gateway.discord.gg") + "/?v=10&encoding=json"
            async with session.ws_connect(gw_url) as ws:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=10)
                if msg.get("op") != 10: return False
                await ws.send_json({
                    "op": 2,
                    "d": {
                        "token": token,
                        "intents": 0,
                        "properties": {"os": "linux", "browser": "disco", "device": "disco"},
                        "presence": {
                            "activities": [{"name": activity_name, "type": activity_type_id}],
                            "status": "online", "since": None, "afk": False,
                        },
                    },
                })
                for _ in range(5):
                    msg = await asyncio.wait_for(ws.receive_json(), timeout=10)
                    if msg.get("op") == 0 and msg.get("t") == "READY": return True
                    if msg.get("op") == 9: return False
        return False
    except Exception:
        return False

# ─── Envoi DM optimisé avec session partagée + retry 429 ─────────────────────

async def send_dm_with_session(session: aiohttp.ClientSession, token: str, user_id: int, payload: dict) -> bool:
    headers = bot_headers(token)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Ouvre le canal DM
            async with session.post(
                f"{DISCORD_API}/users/@me/channels",
                json={"recipient_id": str(user_id)},
                headers=headers,
            ) as r:
                if r.status == 429:
                    data = await r.json()
                    await asyncio.sleep(data.get("retry_after", 1))
                    continue
                if r.status != 200:
                    return False
                channel_id = (await r.json()).get("id")
                if not channel_id:
                    return False

            # Envoie le message
            async with session.post(
                f"{DISCORD_API}/channels/{channel_id}/messages",
                json=payload,
                headers=headers,
            ) as r:
                if r.status == 429:
                    data = await r.json()
                    await asyncio.sleep(data.get("retry_after", 1))
                    continue
                return r.status in (200, 201)

        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5)
    return False

# Fonction de compatibilité pour les appels hors dmall (ex: TokenModal)
async def send_dm_via_token(token, user_id, payload) -> bool:
    async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
        return await send_dm_with_session(session, token, user_id, payload)

async def get_token_guilds(token: str):
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.get(f"{DISCORD_API}/users/@me/guilds?limit=200", headers=bot_headers(token)) as r:
                if r.status != 200: return []
                return await r.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return []

async def fetch_members_via_token(token: str, guild_id: int):
    ids = []
    after = "0"
    try:
        timeout = aiohttp.ClientTimeout(total=120, connect=5, sock_read=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while True:
                url = f"{DISCORD_API}/guilds/{guild_id}/members?limit=1000&after={after}"
                async with session.get(url, headers=bot_headers(token)) as r:
                    if r.status != 200: break
                    data = await r.json()
                    if not data: break
                    for m in data:
                        u = m.get("user", {})
                        if u.get("bot"): continue
                        uid = u.get("id")
                        if uid: ids.append(int(uid))
                    if len(data) < 1000: break
                    after = data[-1]["user"]["id"]
                await asyncio.sleep(0.3)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass
    return ids

# ─── Option 1 : Ajouter IDs ──────────────────────────────────────────────────

class AddIdsModal(discord.ui.Modal, title="1️⃣ Ajouter des IDs"):
    ids_input = discord.ui.TextInput(label="IDs à ajouter", placeholder="Un ID par ligne ou séparés par virgules", style=discord.TextStyle.paragraph, max_length=4000)
    async def on_submit(self, interaction):
        raw = self.ids_input.value.replace(",", "\n")
        new_ids, invalid = [], 0
        for p in raw.splitlines():
            p = p.strip()
            if not p: continue
            try: new_ids.append(int(p))
            except ValueError: invalid += 1
        added = 0
        for uid in new_ids:
            if uid not in config["target_ids"]:
                config["target_ids"].append(uid)
                added += 1
        config["member_count"] = len(config["target_ids"])
        save_config()
        msg = f"✅ **{added}** ID(s) ajouté(s) — Total : **{config['member_count']}** ID(s)"
        if invalid: msg += f"\n⚠️ {invalid} valeur(s) invalide(s) ignorée(s)"
        await interaction.response.send_message(msg, ephemeral=True)
        await refresh_panel()

# ─── Option 2 : Fetch membres via token sélectionné ──────────────────────────

class DmWizardGuildSelect(discord.ui.View):
    def __init__(self, token_index, guilds_data):
        super().__init__(timeout=180)
        self.token_index = token_index
        self.guilds_data = guilds_data
        opts = [discord.SelectOption(label=g.get("name", "?")[:100], value=str(g["id"])) for g in guilds_data[:25]]
        if not opts: opts = [discord.SelectOption(label="Aucun serveur", value="0")]
        sel = discord.ui.Select(placeholder="Sélectionne un serveur...", min_values=1, max_values=1, options=opts)
        sel.callback = self.on_select
        self.add_item(sel)

    async def on_select(self, interaction):
        if not can_use_panel_interaction(interaction):
            return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        value = self.children[0].values[0]
        if value == "0":
            return await interaction.response.send_message("❌ Serveur invalide.", ephemeral=True)
        guild_id = int(value)
        guild_name = next((g.get("name", "?") for g in self.guilds_data if str(g["id"]) == value), "?")
        await interaction.response.edit_message(
            content=f"⏳ Récupération des membres de **{guild_name}**...\n(Peut prendre du temps pour les gros serveurs)",
            view=None,
        )
        token = config["tokens"][self.token_index]
        config["selected_token_index"] = self.token_index
        ids = await fetch_members_via_token(token, guild_id)
        if not ids:
            return await interaction.edit_original_response(
                content=f"❌ Aucun membre récupéré sur **{guild_name}**.\nVérifie que l'intent **SERVER MEMBERS** est activé pour ce bot."
            )
        set_target_ids(ids)
        await interaction.edit_original_response(
            content=f"✅ **{config['member_count']}** membre(s) récupéré(s) de **{guild_name}**"
        )
        await refresh_panel()

class DmWizardBotSelect(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        opts = [discord.SelectOption(label=info.get("name", f"Bot {i+1}"), value=str(i)) for i, info in enumerate(config["token_infos"])]
        if not opts: opts = [discord.SelectOption(label="Aucun bot configuré", value="-1")]
        sel = discord.ui.Select(placeholder="Sélectionne un bot...", min_values=1, max_values=1, options=opts[:25])
        sel.callback = self.on_select
        self.add_item(sel)

    async def on_select(self, interaction):
        if not can_use_panel_interaction(interaction):
            return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        idx = int(self.children[0].values[0])
        if idx == -1:
            return await interaction.response.send_message("❌ Aucun bot.", ephemeral=True)
        token = config["tokens"][idx]
        bot_label = config["token_infos"][idx].get("name", f"Bot {idx+1}")
        await interaction.response.edit_message(content=f"⏳ Récupération des serveurs de **{bot_label}**...", view=None)
        guilds = await get_token_guilds(token)
        if not guilds:
            return await interaction.edit_original_response(
                content=f"❌ **{bot_label}** n'est dans aucun serveur (ou token invalide)."
            )
        await interaction.edit_original_response(
            content=f"🌐 **{bot_label}** est dans **{len(guilds)}** serveur(s).\nSélectionne celui à dmall :",
            view=DmWizardGuildSelect(idx, guilds),
        )

# ─── Option 3 : Fetch par rôles ──────────────────────────────────────────────

class FetchByRolesRoleSelect(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=120)
        self.guild = guild
        roles = [r for r in guild.roles if r.name != "@everyone"][:25]
        opts = [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles]
        if not opts: opts = [discord.SelectOption(label="Aucun rôle", value="0")]
        s = discord.ui.Select(placeholder="Sélectionne les rôles...", min_values=1, max_values=min(len(opts), 25), options=opts)
        s.callback = self.on_select; self.add_item(s)

    async def on_select(self, interaction):
        if not can_use_panel_interaction(interaction): return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        role_ids = {int(v) for v in self.children[0].values if v != "0"}
        await interaction.response.defer()
        try: await asyncio.wait_for(self.guild.chunk(cache=True), timeout=8)
        except Exception: pass
        ids = [m.id for m in self.guild.members if not m.bot and any(r.id in role_ids for r in m.roles)]
        set_target_ids(ids)
        rnames = [r.name for r in self.guild.roles if r.id in role_ids]
        await interaction.edit_original_response(content=f"✅ Fetch par rôles.\n👥 **{config['member_count']}** membre(s) — {', '.join(rnames)}", view=None)
        await refresh_panel()

class FetchByRolesGuildSelect(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        opts = [discord.SelectOption(label=g.name[:100], value=str(g.id)) for g in bot.guilds[:25]]
        if not opts: opts = [discord.SelectOption(label="Aucun serveur", value="0")]
        s = discord.ui.Select(placeholder="Sélectionne un serveur...", min_values=1, max_values=1, options=opts)
        s.callback = self.on_select; self.add_item(s)

    async def on_select(self, interaction):
        if not can_use_panel_interaction(interaction): return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        guild = bot.get_guild(int(self.children[0].values[0]))
        if not guild: return await interaction.response.send_message("❌ Serveur introuvable.", ephemeral=True)
        await interaction.response.edit_message(content=f"🎭 〃 Fetch par rôles — **{guild.name}**\n🎭 Sélectionnez les rôles", view=FetchByRolesRoleSelect(guild))

# ─── Option 4 : Fetch Vocal ──────────────────────────────────────────────────

class FetchVocalOptionView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=120)
        self.guild = guild

    @discord.ui.button(label="🔊 En vocal", style=discord.ButtonStyle.primary)
    async def in_vocal(self, interaction, _):
        if not can_use_panel_interaction(interaction): return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        await interaction.response.defer()
        try: await asyncio.wait_for(self.guild.chunk(cache=True), timeout=8)
        except Exception: pass
        ids = [m.id for m in self.guild.members if not m.bot and m.voice is not None]
        set_target_ids(ids)
        await interaction.edit_original_response(content=f"✅ **{config['member_count']}** membre(s) en vocal sur **{self.guild.name}**", view=None)
        await refresh_panel()

    @discord.ui.button(label="🔇 Pas en vocal", style=discord.ButtonStyle.secondary)
    async def not_in_vocal(self, interaction, _):
        if not can_use_panel_interaction(interaction): return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        await interaction.response.defer()
        try: await asyncio.wait_for(self.guild.chunk(cache=True), timeout=8)
        except Exception: pass
        ids = [m.id for m in self.guild.members if not m.bot and m.voice is None]
        set_target_ids(ids)
        await interaction.edit_original_response(content=f"✅ **{config['member_count']}** membre(s) hors vocal sur **{self.guild.name}**", view=None)
        await refresh_panel()

class FetchVocalGuildSelect(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        opts = [discord.SelectOption(label=g.name[:100], value=str(g.id)) for g in bot.guilds[:25]]
        if not opts: opts = [discord.SelectOption(label="Aucun serveur", value="0")]
        s = discord.ui.Select(placeholder="Sélectionne un serveur...", min_values=1, max_values=1, options=opts)
        s.callback = self.on_select; self.add_item(s)

    async def on_select(self, interaction):
        if not can_use_panel_interaction(interaction): return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        guild = bot.get_guild(int(self.children[0].values[0]))
        if not guild: return await interaction.response.send_message("❌ Serveur introuvable.", ephemeral=True)
        await interaction.response.edit_message(content=f"🔊 〃 Fetch Vocal — **{guild.name}**\nChoisissez les membres à cibler", view=FetchVocalOptionView(guild))

# ─── Option 5 : Autres ───────────────────────────────────────────────────────

class AddIgnoredIdsModal(discord.ui.Modal, title="🚫 Ajouter IDs ignorés"):
    ids_input = discord.ui.TextInput(label="IDs à ignorer", placeholder="Un ID par ligne ou virgules", style=discord.TextStyle.paragraph, max_length=4000)
    async def on_submit(self, interaction):
        raw = self.ids_input.value.replace(",", "\n")
        added = 0
        for p in raw.splitlines():
            try:
                uid = int(p.strip())
                if uid not in config["ignored_ids"]: config["ignored_ids"].append(uid); added += 1
            except ValueError: pass
        save_config()
        await interaction.response.send_message(f"🚫 **{added}** ID(s) ajouté(s) aux ignorés.", ephemeral=True)
        await refresh_panel()

class RemoveIgnoredIdsModal(discord.ui.Modal, title="✅ Retirer IDs ignorés"):
    ids_input = discord.ui.TextInput(label="IDs à retirer des ignorés", placeholder="Un ID par ligne ou virgules", style=discord.TextStyle.paragraph, max_length=4000)
    async def on_submit(self, interaction):
        raw = self.ids_input.value.replace(",", "\n")
        removed = 0
        for p in raw.splitlines():
            try:
                uid = int(p.strip())
                if uid in config["ignored_ids"]: config["ignored_ids"].remove(uid); removed += 1
            except ValueError: pass
        save_config()
        await interaction.response.send_message(f"✅ **{removed}** ID(s) retirés des ignorés.", ephemeral=True)
        await refresh_panel()

class AutresView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="🗑️ Vider la liste", style=discord.ButtonStyle.danger, row=0)
    async def clear_list(self, interaction, _):
        if not can_use_panel_interaction(interaction): return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        config["target_ids"] = []; config["member_count"] = 0; save_config()
        await interaction.response.edit_message(content="🗑️ Liste vidée. 👥 **0** ID(s).", view=None)
        await refresh_panel()

    @discord.ui.button(label="📋 Voir le total", style=discord.ButtonStyle.secondary, row=0)
    async def show_count(self, interaction, _):
        if not can_use_panel_interaction(interaction): return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        await interaction.response.send_message(f"📋 **{config['member_count']}** ID(s) cible\n🚫 **{len(config['ignored_ids'])}** ID(s) ignoré(s)", ephemeral=True)

    @discord.ui.button(label="🚫 Ajouter IDs ignorés", style=discord.ButtonStyle.secondary, row=1)
    async def add_ignored(self, interaction, _):
        if not can_use_panel_interaction(interaction): return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        await interaction.response.send_modal(AddIgnoredIdsModal())

    @discord.ui.button(label="✅ Retirer IDs ignorés", style=discord.ButtonStyle.secondary, row=1)
    async def remove_ignored(self, interaction, _):
        if not can_use_panel_interaction(interaction): return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        await interaction.response.send_modal(RemoveIgnoredIdsModal())

# ─── Menu principal Options DM ────────────────────────────────────────────────

class DmOptionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def is_owner(self, i):
        return can_use_panel_interaction(i)

    @discord.ui.button(label="1️⃣ Ajouter des IDs", style=discord.ButtonStyle.primary, custom_id="dmopt_add_ids")
    async def add_ids(self, interaction, _):
        if not self.is_owner(interaction):
            return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        await interaction.response.send_modal(AddIdsModal())

    @discord.ui.button(label="2️⃣ Fetch des membres", style=discord.ButtonStyle.primary, custom_id="dmopt_fetch_members")
    async def fetch_members(self, interaction, _):
        if not self.is_owner(interaction):
            return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        if not config["tokens"]:
            return await interaction.response.send_message("❌ Aucun token configuré.", ephemeral=True)
        await interaction.response.send_message("🤖 Sélectionnez un bot pour lister ses serveurs", view=DmWizardBotSelect(), ephemeral=True)

    @discord.ui.button(label="3️⃣ Fetch par rôles", style=discord.ButtonStyle.secondary, custom_id="dmopt_fetch_roles")
    async def fetch_roles(self, interaction, _):
        if not self.is_owner(interaction):
            return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        if not config["tokens"]:
            return await interaction.response.send_message("❌ Aucun token configuré.", ephemeral=True)
        if not bot.guilds:
            return await interaction.response.send_message("❌ Le bot principal n'est dans aucun serveur.", ephemeral=True)
        await interaction.response.send_message("🌐 Sélectionnez un serveur (bot principal)", view=FetchByRolesGuildSelect(), ephemeral=True)

    @discord.ui.button(label="4️⃣ Fetch Vocal", style=discord.ButtonStyle.secondary, custom_id="dmopt_fetch_vocal")
    async def fetch_vocal(self, interaction, _):
        if not self.is_owner(interaction):
            return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        if not config["tokens"]:
            return await interaction.response.send_message("❌ Aucun token configuré.", ephemeral=True)
        if not bot.guilds:
            return await interaction.response.send_message("❌ Le bot principal n'est dans aucun serveur.", ephemeral=True)
        await interaction.response.send_message("🌐 Sélectionnez un serveur (bot principal)", view=FetchVocalGuildSelect(), ephemeral=True)

    @discord.ui.button(label="5️⃣ Autres", style=discord.ButtonStyle.secondary, custom_id="dmopt_autres")
    async def autres(self, interaction, _):
        if not self.is_owner(interaction):
            return await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
        await interaction.response.send_message(
            content=f"## 5️⃣ 〃 Autres options\n\n📋 **{config['member_count']}** ID(s) chargé(s)\n🚫 **{len(config['ignored_ids'])}** ID(s) ignoré(s)",
            view=AutresView(),
            ephemeral=True,
        )

# ─── Modals message ───────────────────────────────────────────────────────────

class TokenModal(discord.ui.Modal, title="🤖 Ajouter des Tokens"):
    token_input = discord.ui.TextInput(
        label="Tokens (un par ligne)",
        style=discord.TextStyle.paragraph,
        placeholder="token1\ntoken2\ntoken3",
        max_length=4000,
    )
    async def on_submit(self, interaction):
        raw = self.token_input.value
        tokens = [t.strip() for t in raw.replace(",", "\n").splitlines() if t.strip()]
        if not tokens:
            return await interaction.response.send_message("❌ Aucun token fourni.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        added_lines, invalid, duplicates = [], 0, 0
        for token in tokens:
            if token in config["tokens"]:
                duplicates += 1
                continue
            info = await get_token_bot_info(token)
            if not info:
                invalid += 1
                continue
            config["tokens"].append(token)
            config["token_infos"].append(info)
            invite = f"https://discord.com/oauth2/authorize?client_id={info['id']}&scope=bot&permissions=8"
            # Active automatiquement les 3 intents privilégiés
            await enable_privileged_intents(token)
            # Démarrer la connexion Gateway persistante (statut stream)
            start_token_gateway(token)
            added_lines.append(f"✅ **{info['name']}** — [Inviter]({invite})")
        save_config()
        parts = []
        if added_lines:
            parts.append(f"**{len(added_lines)} token(s) ajouté(s) :**\n" + "\n".join(added_lines))
        if duplicates:
            parts.append(f"⚠️ {duplicates} token(s) déjà présent(s)")
        if invalid:
            parts.append(f"❌ {invalid} token(s) invalide(s)")
        await interaction.followup.send("\n\n".join(parts) or "❌ Aucun token ajouté.", ephemeral=True)
        await refresh_panel()

class SimpleMessageModal(discord.ui.Modal, title="📝 Message texte simple"):
    message_input = discord.ui.TextInput(label="Message", style=discord.TextStyle.paragraph, max_length=2000, required=False)
    async def on_submit(self, interaction):
        config["message"] = self.message_input.value.strip() or None; save_config()
        await interaction.response.send_message("✅ Message défini !", ephemeral=True); await refresh_panel()

class EmbedJsonModal(discord.ui.Modal, title="Embed JSON"):
    json_input = discord.ui.TextInput(label="JSON de l'embed", style=discord.TextStyle.paragraph, max_length=4000)
    async def on_submit(self, interaction):
        try:
            ed = json.loads(self.json_input.value.strip())
            if not isinstance(ed, dict): raise ValueError
            discord.Embed.from_dict(ed)
        except Exception: return await interaction.response.send_message("❌ JSON invalide.", ephemeral=True)
        config["embed"] = ed; save_config()
        await interaction.response.send_message("✅ Embed JSON défini !", ephemeral=True); await refresh_panel()

class EmbedBuilderModal(discord.ui.Modal, title="Embed Builder"):
    title_input = discord.ui.TextInput(label="Titre", max_length=256, required=False)
    desc_input = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph, max_length=4000, required=False)
    color_input = discord.ui.TextInput(label="Couleur hex", placeholder="5865f2", max_length=7, required=False)
    button_label_input = discord.ui.TextInput(label="Texte du bouton", max_length=80, required=False)
    button_url_input = discord.ui.TextInput(label="URL du bouton", max_length=200, required=False)
    async def on_submit(self, interaction):
        ed = {}
        if self.title_input.value.strip(): ed["title"] = self.title_input.value.strip()
        if self.desc_input.value.strip(): ed["description"] = self.desc_input.value.strip()
        c = self.color_input.value.strip().replace("#", "")
        if c:
            try: ed["color"] = int(c, 16)
            except ValueError: return await interaction.response.send_message("❌ Couleur invalide.", ephemeral=True)
        config["embed"] = ed or None
        config["button_label"] = self.button_label_input.value.strip() or None
        config["button_url"] = self.button_url_input.value.strip() or None
        save_config()
        await interaction.response.send_message("✅ Embed builder enregistré !", ephemeral=True); await refresh_panel()

class StatusModal(discord.ui.Modal, title="🎮 Statut du Bot"):
    type_input = discord.ui.TextInput(label="Type", placeholder="joue / regarde / ecoute / stream", max_length=10)
    text_input = discord.ui.TextInput(label="Texte", max_length=128)
    async def on_submit(self, interaction):
        t = self.type_input.value.strip().lower()
        act_id = ACTIVITY_TYPE_IDS.get(t)
        if act_id is None: return await interaction.response.send_message("❌ Utilise : joue / regarde / ecoute / stream", ephemeral=True)
        name = self.text_input.value.strip()
        if not config["tokens"]:
            return await interaction.response.send_message("❌ Aucun token configuré.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        results = await asyncio.gather(*[set_token_status_via_gateway(token, act_id, name) for token in config["tokens"]])
        ok = sum(1 for r in results if r)
        fail = len(results) - ok
        msg = f"✅ Statut **{t} {name}** appliqué sur **{ok}/{len(results)}** bot(s)"
        if fail: msg += f"\n⚠️ **{fail}** bot(s) ont échoué (token invalide ou erreur gateway)"
        await interaction.followup.send(msg, ephemeral=True)

# ─── MessageConfigView ────────────────────────────────────────────────────────

class MessageConfigView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    def is_owner(self, i): return can_use_panel_interaction(i)

    @discord.ui.button(label="Saisir un message", style=discord.ButtonStyle.primary, custom_id="simple_message_btn")
    async def simple_message_btn(self, i, _):
        if not self.is_owner(i): return await i.response.send_message("❌", ephemeral=True)
        await i.response.send_modal(SimpleMessageModal())

    @discord.ui.button(label="Embed JSON", style=discord.ButtonStyle.primary, custom_id="embed_json_btn")
    async def embed_json_btn(self, i, _):
        if not self.is_owner(i): return await i.response.send_message("❌", ephemeral=True)
        await i.response.send_modal(EmbedJsonModal())

    @discord.ui.button(label="Embed Builder", style=discord.ButtonStyle.primary, custom_id="embed_builder_btn")
    async def embed_builder_btn(self, i, _):
        if not self.is_owner(i): return await i.response.send_message("❌", ephemeral=True)
        await i.response.send_modal(EmbedBuilderModal())

    @discord.ui.button(label="Aperçu", style=discord.ButtonStyle.secondary, custom_id="preview_message_btn")
    async def preview_message_btn(self, i, _):
        if not self.is_owner(i): return await i.response.send_message("❌", ephemeral=True)
        payload = build_dm_payload(i.user)
        if not payload: return await i.response.send_message("❌ Aucun message configuré.", ephemeral=True)
        c = f"👀 Aperçu :\n\n{payload['content']}" if payload.get("content") else "👀 Aperçu :"
        e = discord.Embed.from_dict(payload["embeds"][0]) if payload.get("embeds") else None
        v = None
        if config["button_label"] and config["button_url"]:
            v = discord.ui.View(); v.add_item(discord.ui.Bdanutton(label=config["button_label"], url=config["button_url"]))
        await i.response.send_message(c, embed=e, view=v, ephemeral=True)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger, custom_id="reset_message_btn")
    async def reset_message_btn(self, i, _):
        if not self.is_owner(i): return await i.response.send_message("❌", ephemeral=True)
        config["message"] = config["embed"] = config["button_label"] = config["button_url"] = None; save_config()
        await i.response.send_message("✅ Réinitialisé.", ephemeral=True); await refresh_panel()

# ─── Dmall : moteur optimisé ──────────────────────────────────────────────────

async def run_dmall(interaction, selected_tokens, selected_infos):
    global DMALL_RUNNING, DMALL_STOP
    if DMALL_RUNNING:
        return await interaction.edit_original_response(content="⏳ Un dmall est déjà en cours.", view=None)

    target_ids = [uid for uid in config["target_ids"] if uid not in config["ignored_ids"]]
    if not target_ids:
        return await interaction.edit_original_response(content="❌ Aucune cible.", view=None)

    DMALL_RUNNING = True
    DMALL_STOP = False
    nb = len(selected_tokens)
    per_bot_sent = [0] * nb
    per_bot_failed = [0] * nb

    chunks = [target_ids[i::nb] for i in range(nb)]

    def bname(i):
        return selected_infos[i].get("name", f"Bot {i+1}") if i < len(selected_infos) else f"Bot {i+1}"

    def stats_block():
        return "\n".join(
            f"• **{bname(i)}** — ✅ {per_bot_sent[i]} / ❌ {per_bot_failed[i]} ({len(chunks[i])} cibles)"
            for i in range(nb)
        )

    def fmt():
        total_sent = sum(per_bot_sent)
        total_failed = sum(per_bot_failed)
        total_done = total_sent + total_failed
        total = len(target_ids)
        filled = round((total_done / total) * 10) if total > 0 else 0
        bar = "🟩" * filled + "⬛" * (10 - filled)
        return (
            f"## 🚀 Dmall en cours — {nb} bot(s) en parallèle\n"
            f"{bar} `{total_done}/{total}`\n"
            f"✅ **{total_sent}** envoyé(s) | ❌ **{total_failed}** échoué(s)\n\n"
            f"{stats_block()}"
        )

    await interaction.edit_original_response(content=fmt(), view=None)
    progress_msg = await interaction.original_response()

    # Semaphore : 25 DMs simultanés par bot pour maximiser la vitesse
    CONCURRENT_PER_BOT = 25

    async def bot_worker(tidx, token, chunk):
        sem = asyncio.Semaphore(CONCURRENT_PER_BOT)
        connector = aiohttp.TCPConnector(limit=CONCURRENT_PER_BOT + 2)
        timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async def send_one(uid):
                async with sem:
                    if DMALL_STOP:
                        return
                    payload = build_dm_payload_for_id(uid)
                    if not payload:
                        per_bot_failed[tidx] += 1
                        return
                    ok = await send_dm_with_session(session, token, uid, payload)
                    if ok:
                        per_bot_sent[tidx] += 1
                    else:
                        per_bot_failed[tidx] += 1

            await asyncio.gather(*[send_one(uid) for uid in chunk])

    async def progress_updater():
        while DMALL_RUNNING:
            try:
                await progress_msg.edit(content=fmt())
            except Exception:
                pass
            await asyncio.sleep(2)

    try:
        workers = [bot_worker(i, selected_tokens[i], chunks[i]) for i in range(nb)]
        updater = asyncio.create_task(progress_updater())
        await asyncio.gather(*workers)
    finally:
        DMALL_RUNNING = False
        updater.cancel()

    total_sent = sum(per_bot_sent)
    total_failed = sum(per_bot_failed)
    # Mise à jour des stats globales
    config["stats_total_sent"] += total_sent
    config["stats_total_failed"] += total_failed
    config["stats_total_sessions"] += 1
    existing = set(config.get("stats_unique_users", []))
    existing.update(target_ids)
    config["stats_unique_users"] = list(existing)
    save_config()
    try:
        await progress_msg.edit(
            content=(
                f"## ✅ Dmall terminé !\n"
                f"✅ **{total_sent}** envoyé(s) | ❌ **{total_failed}** échoué(s)\n\n"
                f"{stats_block()}"
            )
        )
    except Exception:
        pass


class DmallBotPickView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="🌐 Tous les bots", style=discord.ButtonStyle.danger)
    async def all_bots(self, interaction, _):
        if not can_use_panel_interaction(interaction):
            return await interaction.response.send_message("❌", ephemeral=True)
        await interaction.response.defer()
        await run_dmall(interaction, list(config["tokens"]), list(config["token_infos"]))

    @discord.ui.button(label="🤖 Choisir un bot", style=discord.ButtonStyle.primary)
    async def pick_one(self, interaction, _):
        if not can_use_panel_interaction(interaction):
            return await interaction.response.send_message("❌", ephemeral=True)
        if not config["tokens"]:
            return await interaction.response.send_message("❌ Aucun bot.", ephemeral=True)
        opts = [
            discord.SelectOption(
                label=info.get("name", f"Bot {i+1}")[:100],
                value=str(i),
                description=f"Bot #{i+1}"
            )
            for i, info in enumerate(config["token_infos"])
        ]
        if not opts:
            opts = [discord.SelectOption(label="Aucun bot", value="-1")]
        sel = discord.ui.Select(placeholder="Sélectionne un bot...", options=opts[:25])

        async def on_select(inter):
            if not can_use_panel_interaction(inter):
                return await inter.response.send_message("❌", ephemeral=True)
            idx = int(sel.values[0])
            if idx == -1:
                return await inter.response.send_message("❌ Aucun bot valide.", ephemeral=True)
            await inter.response.defer()
            await run_dmall(
                inter,
                [config["tokens"][idx]],
                [config["token_infos"][idx]],
            )

        sel.callback = on_select
        v = discord.ui.View(timeout=60)
        v.add_item(sel)
        await interaction.response.edit_message(
            content="## 🤖 Sélectionne le bot à utiliser :",
            view=v,
        )


# ─── PanelView ────────────────────────────────────────────────────────────────

class PanelView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    def is_owner(self, i): return can_use_panel_interaction(i)

    @discord.ui.button(label="🤖 Ajouter Token", style=discord.ButtonStyle.primary, custom_id="add_token_btn")
    async def add_token_btn(self, i, _):
        if not self.is_owner(i): return await i.response.send_message("# `❌` ***〃 Ce panel ne t'appartient pas. Fais `+panel` pour créer le tien.***", ephemeral=True)
        if not await is_in_support(i.user.id):
            return await i.response.send_message("# `❌` ***〃 Tu dois être sur le serveur support : https://discord.gg/Nx3EFxg5eM ***", ephemeral=True)
        await i.response.send_modal(TokenModal())

    @discord.ui.button(label="📝 Définir le message", style=discord.ButtonStyle.primary, custom_id="open_message_config_btn")
    async def open_message_config_btn(self, i, _):
        if not self.is_owner(i): return await i.response.send_message("# `❌` ***〃 Ce panel ne t'appartient pas. Fais `+panel` pour créer le tien.***", ephemeral=True)
        if not await is_in_support(i.user.id):
            return await i.response.send_message("# `❌` ***〃 Tu dois être sur le serveur support : https://discord.gg/Nx3EFxg5eM ***", ephemeral=True)
        await send_ephemeral_components(i, build_message_config_components())

    @discord.ui.button(label="⚙️ Options DM", style=discord.ButtonStyle.secondary, custom_id="dm_options_btn")
    async def dm_options_btn(self, i, _):
        if not self.is_owner(i): return await i.response.send_message("# `❌` ***〃 Ce panel ne t'appartient pas. Fais `+panel` pour créer le tien.***", ephemeral=True)
        if not await is_in_support(i.user.id):
            return await i.response.send_message("# `❌` ***〃 Tu dois être sur le serveur support : https://discord.gg/Nx3EFxg5eM ***", ephemeral=True)
        await send_ephemeral_components(i, build_dm_options_components())

    @discord.ui.button(label="⭐ Statut", style=discord.ButtonStyle.secondary, custom_id="set_status_btn")
    async def set_status_btn(self, i, _):
        if not self.is_owner(i): return await i.response.send_message("# `❌` ***〃 Ce panel ne t'appartient pas. Fais `+panel` pour créer le tien.***", ephemeral=True)
        if not await is_in_support(i.user.id):
            return await i.response.send_message("# `❌` ***〃 Tu dois être sur le serveur support : https://discord.gg/Nx3EFxg5eM ***", ephemeral=True)
        if i.user.id != OWNER_ID and i.user.id not in config.get("premium_users", []):
            return await i.response.send_message(
                "❌ 〃 Vous devez être premium pour utiliser ce bouton, afin de devenir Premium contactez un owner dans le serveur support",
                ephemeral=True,
            )
        await i.response.send_modal(StatusModal())

    @discord.ui.button(label="🚀 Dmall", style=discord.ButtonStyle.danger, custom_id="dmall_execute_btn")
    async def dmall_execute_btn(self, interaction, _):
        if not self.is_owner(interaction): return await interaction.response.send_message("# `❌` ***〃 Ce panel ne t'appartient pas. Fais `+panel` pour créer le tien.***", ephemeral=True)
        if not await is_in_support(interaction.user.id):
            return await interaction.response.send_message("# `❌` ***〃 Tu dois être sur le serveur support : https://discord.gg/Nx3EFxg5eM ***", ephemeral=True)
        if DMALL_RUNNING: return await interaction.response.send_message("⏳ Un dmall est déjà en cours.", ephemeral=True)
        if not config["tokens"]: return await interaction.response.send_message("❌ Aucun token.", ephemeral=True)
        if not config["message"] and not config["embed"]: return await interaction.response.send_message("❌ Aucun message configuré.", ephemeral=True)
        if not config["target_ids"]: return await interaction.response.send_message("❌ Aucun membre. Configure via **⚙️ Options DM**.", ephemeral=True)
        await interaction.response.send_message(
            f"## 🚀 Lancer le Dmall\n**Sélectionne le(s) bot(s) à utiliser :**\n👥 **{len(config['target_ids'])}** cibles",
            view=DmallBotPickView(),
            ephemeral=True,
        )


@bot.command(name="stop")
async def stop_cmd(ctx):
    global DMALL_STOP
    if ctx.author.id != OWNER_ID:
        return
    if not DMALL_RUNNING:
        return await ctx.send("❌ Aucun dmall en cours.", delete_after=5)
    DMALL_STOP = True
    await ctx.send("🛑 Dmall arrêté.", delete_after=5)


def can_use_panel(ctx) -> bool:
    if ctx.author.id == OWNER_ID: return True
    if ctx.guild is None: return False
    if ctx.guild.owner_id == ctx.author.id: return True
    if ctx.author.guild_permissions.administrator: return True
    return False

def can_use_panel_interaction(interaction) -> bool:
    if interaction.user.id == OWNER_ID: return True
    panel_owner = config.get("panel_owner_id")
    if panel_owner and interaction.user.id == panel_owner: return True
    return False

async def is_in_support(user_id: int) -> bool:
    if user_id == OWNER_ID: return True
    if not SUPPORT_GUILD_ID: return True
    support_guild = bot.get_guild(SUPPORT_GUILD_ID)
    if support_guild:
        member = support_guild.get_member(user_id)
        if member is None:
            try:
                member = await support_guild.fetch_member(user_id)
            except discord.NotFound:
                return False
            except Exception:
                return False
        return True
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.get(
                f"{DISCORD_API}/guilds/{SUPPORT_GUILD_ID}/members/{user_id}",
                headers=bot_headers(),
            ) as r:
                return r.status == 200
    except Exception:
        return False

@bot.command(name="help")
async def help_cmd(ctx):
    await ctx.send(
        "## `💎` 〃 FluxBot — Commandes\n"
        ">>> `+panel` — Ouvre le panel de configuration du Dmall\n"
    )

@bot.command(name="panel")
async def panel_cmd(ctx):
    if not can_use_panel(ctx):
        return
    # Vérifier que l'auteur est dans le serveur support
    in_support = False
    if SUPPORT_GUILD_ID:
        support_guild = bot.get_guild(SUPPORT_GUILD_ID)
        if support_guild:
            member = support_guild.get_member(ctx.author.id)
            if member is None:
                try:
                    member = await support_guild.fetch_member(ctx.author.id)
                except discord.NotFound:
                    member = None
                except Exception:
                    member = None
            in_support = member is not None
        else:
            # Bot pas dans le serveur support — vérifier via API directe
            try:
                async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
                    async with session.get(
                        f"{DISCORD_API}/guilds/{SUPPORT_GUILD_ID}/members/{ctx.author.id}",
                        headers=bot_headers(),
                    ) as r:
                        in_support = r.status == 200
            except Exception:
                in_support = False
    else:
        in_support = True  # Invitation pas encore résolue, on laisse passer
    if not in_support:
        return await ctx.send(
            "# `❌` ***〃 Tu dois être sur le serveur support : https://discord.gg/Nx3EFxg5eM ***",
        )
    # Tracker l'utilisateur du panel
    uid = ctx.author.id
    if uid not in config.get("stats_panel_users", []):
        config.setdefault("stats_panel_users", []).append(uid)
        save_config()
    try:
        # Supprime l'ancien panel s'il existe
        if config["panel_message_id"] and config["panel_channel_id"]:
            async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
                await session.delete(
                    f"{DISCORD_API}/channels/{config['panel_channel_id']}/messages/{config['panel_message_id']}",
                    headers=bot_headers(),
                )

        # Remet tout à zéro
        config["tokens"] = []
        config["token_infos"] = []
        config["message"] = None
        config["embed"] = None
        config["button_label"] = None
        config["button_url"] = None
        config["ignored_ids"] = []
        config["target_ids"] = []
        config["member_count"] = 0
        config["selected_token_index"] = 0
        config["panel_message_id"] = None
        config["panel_channel_id"] = None
        config["panel_owner_id"] = None
        save_config()

        data = await send_panel_v2(ctx.channel.id)
        config["panel_message_id"] = data["id"]
        config["panel_channel_id"] = ctx.channel.id
        config["panel_owner_id"] = ctx.author.id
        save_config()
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}", delete_after=10)


# ─── +botconfig ───────────────────────────────────────────────────────────────

async def url_to_base64(url: str) -> str | None:
    """Télécharge une image depuis une URL et retourne le data URI base64."""
    try:
        import base64, mimetypes
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.get(url) as r:
                if r.status != 200: return None
                ct = r.content_type or "image/png"
                data = await r.read()
                b64 = base64.b64encode(data).decode()
                return f"data:{ct};base64,{b64}"
    except Exception:
        return None

async def patch_bot_via_token(token: str, payload: dict) -> tuple[bool, str]:
    """Modifie le profil du bot via PATCH /users/@me."""
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.patch(f"{DISCORD_API}/users/@me", json=payload, headers=bot_headers(token)) as r:
                data = await r.json()
                if r.status == 200: return True, ""
                msg = data.get("message", str(data))
                return False, msg
    except Exception as e:
        return False, str(e)

async def patch_app_via_token(token: str, payload: dict) -> tuple[bool, str]:
    """Modifie l'application du bot via PATCH /applications/@me (bio/description)."""
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.patch(f"{DISCORD_API}/applications/@me", json=payload, headers=bot_headers(token)) as r:
                data = await r.json()
                if r.status == 200: return True, ""
                return False, data.get("message", str(data))
    except Exception as e:
        return False, str(e)

_token_gateway_tasks: dict[str, asyncio.Task] = {}

async def _maintain_token_status(token: str, activity_name: str, twitch_url: str):
    """Connexion Gateway persistante avec heartbeat — maintient le statut stream indéfiniment."""
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{DISCORD_API}/gateway", headers=bot_headers(token)) as r:
                    if r.status != 200:
                        await asyncio.sleep(30)
                        continue
                    gw_url = (await r.json()).get("url", "wss://gateway.discord.gg") + "/?v=10&encoding=json"
                async with session.ws_connect(gw_url) as ws:
                    heartbeat_interval = 41250
                    last_seq = None
                    hb_task = None

                    async def heartbeat_loop():
                        await asyncio.sleep(heartbeat_interval / 1000 * 0.9)
                        while True:
                            try:
                                await ws.send_json({"op": 1, "d": last_seq})
                            except Exception:
                                return
                            await asyncio.sleep(heartbeat_interval / 1000)

                    async for msg in ws:
                        if msg.type != aiohttp.WSMsgType.TEXT:
                            break
                        data = json.loads(msg.data)
                        op = data.get("op")
                        s = data.get("s")
                        if s:
                            last_seq = s
                        if op == 10:
                            heartbeat_interval = data["d"]["heartbeat_interval"]
                            if hb_task:
                                hb_task.cancel()
                            hb_task = asyncio.create_task(heartbeat_loop())
                            await ws.send_json({
                                "op": 2,
                                "d": {
                                    "token": token,
                                    "intents": 0,
                                    "properties": {"os": "linux", "browser": "disco", "device": "disco"},
                                    "presence": {
                                        "activities": [{"name": activity_name, "type": 1, "url": twitch_url}],
                                        "status": "online", "since": None, "afk": False,
                                    },
                                },
                            })
                        elif op == 9:
                            break
                    if hb_task:
                        hb_task.cancel()
        except asyncio.CancelledError:
            return
        except Exception:
            pass
        await asyncio.sleep(5)

def start_token_gateway(token: str):
    """Lance (ou relance) la connexion Gateway persistante pour un token."""
    existing = _token_gateway_tasks.get(token)
    if existing and not existing.done():
        existing.cancel()
    _token_gateway_tasks[token] = asyncio.create_task(
        _maintain_token_status(token, "discord.gg/Nx3EFxg5eM", "https://www.twitch.tv/uhqzk")
    )

async def set_token_status_streaming(token: str, activity_name: str, twitch_url: str) -> bool:
    """Alias conservé pour compatibilité (utilisé par le panel ⭐ Statut)."""
    start_token_gateway(token)
    return True

# Modals BotConfig

class BotConfigNameModal(discord.ui.Modal, title="✏️ Changer le nom"):
    name_input = discord.ui.TextInput(label="Nouveau nom du bot", max_length=32)
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        token = os.environ.get("TOKEN", "")
        ok, err = await patch_bot_via_token(token, {"username": self.name_input.value.strip()})
        if ok: await interaction.followup.send(f"✅ Nom changé en **{self.name_input.value.strip()}**", ephemeral=True)
        else: await interaction.followup.send(f"❌ Erreur : `{err}`", ephemeral=True)

class BotConfigStatusModal(discord.ui.Modal, title="🎮 Changer le statut"):
    type_input = discord.ui.TextInput(label="Type (joue / regarde / ecoute / stream)", placeholder="stream", max_length=10)
    text_input = discord.ui.TextInput(label="Texte du statut", max_length=128)
    twitch_input = discord.ui.TextInput(label="Pseudo ou lien Twitch (si type=stream)", placeholder="monpseudo ou https://twitch.tv/monpseudo", required=False, max_length=200)
    async def on_submit(self, interaction):
        t = self.type_input.value.strip().lower()
        name = self.text_input.value.strip()
        raw = self.twitch_input.value.strip()
        # Normalise l'URL Twitch (supporte tous les formats)
        if raw:
            import re as _re
            m = _re.search(r"twitch\.tv/([A-Za-z0-9_]+)", raw)
            if m:
                twitch_url = "https://twitch.tv/" + m.group(1)
            else:
                # Juste un pseudo sans URL
                pseudo = raw.strip("/").split("/")[0]
                twitch_url = "https://twitch.tv/" + pseudo
        else:
            twitch_url = ""
        if t == "stream":
            if twitch_url:
                act = discord.Activity(type=discord.ActivityType.streaming, name=name, url=twitch_url)
                confirmation = f"✅ Statut stream **{name}** — bouton 🟣 Regarder activé !"
            else:
                act = discord.Activity(type=discord.ActivityType.streaming, name=name, url="https://twitch.tv/discord")
                confirmation = f"✅ Statut stream **{name}** (sans lien Twitch spécifique)"
        else:
            act_type = ACTIVITY_TYPES.get(t)
            if not act_type:
                return await interaction.response.send_message("❌ Utilise : joue / regarde / ecoute / stream", ephemeral=True)
            act = discord.Activity(type=act_type, name=name)
            confirmation = f"✅ Statut **{t} {name}**"
        await bot.change_presence(status=discord.Status.online, activity=act)
        # Sauvegarder pour restauration après reconnexion
        config["saved_presence"] = {"type": t, "name": name, "twitch_url": twitch_url}
        save_config()
        await interaction.response.send_message(confirmation, ephemeral=True)

class BotConfigAvatarModal(discord.ui.Modal, title="🖼️ Changer la photo de profil"):
    url_input = discord.ui.TextInput(label="URL de l'image (PNG/JPG/GIF)", max_length=500)
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        b64 = await url_to_base64(self.url_input.value.strip())
        if not b64:
            return await interaction.followup.send("❌ Impossible de télécharger l'image.", ephemeral=True)
        token = os.environ.get("TOKEN", "")
        ok, err = await patch_bot_via_token(token, {"avatar": b64})
        if ok: await interaction.followup.send("✅ Photo de profil changée !", ephemeral=True)
        else: await interaction.followup.send(f"❌ Erreur : `{err}`", ephemeral=True)

class BotConfigBannerModal(discord.ui.Modal, title="🖼️ Changer la bannière"):
    url_input = discord.ui.TextInput(label="URL de la bannière (PNG/JPG/GIF)", max_length=500)
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        b64 = await url_to_base64(self.url_input.value.strip())
        if not b64:
            return await interaction.followup.send("❌ Impossible de télécharger l'image.", ephemeral=True)
        token = os.environ.get("TOKEN", "")
        ok, err = await patch_bot_via_token(token, {"banner": b64})
        if ok: await interaction.followup.send("✅ Bannière changée !", ephemeral=True)
        else: await interaction.followup.send(f"❌ Erreur : `{err}`\n-# Note : la bannière nécessite Nitro sur le compte bot.", ephemeral=True)

class BotConfigBioModal(discord.ui.Modal, title="📝 Changer la bio"):
    bio_input = discord.ui.TextInput(label="Bio / Description", style=discord.TextStyle.paragraph, max_length=400, required=False)
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        token = os.environ.get("TOKEN", "")
        ok, err = await patch_app_via_token(token, {"description": self.bio_input.value.strip()})
        if ok: await interaction.followup.send("✅ Bio changée !", ephemeral=True)
        else: await interaction.followup.send(f"❌ Erreur : `{err}`", ephemeral=True)

class BotConfigView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="✏️ Nom", style=discord.ButtonStyle.primary, custom_id="bc_name")
    async def change_name(self, interaction, _):
        if interaction.user.id != OWNER_ID: return await interaction.response.send_message("❌", ephemeral=True)
        await interaction.response.send_modal(BotConfigNameModal())

    @discord.ui.button(label="🎮 Statut", style=discord.ButtonStyle.primary, custom_id="bc_status")
    async def change_status(self, interaction, _):
        if interaction.user.id != OWNER_ID: return await interaction.response.send_message("❌", ephemeral=True)
        await interaction.response.send_modal(BotConfigStatusModal())

    @discord.ui.button(label="🖼️ Photo de profil", style=discord.ButtonStyle.secondary, custom_id="bc_avatar")
    async def change_avatar(self, interaction, _):
        if interaction.user.id != OWNER_ID: return await interaction.response.send_message("❌", ephemeral=True)
        await interaction.response.send_modal(BotConfigAvatarModal())

    @discord.ui.button(label="🖼️ Bannière", style=discord.ButtonStyle.secondary, custom_id="bc_banner")
    async def change_banner(self, interaction, _):
        if interaction.user.id != OWNER_ID: return await interaction.response.send_message("❌", ephemeral=True)
        await interaction.response.send_modal(BotConfigBannerModal())

    @discord.ui.button(label="📝 Bio", style=discord.ButtonStyle.secondary, custom_id="bc_bio")
    async def change_bio(self, interaction, _):
        if interaction.user.id != OWNER_ID: return await interaction.response.send_message("❌", ephemeral=True)
        await interaction.response.send_modal(BotConfigBioModal())

def build_botconfig_components() -> list:
    nb = len(config["tokens"])
    return [
        {
            "type": 17, "accent_color": 0x757A86,
            "components": [
                text_component(f"## ⚙️ 〃 BotConfig\n**__Configurez vos bots ci-dessous. S'applique sur les {nb} token(s) ajouté(s).__**"),
                separator(),
                text_component("✏️ **Nom** — Change le username de tous les bots\n🎮 **Statut** — Change le statut (supporte le stream Twitch)\n🖼️ **Photo / Bannière** — Change les images de profil\n📝 **Bio** — Change la description de l'application"),
                separator(),
                action_row(button("✏️ Nom", BLUE, "bc_name"), button("🎮 Statut", BLUE, "bc_status")),
                action_row(button("🖼️ Photo de profil", GRAY, "bc_avatar"), button("🖼️ Bannière", GRAY, "bc_banner"), button("📝 Bio", GRAY, "bc_bio")),
                separator(),
                text_component("-# FluxBot • Crée par **mazuu.bs**"),
            ],
        }
    ]

@bot.command(name="premium")
async def premium_cmd(ctx, subcommand: str = None, *, target: str = None):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except Exception: pass
    usage = "❌ Usage : `+premium <add/remove/clear> @user/ID`"
    if not subcommand:
        return await ctx.send(usage)
    sub = subcommand.lower()
    if sub == "clear":
        count = len(config.get("premium_users", []))
        config["premium_users"] = []
        save_config()
        return await ctx.send(f"🗑️ **{count}** utilisateur(s) retiré(s) du Premium.")
    if sub in ("add", "remove"):
        if not target:
            return await ctx.send(usage)
        raw = target.strip().replace("<@", "").replace(">", "").replace("!", "")
        try:
            uid = int(raw)
        except ValueError:
            return await ctx.send("❌ Utilisateur invalide.")
        premium_list = config.setdefault("premium_users", [])
        if sub == "add":
            if uid in premium_list:
                return await ctx.send(f"⚠️ <@{uid}> est déjà **Premium**.")
            premium_list.append(uid)
            save_config()
            await ctx.send(f"⭐ <@{uid}> ajouté au **Premium** — accès au bouton Statut débloqué.")
        else:
            if uid not in premium_list:
                return await ctx.send(f"⚠️ <@{uid}> n'est pas **Premium**.")
            premium_list.remove(uid)
            save_config()
            await ctx.send(f"✅ <@{uid}> retiré du **Premium**.")
    else:
        await ctx.send(usage)

@bot.command(name="listpremium")
async def listpremium_cmd(ctx):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except Exception: pass
    premium_list = config.get("premium_users", [])
    if not premium_list:
        lines = "Aucun utilisateur premium."
    else:
        lines = "\n".join(f"`{i}.` <@{uid}> — `{uid}`" for i, uid in enumerate(premium_list, 1))
    components = [
        {
            "type": 17, "accent_color": 0x757A86,
            "components": [
                text_component(f"## ⭐ 〃 Liste Premium — {len(premium_list)} utilisateur(s)"),
                separator(),
                text_component(lines),
                separator(),
                text_component("-# FluxBot • Crée par **mazuu.bs**"),
            ],
        }
    ]
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(
                f"{DISCORD_API}/channels/{ctx.channel.id}/messages",
                json={"flags": COMPONENTS_V2, "components": components},
                headers=bot_headers(),
            ) as r:
                if r.status >= 400:
                    data = await r.json()
                    await ctx.send(f"❌ Erreur : {data}", delete_after=10)
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}", delete_after=10)

@bot.command(name="lb")
async def lb_cmd(ctx):
    if ctx.author.id != OWNER_ID: return
    try: await ctx.message.delete()
    except Exception: pass
    total_sent     = config.get("stats_total_sent", 0)
    total_failed   = config.get("stats_total_failed", 0)
    total_sessions = config.get("stats_total_sessions", 0)
    unique_users   = len(config.get("stats_unique_users", []))
    total_tokens   = len(config.get("tokens", []))
    total_targets  = config.get("member_count", 0)
    panel_users    = len(config.get("stats_panel_users", []))
    server_count   = len(bot.guilds)
    success_rate   = f"{round(total_sent / (total_sent + total_failed) * 100)}%" if (total_sent + total_failed) > 0 else "N/A"
    components = [
        {
            "type": 17, "accent_color": 0x757A86,
            "components": [
                text_component("## 📊 〃 Leaderboard — Statistiques globales"),
                separator(),
                text_component(
                    f"✅ **DMs envoyés** — `{total_sent:,}`\n"
                    f"❌ **DMs échoués** — `{total_failed:,}`\n"
                    f"📈 **Taux de succès** — `{success_rate}`"
                ),
                separator(),
                text_component(
                    f"👥 **Utilisateurs uniques ciblés** — `{unique_users:,}`\n"
                    f"🚀 **Sessions Dmall lancées** — `{total_sessions:,}`\n"
                    f"🤖 **Tokens actifs** — `{total_tokens}`\n"
                    f"🎯 **Cibles actuelles** — `{total_targets:,}`"
                ),
                separator(),
                text_component(
                    f"🌐 **Serveurs** — `{server_count}`\n"
                    f"👤 **Utilisateurs du panel** — `{panel_users}`"
                ),
                separator(),
                text_component("-# FluxBot • Crée par **mazuu.bs**"),
            ],
        }
    ]
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(
                f"{DISCORD_API}/channels/{ctx.channel.id}/messages",
                json={"flags": COMPONENTS_V2, "components": components},
                headers=bot_headers(),
            ) as r:
                if r.status >= 400:
                    data = await r.json()
                    await ctx.send(f"❌ Erreur : {data}", delete_after=10)
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}", delete_after=10)

@bot.command(name="botconfig")
async def botconfig_cmd(ctx):
    if ctx.author.id != OWNER_ID: return
    try:
        await ctx.message.delete()
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(
                f"{DISCORD_API}/channels/{ctx.channel.id}/messages",
                json={"flags": COMPONENTS_V2, "components": build_botconfig_components()},
                headers=bot_headers(),
            ) as r:
                if r.status >= 400:
                    data = await r.json()
                    await ctx.send(f"❌ Erreur : {data}", delete_after=10)
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}", delete_after=10)


@bot.command(name="enablev2")
async def enable_components_v2(ctx):
    if ctx.author.id != OWNER_ID:
        return
    async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
        async with session.get(f"{DISCORD_API}/applications/@me", headers=bot_headers()) as r:
            app_data = await r.json()
            current_flags = app_data.get("flags", 0)
        new_flags = current_flags | (1 << 23)
        async with session.patch(
            f"{DISCORD_API}/applications/@me",
            json={"flags": new_flags},
            headers=bot_headers()
        ) as r:
            data = await r.json()
            if r.status == 200:
                await ctx.send(f"✅ Flags mis à jour : `{data.get('flags')}` — Retape `+panel`", delete_after=15)
            else:
                await ctx.send(f"❌ Erreur {r.status} : `{data}`", delete_after=20)


@bot.event
async def on_ready():
    global VIEWS_READY, SUPPORT_GUILD_ID
    load_config()
    if not VIEWS_READY:
        bot.add_view(PanelView())
        bot.add_view(MessageConfigView())
        bot.add_view(DmOptionsView())
        bot.add_view(BotConfigView())
        VIEWS_READY = True
    # Résoudre l'ID du serveur support depuis l'invitation
    if SUPPORT_GUILD_ID is None:
        try:
            async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
                async with session.get(f"{DISCORD_API}/invites/{SUPPORT_INVITE}") as r:
                    if r.status == 200:
                        data = await r.json()
                        SUPPORT_GUILD_ID = int(data["guild"]["id"])
                        print(f"[OK] Serveur support ID : {SUPPORT_GUILD_ID}")
        except Exception as e:
            print(f"[WARN] Impossible de résoudre l'invitation support : {e}")
    # Relancer les connexions Gateway persistantes pour tous les tokens enregistrés
    for token in config.get("tokens", []):
        start_token_gateway(token)
    # Restaurer le statut sauvegardé
    sp = config.get("saved_presence")
    if sp:
        try:
            t = sp.get("type", "joue")
            name = sp.get("name", "")
            twitch_url = sp.get("twitch_url", "")
            if t == "stream":
                url = twitch_url or "https://twitch.tv/discord"
                act = discord.Activity(type=discord.ActivityType.streaming, name=name, url=url)
            else:
                act_type = ACTIVITY_TYPES.get(t, discord.ActivityType.playing)
                act = discord.Activity(type=act_type, name=name)
            await bot.change_presence(status=discord.Status.online, activity=act)
        except Exception as e:
            print(f"[WARN] Impossible de restaurer le statut : {e}")
    print(f"[OK] {bot.user} connecté ({len(bot.guilds)} serveur(s)) — {len(config.get('tokens', []))} gateway(s) token lancé(s)")


bot.run(os.environ.get("DISCORD_TOKEN", os.environ.get("TOKEN", "")))
