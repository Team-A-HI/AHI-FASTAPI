from starlette.config import Config
from dotenv import load_dotenv
env = Config(".env")
load_dotenv()
def getAPIkey():
    return env('OPENAI_API_KEY')
def getModel():
    return env('MODEL')

def geturl():
    return env('dburl')
