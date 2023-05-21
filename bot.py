import asyncio
import logging
import os
import shutil
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from util.db import DbManager

load_dotenv()
TEMP = "temp"
STATUS = os.getenv("BOT_STATUS")
FILE_DIR = os.getenv("FILE_DIR")
SETTING_VALS = {"_id", "description", "value"}


class Eindjeboss(commands.Bot):

    def __init__(self) -> None:
        intents = discord.Intents.all()
        activity = discord.Activity(
            type=discord.ActivityType.listening, detail="", name=STATUS)
        super().__init__(command_prefix="!", case_insensitive=True,
                         intents=intents, activity=activity,
                         owner_id=os.getenv('RAGDOLL_ID'))

    async def setup_hook(self):
        if hasattr(time, 'tzset'):
            os.environ['TZ'] = 'Europe/Amsterdam'
            time.tzset()

        if os.path.exists(TEMP) and os.path.isdir(TEMP):
            shutil.rmtree(TEMP)
        shutil.copytree("default_files", FILE_DIR, dirs_exist_ok=True)

        self.dbmanager = DbManager()
        await self.load_extensions()
        await self.load_settings()
        await self.tree.sync()

    async def load_extensions(self):
        for filename in os.listdir("./cogs"):
            if not filename.endswith('py'):
                continue
            extension_name = f"cogs.{filename[:-3]}"
            logging.info(f"Loading extension: {extension_name}")
            await self.load_extension(extension_name)
        logging.info("Finished loading extensions")

    async def load_settings(self):
        settings = await self.settings.find({}).to_list(length=88675309)
        for setting in settings:
            self.__setattr__(setting["_id"], setting["value"])
        logging.info("Finished loadings settings")

    async def add_setting(self, setting):
        if setting.keys() != SETTING_VALS:
            raise ValueError(
                f"Setting {setting} does not match expected fields")

        self.__setattr__(setting["_id"], setting["value"])
        self.settings.insert_one(setting)
        logging.info("Added setting %s with value %s", setting["_id"],
                     setting["value"])

    async def update_setting(self, setting):
        settings = await self.settings.find({}).to_list(length=88675309)

        if not any([st["_id"] == setting["_id"] for st in settings]):
            raise ValueError(
                f"Setting {setting} not found. Create it with /createsetting")

        old_val = self.__getattribute__(setting["_id"])
        self.__setattr__(setting["_id"], setting["value"])
        await self.settings.update_one({"_id": setting["_id"]},
                                       {"$set": {"value": setting["value"]}})
        logging.info("Updated setting %s with value %s (was %s)",
                     setting["_id"], setting["value"], old_val)
        return old_val

    async def get_settings(self):
        settings = await self.settings.find({}).to_list(length=88675309)
        return settings


async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")

    logging_file_name = f"{FILE_DIR}/logs/eindjeboss.log"

    if not Path(logging_file_name).is_file():
        open(logging_file_name, 'a').close()

    log_format = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s',
                                   datefmt='%Y-%m-%d %H:%M:%S')
    log_handler = RotatingFileHandler(logging_file_name, mode='a',
                                      maxBytes=5*1024*1024, backupCount=10,
                                      encoding=None, delay=0)

    discord.utils.setup_logging(handler=log_handler, formatter=log_format)

    client = Eindjeboss()

    @client.event
    async def on_ready():
        print(f"{client.user.name} is ready to serve.")

    async with client:
        await client.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Powering down...")
