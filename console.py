import os
import sys
import logging
import dotenv

dotenv.load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create a handler to log to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_ENVIRONMENT = os.environ["PINECONE_ENVIRONMENT"]
PINECONE_DATABASE = os.environ["PINECONE_DATABASE"]
OPENAI_KEY = os.environ["OPENAI_KEY"]
EMBEDDING_MODEL = os.environ["EMBEDDING_MODEL"]
config = {
  'user': os.environ["USER_NAME"],
  'password': os.environ["PASSWORD"],
  'host': os.environ["HOST"],
  'database': os.environ["DATABASE_NAME"],
  'raise_on_warnings': True
}

import anthropic
from lib.searchtools import EmbeddingSearchTool
from lib.vectorstore import PineconeVectorStore
from lib.embedder import OpenAIEmbedder
from lib.chat_core import CrewfareChat

vector_store = PineconeVectorStore(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT, index=PINECONE_DATABASE)
EVENT_SEARCH_TOOL_DESCRIPTION = 'The search engine will search over the Crewfare Event database, and return for each event its name, location, dates, end date, and a set of tags.'
embedder = OpenAIEmbedder(OPENAI_KEY, EMBEDDING_MODEL)
event_search_tool = EmbeddingSearchTool(tool_description=EVENT_SEARCH_TOOL_DESCRIPTION, vector_store = vector_store, embedder=embedder)
ANTHROPIC_SEARCH_MODEL = os.environ['ANTHROPIC_SEARCH_MODEL']
client = CrewfareChat(api_key=os.environ['ANTHROPIC_API_KEY'], search_tool = event_search_tool, verbose=False)

def format_content(content):
    titles = content.split("\n\n")
   
    return {title.strip().split(': ')[0]: title.split(': ')[1] for title in titles}

while True:
    query = input('USER: ')
    relevant_search_results = client.completion_with_retrieval(
        query=query,
        stop_sequences=[anthropic.HUMAN_PROMPT, 'END_OF_SEARCH'],
        model=ANTHROPIC_SEARCH_MODEL,
        n_search_results_to_use=10,
        max_searches_to_try=5,
        max_tokens_to_sample=1000)

    print(relevant_search_results)
