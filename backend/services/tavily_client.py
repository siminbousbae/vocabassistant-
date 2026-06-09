"""
Tavily Search API client for the Vocabulary Assistant.
Searches real English news sources for authentic example sentences.
"""

import re
from typing import List, Dict, Any, Optional
from tavily import TavilyClient
from backend.config import settings


class TavilySearchClient:
    """Client for Tavily search API - finds real news articles with target words."""

    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.client = TavilyClient(api_key=self.api_key)
        self.trusted_domains = settings.TRUSTED_DOMAINS

    def search_articles(self, word: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for news articles containing the target word.
        Returns list of articles with title, url, content, source.
        """
        try:
            # Build search query to find articles with the word
            query = f'"{word}" news article recent'

            response = self.client.search(
                query=query,
                search_depth="advanced",
                include_domains=self.trusted_domains,
                max_results=max_results,
                include_answer=False,
                include_raw_content=True  # Get full article content
            )

            results = []
            for result in response.get("results", []):
                article = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "raw_content": result.get("raw_content", ""),
                    "source": self._extract_domain(result.get("url", "")),
                    "score": result.get("score", 0)
                }
                results.append(article)

            return results

        except Exception as e:
            print(f"Tavily search failed: {e}")
            return []

    def extract_sentences_with_word(self, word: str, text: str, max_sentences: int = 3) -> List[str]:
        """
        Extract sentences containing the target word from article text.
        Uses regex to find natural sentence boundaries.
        """
        if not text:
            return []

        # Clean text
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = re.sub(r'\s+', ' ', text)

        # Split into sentences (basic approach)
        # More robust than simple split on '.' to handle abbreviations
        sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
        sentences = re.split(sentence_pattern, text)

        # Find sentences containing the word (case-insensitive, whole word)
        word_pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
        matching_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip too short sentences
                continue
            if len(sentence) > 300:  # Skip too long sentences
                continue
            if word_pattern.search(sentence):
                matching_sentences.append(sentence)

        return matching_sentences[:max_sentences]

    def get_best_example(self, word: str) -> Dict[str, Any]:
        """
        Full pipeline: search articles -> extract sentences -> return best one.
        Returns dict with: sentence, source_name, source_url
        """
        # Step 1: Search for articles
        articles = self.search_articles(word, max_results=5)

        if not articles:
            return {
                "sentence": "",
                "source_name": "",
                "source_url": "",
                "error": "No articles found"
            }

        # Step 2: Extract sentences from all articles
        all_sentences = []
        for article in articles:
            # Try raw_content first, fallback to content
            text = article.get("raw_content", "") or article.get("content", "")
            sentences = self.extract_sentences_with_word(word, text, max_sentences=2)

            for sentence in sentences:
                all_sentences.append({
                    "sentence": sentence,
                    "source_name": article["source"],
                    "source_url": article["url"],
                    "article_title": article["title"]
                })

        if not all_sentences:
            return {
                "sentence": "",
                "source_name": "",
                "source_url": "",
                "error": "No sentences found in articles"
            }

        # Step 3: Return the first good sentence (could be enhanced with LLM filtering)
        # For now, return the one from highest-scoring article
        best = all_sentences[0]
        return {
            "sentence": best["sentence"],
            "source_name": best["source_name"],
            "source_url": best["source_url"],
            "article_title": best["article_title"]
        }

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL for source attribution."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain
        except:
            return "Unknown Source"

    def verify_url_accessible(self, url: str) -> bool:
        """Check if a URL is accessible."""
        try:
            import requests
            response = requests.head(url, timeout=5, allow_redirects=True)
            return response.status_code == 200
        except:
            return False


# Global instance
tavily_search_client = TavilySearchClient()
