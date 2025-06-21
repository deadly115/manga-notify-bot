# bot.py — Track manga, manage ping lists, show latest chapter across 4 sites
# Works on discord.py 2.5.x + aiohttp + aiosqlite + python-dotenv + beautifulsoup4 + lxml
# models.sql as before: subscriptions(url,channel_id,last_id,ping_ids,owner_id)

import os
import asyncio
import logging
from pathlib import Path
from typing import List, Optional

import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp, aiosqlite
from bs4 import BeautifulSoup

# ─────── Load DISCORD_TOKEN ────────────────────────────────────────────
# 1) Read from the real environment (Railway, VPS, etc.)
TOKEN = os.getenv("DISCORD_TOKEN")
# 2) If not set, fall back to loading a .env file (for local dev)
if not TOKEN:
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
# 3) If still missing, abort
if not TOKEN:
    raise SystemExit("❌ Please set DISCORD_TOKEN as an environment variable")

# ─────── Logging & Bot Setup ───────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
bot = commands.Bot(command_prefix="/", intents=discord.Intents.default())

DB_FILE = "data.db"
SQL     = Path("models.sql").read_text()

# Import the dispatcher that picks the right adapter based on URL
from adapters import get_latest

# ─────── Database Helpers ─────────────────────────────────────────────
async def db_init():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.executescript(SQL)
        await db.commit()

async def db_upsert(url: str, channel_id: int, last_id: str,
                    ping_ids: List[int], owner_id: int):
    csv = ",".join(map(str, ping_ids))
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO subscriptions "
            "(url,channel_id,last_id,ping_ids,owner_id) VALUES (?,?,?,?,?)",
            (url, channel_id, last_id, csv, owner_id),
        )
        await db.commit()

async def db_get(url: str, channel_id: int) -> Optional[tuple]:
    async with aiosqlite.connect(DB_FILE) as db:
        cur = await db.execute(
            "SELECT last_id,ping_ids FROM subscriptions "
            "WHERE url=? AND channel_id=?",
            (url, channel_id),
        )
        row = await cur.fetchone()
        await cur.close()
        return row

async def db_rows() -> List[tuple]:
    async with aiosqlite.connect(DB_FILE) as db:
        cur = await db.execute(
            "SELECT url,channel_id,last_id,ping_ids FROM subscriptions"
        )
        rows = await cur.fetchall()
        await cur.close()
        return rows

async def db_urls_for_channel(channel_id: int) -> List[str]:
    async with aiosqlite.connect(DB_FILE) as db:
        cur = await db.execute(
            "SELECT url FROM subscriptions WHERE channel_id=?", (channel_id,)
        )
        rows = await cur.fetchall()
        await cur.close()
        return [r[0] for r in rows]

# ─────── Mentionable-select View ──────────────────────────────────────
class PingSelectView(discord.ui.View):
    """Ephemeral view to pick users/roles to ping."""

    def __init__(self, url: str, channel_id: int, owner_id: int,
                 preset: Optional[List[int]] = None):
        super().__init__(timeout=120)
        self.url = url
        self.ch_id = channel_id
        self.owner_id = owner_id

        select = discord.ui.MentionableSelect(
            placeholder="Select members / roles",
            min_values=1, max_values=25,
        )
        select.callback = self.on_finish
        self.add_item(select)

    async def on_finish(self, interaction: discord.Interaction):
        sel: discord.ui.MentionableSelect = self.children[0]
        ids = [v.id for v in sel.values if hasattr(v, "id")]
        last_id, *_ = await db_get(self.url, self.ch_id) or ("-",)
        await db_upsert(self.url, self.ch_id, last_id, ids, self.owner_id)
        await interaction.response.edit_message(
            content="✅ Saved: " + " ".join(f"<@{i}>" for i in ids),
            view=None
        )

