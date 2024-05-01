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

import pinecone
from lib.vectorstore import PineconeVectorStore
from lib.embedder import OpenAIEmbedder
from lib.db import export_data_from_mysql
from lib.utils import embed_and_upload

############################################
# Knowledgebase Service Implementations
############################################

pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
if PINECONE_DATABASE not in pinecone.list_indexes():
    logger.info("No remote vectorstore found. Creating new index and filling it from local text files.")

    batch_size = 128
    query = "data/query.sql"

    export_data_from_mysql(query, 'data/event.jsonl', config)

    embedder = OpenAIEmbedder(OPENAI_KEY, EMBEDDING_MODEL)

    pinecone.create_index(PINECONE_DATABASE, dimension=1536, metric="cosine")
    vector_store = PineconeVectorStore(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT, index=PINECONE_DATABASE)
    embed_and_upload('data/event.jsonl', vector_store, embedder=embedder, batch_size=batch_size)
    ########## Delete the three lines above and uncomment the lines below to use hybrid vector stores. ##########
    # pinecone.create_index(PINECONE_DATABASE, dimension=768, metric="dotproduct") # Pinecone only supports hybrid retrieval with dotproduct
    # vector_store = PineconeHybridVectorStore(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT, index=PINECONE_DATABASE)
    # embedder = LocalHybridEmbedder(DEFAULT_EMBEDDER, DEFAULT_SPARSE_EMBEDDER)
    # embed_and_upload(input_file=input_file, vectorstore=vector_store, embedder=embedder, batch_size=batch_size)
else:
    vector_store = PineconeVectorStore(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT, index=PINECONE_DATABASE)
    ########## Delete the line above and uncomment the line below to use hybrid vector stores. ##########
    # vector_store = PineconeHybridVectorStore(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT, index=PINECONE_DATABASE)

export_data_from_mysql("data/query.sql", 'data/event.jsonl', config)