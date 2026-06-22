# API keys and global configs

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4o-mini"

DB_PATH = 'data/askdata.db' 
CHROMA_PATH = "chroma_db"