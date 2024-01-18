from starlette.config import Config
from dotenv import load_dotenv , dotenv_values
env = dotenv_values('.env', encoding='utf-8')
def getAPIkey():
    return env.get('OPENAI_API_KEY')
def getModel():
    return env.get('MODEL')
def geturl():
    return env.get('dburl')
load_dotenv()