# ─────── /track Command ───────────────────────────────────────────────
@bot.tree.command(description="Track a series and pick who to ping")
@app_commands.describe(
    url="Series URL (Corona-ex, Walker, Gardo, or Manga-Up)",
    channel="Channel where updates will be posted"
)
async def track(inter: discord.Interaction, url: str, channel: discord.TextChannel):
    try:
        chap_id, *_ = await get_latest(url)
    except Exception as e:
        return await inter.response.send_message(f"❌ `{e}`", ephemeral=True)

    # Save new subscription with no pings yet
    await db_upsert(url, channel.id, chap_id, [], inter.user.id)

    # Prompt the user to choose members/roles to ping
    await inter.response.send_message(
        "Pick who to mention on new chapters:",
        view=PingSelectView(url, channel.id, inter.user.id),
        ephemeral=True
    )

# ─────── /updatemembers Command ───────────────────────────────────────
@bot.tree.command(description="Edit ping list for a tracked channel")
async def updatemembers(inter: discord.Interaction,
                        channel: discord.TextChannel):
    urls = await db_urls_for_channel(channel.id)
    if not urls:
        return await inter.response.send_message(
            "❌ No subscriptions in that channel.", ephemeral=True
        )

    async def send_picker(series_url: str):
        row = await db_get(series_url, channel.id)
        preset = [int(x) for x in row[1].split(",")] if row and row[1] else []
        await inter.response.send_message(
            f"Edit mentions for {series_url}:",
            view=PingSelectView(series_url, channel.id,
                                inter.user.id, preset),
            ephemeral=True
        )

    if len(urls) == 1:
        return await send_picker(urls[0])

    sel = discord.ui.Select(
        placeholder="Select series to edit",
        options=[discord.SelectOption(label=u, value=u) for u in urls]
    )
    async def choose(i2: discord.Interaction):
        await send_picker(sel.values[0])
    sel.callback = choose
    view = discord.ui.View(timeout=60)
    view.add_item(sel)
    await inter.response.send_message(
        "Choose series to edit:", view=view, ephemeral=True
    )

# ─────── /latest Command ──────────────────────────────────────────────
@bot.tree.command(description="Show the latest chapter tracked in a channel")
async def latest(inter: discord.Interaction, channel: discord.TextChannel):
    urls = await db_urls_for_channel(channel.id)
    if not urls:
        return await inter.response.send_message(
            "❌ No series tracked in that channel.", ephemeral=True
        )

    series_url = urls[0]
    await inter.response.defer(ephemeral=True, thinking=True)
    try:
        chap_id, title, link = await get_latest(series_url)
    except Exception as e:
        return await inter.followup.send(f"❌ `{e}`", ephemeral=True)

    embed = discord.Embed(
        title=title,
        url=link,
        description=f"Chapter ID `{chap_id}`",
        colour=0x2ecc71
    )
    await inter.followup.send(embed=embed, ephemeral=True)

# ─────── Background Poller ────────────────────────────────────────────
@tasks.loop(minutes=15)
async def poll():
    rows = await db_rows()
    for url, ch_id, last_id, ping_csv in rows:
        try:
            new_id, title, link = await get_latest(url)
        except Exception as e:
            logging.warning("%s → %s", url, e)
            continue
        if new_id == last_id:
            continue
        mentions = " ".join(f"<@{i}>" for i in ping_csv.split(",") if i)
        ch = bot.get_channel(ch_id)
        if ch:
            try:
                await ch.send(f"{mentions}\n**New chapter:** {title}\n{link}")
            except discord.Forbidden:
                logging.warning("Missing perms in #%s", ch_id)
        await db_upsert(url, ch_id, new_id, ping_csv.split(","), owner_id=0)

# ─────── Run the Bot ───────────────────────────────────────────────────
@bot.event
async def on_ready():
    await bot.tree.sync()
    logging.info("Logged in as %s", bot.user)

async def main():
    await db_init()
    poll.start()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
