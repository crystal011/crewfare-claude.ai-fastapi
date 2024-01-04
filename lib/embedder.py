from .types import Embedding, Embedder
from tenacity import retry, wait_exponential, stop_after_attempt
from openai import OpenAI

############################################
# OpenAI Embedder implementations
############################################

class OpenAIEmbedder(Embedder):

    def __init__(self, api_key: str, model_name: str):

        self.api_key = api_key
        self.model_name = model_name
        self.dim = 1536
        self.client = OpenAI(api_key=api_key)

    def embed(self, text: str) -> Embedding:
        emb = self.embed_batch([text])
        return emb[0]
    
    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(10))
    def embed_batch(self, texts: list[str]) -> list[Embedding]:
        embeddings = []
        for text in texts:
            embedding = self.client.embeddings.create(input=text, model=self.model_name).data[0].embedding
            embeddings.append(embedding)

        return [Embedding(embedding=embedding, text=text) for embedding, text in zip(embeddings, texts)]
