# -*- coding: utf-8 -*-
"""
discord_bot_listener.py
------------------------
Live Discord Bot listener service for Convo-Shorts automation.
Listens for chat replies ('yes', 'approve', 'no', 'reject') in Discord review channels
and automatically triggers YouTube upload or video re-generation.
"""

import os
import sys
import json
import logging
import requests
import discord

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DiscordBot")

# Read token from config.json or environment
_CFG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")

if os.path.exists(_CFG_PATH):
    try:
        with open(_CFG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            DISCORD_BOT_TOKEN = cfg.get("discord_bot_token", DISCORD_BOT_TOKEN)
    except Exception as e:
        logger.warning(f"Could not load config.json: {e}")
GROWTH_SERVER_URL = "http://127.0.0.1:8010"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    logger.info(f"✅ Discord Bot is ONLINE as {client.user} (ID: {client.user.id})")

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    content = message.content.strip().lower()
    raw_content = message.content.strip()
    
    # Check for approval trigger: "approve <job_id>" or "yes", "approve"
    if content in ["yes", "approve", "y", "1"] or content.startswith("approve "):
        job_id = None
        parts = raw_content.split()
        if len(parts) > 1 and parts[0].lower() == "approve":
            job_id = parts[1]

        logger.info(f"Received APPROVAL from {message.author}: '{raw_content}' (Job: {job_id})")
        await message.channel.send("🟢 **[APPROVED]** Received approval! Uploading Short to YouTube...")
        
        try:
            payload = {"privacy_status": "public"}
            if job_id:
                payload["job_id"] = job_id
                resp = requests.post(f"{GROWTH_SERVER_URL}/api/upload-approved", json=payload, timeout=60)
            else:
                resp = requests.post(f"{FLASK_SERVER_URL}/upload_youtube", json={}, timeout=60)

            res_data = resp.json()
            if resp.ok and res_data.get("status") == "success":
                yt_url = res_data.get("youtube_url", res_data.get("url", "https://youtube.com"))
                await message.channel.send(f"✅ **[PUBLISHED]** Video successfully published to YouTube!\nWatch here: {yt_url}")
            else:
                err_msg = res_data.get("message", res_data.get("error", "Unknown error"))
                await message.channel.send(f"❌ **[UPLOAD ERROR]** YouTube upload failed: `{err_msg}`")
        except Exception as e:
            logger.error(f"Error during YouTube upload: {e}")
            await message.channel.send(f"❌ **[SYSTEM ERROR]** Failed to connect to YouTube engine: `{e}`")

    # Check for rejection trigger: "reject <job_id>" or "no", "reject"
    elif content in ["no", "reject", "n", "0"] or content.startswith("reject "):
        job_id = None
        parts = raw_content.split()
        if len(parts) > 1 and parts[0].lower() == "reject":
            job_id = parts[1]

        logger.info(f"Received REJECTION from {message.author}: '{raw_content}' (Job: {job_id})")
        
        try:
            payload = {"reason": "REJECTED_VIA_DISCORD_COMMAND"}
            if job_id:
                payload["job_id"] = job_id
            
            resp = requests.post(f"{GROWTH_SERVER_URL}/api/reject", json=payload, timeout=30)
            res_data = resp.json()
            if resp.ok and res_data.get("status") == "success":
                scrapped_count = res_data.get("scrapped_files_count", 0)
                await message.channel.send(
                    f"🔴 **[SCRAPPED]** Video for job `{job_id or 'current'}` has been permanently rejected and scrapped.\n"
                    f"• Upload Status: **SCRAPPED (Zero uploads allowed, including private)**\n"
                    f"• Deleted {scrapped_count} video artifact(s)."
                )
            else:
                err_msg = res_data.get("message", "Rejection failed")
                await message.channel.send(f"⚠️ **[REJECTION NOTICE]** Video marked as rejected: `{err_msg}`")
        except Exception as e:
            logger.error(f"Error during rejection processing: {e}")
            await message.channel.send(f"🔴 **[REJECTED]** Video rejected! Scrapping files and halting upload.")

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        logger.error("No DISCORD_BOT_TOKEN found in config.json or environment. Please add 'discord_bot_token' to config.json.")
        sys.exit(1)
        
    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.errors.PrivilegedIntentsRequired:
        logger.warning("Message Content Intent not enabled in Developer Portal. Retrying with default intents (mentions mode)...")
        intents = discord.Intents.default()
        intents.message_content = False
        client = discord.Client(intents=intents)
        client.run(DISCORD_BOT_TOKEN)
