import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = {int(x) for x in os.getenv("ADMINS", "").split(",") if x}
MAX_PLAYERS = int(os.getenv("MAX_PLAYERS", "15"))
DB_PATH = os.getenv("DB_PATH", "river_team.db")
