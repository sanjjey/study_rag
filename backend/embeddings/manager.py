from langchain_huggingface import HuggingFaceEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()

class EmbeddingManager:
    def __init__(self):
        model_name = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-base-en-v1.5")
        encode_kwargs = {'normalize_embeddings': True}
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'}, # Can be changed to 'cuda' if GPU available
            encode_kwargs=encode_kwargs
        )

    def get_embeddings(self):
        return self.embeddings
