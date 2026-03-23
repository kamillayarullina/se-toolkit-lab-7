import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env.bot.secret'), override=True)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env.bot.example'), override=False)

BOT_TOKEN = os.getenv('BOT_TOKEN')
LMS_API_BASE_URL = os.getenv('LMS_API_BASE_URL')
LMS_API_KEY = os.getenv('LMS_API_KEY')
LLM_API_KEY = os.getenv('LLM_API_KEY')