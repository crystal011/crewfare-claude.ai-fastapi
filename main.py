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
ANTHROPIC_SEARCH_MODEL = os.environ['ANTHROPIC_SEARCH_MODEL']

import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

import anthropic
from lib.embedder import OpenAIEmbedder
from lib.vectorstore import PineconeVectorStore
from lib.searchtools import EmbeddingSearchTool
from lib.chat_core import CrewfareChat
import time
import random
import hashlib
from search.bot import Assistant

search = Assistant()

CORS_ALLOW_ORIGINS = os.environ.get("CORS_ALLOW_ORIGINS", "*")

def generate_unique_number():
    timestamp = str(time.time())
    random_number = str(random.randint(1, 1000))
    data = timestamp + random_number
    
    hash_object = hashlib.sha256(data.encode())
    unique_id = hash_object.hexdigest()
    
    return unique_id + timestamp

vector_store = PineconeVectorStore(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT, index=PINECONE_DATABASE)
EVENT_SEARCH_TOOL_DESCRIPTION = 'The search engine will search over the Crewfare Event database, and return for each event its name, location, dates, end date, description, url'
embedder = OpenAIEmbedder(OPENAI_KEY, EMBEDDING_MODEL)
event_search_tool = EmbeddingSearchTool(tool_description=EVENT_SEARCH_TOOL_DESCRIPTION, vector_store = vector_store, embedder=embedder)
ai_engine = CrewfareChat(api_key=os.environ['ANTHROPIC_API_KEY'], search_tool = event_search_tool, verbose = False)

user_bots = {}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def welcome():
    return {"message": "Welcome crewfare"}
    
@app.get("/query/")
async def searchapi(q: str = Query(None, alias="search")):
    logger.info(q)
    if q:
        # relevant_search_results = ai_engine.search(
        #     query=q,
        #     stop_sequences=[anthropic.HUMAN_PROMPT, 'END_OF_SEARCH'],
        #     model=ANTHROPIC_SEARCH_MODEL,
        #     n_search_results_to_use=20,
        #     max_searches_to_try=1,
        #     max_tokens_to_sample=1000,
        #     score=0.8
        # )

        # relevant_search_results = search.run(q)

        relevant_search_results = search.run(q)
        print(relevant_search_results)

        return {"message": relevant_search_results}
    else:
        return {"message": "No query provided."}

@app.get("/chat/")
async def chatapi(q: str = Query(None, alias="q"), token: str = Query(None, alias="chatHistory")):
    logger.info(q)
    logger.info(token)
    if q:
        if token is None or token == '':    # New user on website
            token = generate_unique_number()
        elif time.time() - float(token[64:]) > 600:   # Expire session time
            del user_bots[token[:64]]
            token = generate_unique_number()
        else:
            token = token[:64] + str(time.time())
        client = user_bots.get(token[:64], CrewfareChat(api_key=os.environ['ANTHROPIC_API_KEY'], search_tool = event_search_tool, verbose = False))
        user_bots[token[:64]] = client
        response = StreamingResponse(
            client.completion_with_retrieval(
                query=q,
                stop_sequences=[anthropic.HUMAN_PROMPT, 'END_OF_SEARCH'],
                model=ANTHROPIC_SEARCH_MODEL,
                n_search_results_to_use=5,
                max_searches_to_try=1,
                max_tokens_to_sample=1000),
            media_type="text/event-stream",
            headers={ 'X-Chat-History': token }
        )

        return response
    else:
        return {"message": "No query provided."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0")
