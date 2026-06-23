# extract keywords from user query for schema retrieval

# ============================================================
# DEV: rule-based keyword extraction (free, no API calls)
# PROD: swap for LLM-based extraction when ready
# ============================================================

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from typing import List
import re
from config import LLM_PROVIDER, LLM_MODEL, OPENAI_API_KEY

STOPWORDS = {
    "what", "which", "who", "how", "many", "much", "is", "are",
    "the", "a", "an", "of", "in", "for", "to", "and", "or",
    "by", "with", "from", "that", "show", "me", "find", "get",
    "list", "give", "tell", "all", "each", "per", "have", "has",
    "where", "when", "than", "more", "than", "top", "between"
}

"""
DEV: rule-based keyword extractor.
Splits query into words, removes stopwords and short tokens.
Similar to retrieval logic with API calls.
"""
def extract_keywords_local(query: str) -> List[str]:
    # lowercase and split on spaces/punc
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", query.lower())

    keywords = []
    for token in tokens:
        if token not in STOPWORDS and len(token) > 2:
            keywords.append(token)

    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            unique.append(kw)
    
    return unique

# ============================================================
# PROD: LLM-based extraction (better to comment out when using DEV)
# ============================================================
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

def get_llm():
    if LLM_PROVIDER == "openai":
        return ChatOpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY, temperature=0)
    
def parse_llm_output(text: str) -> List[str]:
    text = text.strip()
    for prefix in ["Result:", "Parsed Result: "]:
        if text.startswith(prefix):
            text = text.replace(prefix, "", 1)
    text = text.replace(", ", ",")

    res = []
    items = text.split(",")

    for i in items:
        # remove leading and trailing spaces
        cleaned = i.strip()
        # and filter empty string
        if cleaned:
            res.append(cleaned)

    return res

async def extract_keywords_llm(query: str) -> List[str]:
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(
        """
        Extract core database field names and business concepts from this query.
        Output format: Result: <keyword1>, <keyword2>
        Query: {query}
        """
    )
    chain = prompt | llm
    res = await chain.ainvoke({"query": query})
    return parse_llm_output(res.content)

"""
This is the main entry point.
DEV: calls rule-base extractor
PROD: swap with commented line
"""
def extract_keywords(query: str) -> List[str]:
    # return await extract_keywords_llm(query)
    return extract_keywords_local(query)

if __name__ == "__main__":
    test_queries = [
        "What is the total trade count for each user?",
        "Which users have interest rate higher than 3.5?",
        "Show me user age and trade summary",
    ]
    for q in test_queries:
        keywords = extract_keywords(q)
        print(f"Query:    {q}")
        print(f"Keywords: {keywords}")
        print()




