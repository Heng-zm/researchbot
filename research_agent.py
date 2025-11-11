"""
AI Research Agent - Powerful internet research tool with AI analysis
"""
import os
import json
import random
from typing import List, Dict, Optional, Callable
from datetime import datetime
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
import time
from newspaper import Article
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class WebScraper:
    """Enhanced web scraper for extracting content from URLs"""
    
    def __init__(self, timeout: int = 10):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def scrape_url(self, url: str) -> Dict:
        """Scrape content from a URL with improved error handling"""
        if not url or not url.startswith(('http://', 'https://')):
            return {'url': url, 'error': 'Invalid URL', 'success': False}
        
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            # Validate that we got meaningful content
            if not article.text or len(article.text.strip()) < 50:
                raise ValueError("Insufficient content extracted")
            
            return {
                'url': url,
                'title': article.title or 'Untitled',
                'text': article.text[:10000],  # Limit to 10KB
                'authors': article.authors,
                'publish_date': str(article.publish_date) if article.publish_date else None,
                'success': True
            }
        except Exception as e:
            logging.debug(f"Article extraction failed for {url}: {e}")
            # Fallback to basic scraping
            try:
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Remove script, style, and other unwanted elements
                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()
                
                # Try to find main content
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.body
                if main_content:
                    text = main_content.get_text(separator=' ', strip=True)
                else:
                    text = soup.get_text(separator=' ', strip=True)
                
                # Clean up whitespace
                text = ' '.join(text.split())
                
                if len(text.strip()) < 50:
                    raise ValueError("Insufficient content")
                
                return {
                    'url': url,
                    'title': soup.title.string if soup.title else 'Untitled',
                    'text': text[:10000],  # Limit to 10KB
                    'success': True
                }
            except Exception as fallback_error:
                logging.warning(f"Failed to scrape {url}: {fallback_error}")
                return {
                    'url': url,
                    'error': str(fallback_error),
                    'success': False
                }


class SearchEngine:
    """Web search engine using Google Custom Search API or DuckDuckGo fallback"""
    
    def __init__(self, preferred_engine: str = "auto"):
        """
        Initialize search engine
        
        Args:
            preferred_engine: 'google', 'duckduckgo', or 'auto' (tries Google first, falls back to DuckDuckGo)
        """
        self._ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        # Google Custom Search API credentials
        self.google_api_key = os.environ.get("GOOGLE_API_KEY")
        self.google_cse_id = os.environ.get("GOOGLE_CSE_ID")
        self.preferred_engine = preferred_engine.lower()
        
        # Rotate between available backends to mitigate per-endpoint throttling
        self._backends_cycle = ["api", "html", "lite"]
        self._backend_idx = 0
        self.ddgs = self._make_ddgs()
    
    def set_preferred_engine(self, engine: str) -> None:
        """Set preferred search engine: 'google', 'duckduckgo', or 'auto'"""
        self.preferred_engine = engine.lower()
        logging.info(f"Search engine preference set to: {self.preferred_engine}")
    
    def _make_ddgs(self) -> DDGS:
        """Create a DDGS client with headers, optional proxies, and higher timeout."""
        proxies = {}
        http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy
        headers = {"User-Agent": self._ua}
        # timeout=20 to be a bit more lenient on slow responses
        return DDGS(headers=headers, proxies=proxies or None, timeout=20)
    
    def _retry_backoff(self, attempt: int) -> None:
        """Exponential backoff with jitter for rate limiting"""
        base = min(16, 2 ** attempt)  # Cap at 16 seconds instead of 32
        jitter = random.uniform(-0.5, 0.5)
        sleep_time = max(1, base + jitter)
        logging.info(f"Rate limited, backing off for {sleep_time:.1f}s")
        time.sleep(sleep_time)
    
    def _search_google(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search using Google Custom Search API with error handling"""
        if not self.google_api_key or not self.google_cse_id:
            return []  # Fall back to DuckDuckGo
        
        # Skip if CSE ID is placeholder
        if 'your_custom_search_engine_id' in self.google_cse_id.lower():
            logging.info("Google CSE ID not configured, using DuckDuckGo")
            return []
        
        try:
            results = []
            # Google Custom Search API returns max 10 results per request
            num_requests = min((max_results + 9) // 10, 3)  # Limit to 3 requests max
            
            for i in range(num_requests):
                start_index = i * 10 + 1
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': self.google_api_key,
                    'cx': self.google_cse_id,
                    'q': query,
                    'start': start_index,
                    'num': min(10, max_results - len(results))
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                items = data.get('items', [])
                if not items:
                    break
                    
                for item in items:
                    results.append({
                        'title': item.get('title', 'Untitled'),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                    })
                
                if len(results) >= max_results:
                    break
            
            logging.info(f"Google search returned {len(results)} results")
            return results[:max_results]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logging.warning("Google API rate limit exceeded")
            else:
                logging.error(f"Google Search HTTP error: {e}")
            return []  # Fall back to DuckDuckGo
        except Exception as e:
            logging.error(f"Google Search error: {e}")
            return []  # Fall back to DuckDuckGo
    
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search the web using preferred engine or fallback."""
        # Force DuckDuckGo if explicitly set
        if self.preferred_engine == "duckduckgo":
            logging.info("Using DuckDuckGo (user preference)")
            return self._search_duckduckgo(query, max_results)
        
        # Force Google if explicitly set
        if self.preferred_engine == "google":
            if self.google_api_key and self.google_cse_id:
                logging.info("Using Google (user preference)")
                google_results = self._search_google(query, max_results)
                if google_results:
                    return google_results
                # If Google fails, fall back to DuckDuckGo
                logging.warning("Google search failed, falling back to DuckDuckGo")
            else:
                logging.warning("Google not configured, using DuckDuckGo")
            return self._search_duckduckgo(query, max_results)
        
        # Auto mode: Try Google first if configured, then fall back to DuckDuckGo
        if self.google_api_key and self.google_cse_id:
            google_results = self._search_google(query, max_results)
            if google_results:
                return google_results
        
        # Fall back to DuckDuckGo
        return self._search_duckduckgo(query, max_results)
    
    def _search_duckduckgo(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search using DuckDuckGo with retry logic."""
        logging.info("Using DuckDuckGo search")
        from duckduckgo_search.exceptions import DuckDuckGoSearchException
        # Cap results to avoid triggering aggressive rate-limits
        max_results = max(1, min(max_results, 20))
        last_error: Optional[Exception] = None
        for attempt in range(5):
            try:
                backend = self._backends_cycle[self._backend_idx % len(self._backends_cycle)]
                results_raw = self.ddgs.text(
                    query,
                    max_results=max_results,
                    backend=backend,
                    safesearch="moderate",
                    region="wt-wt",
                ) or []
                results: List[Dict] = []
                for r in results_raw:
                    results.append({
                        'title': r.get('title', ''),
                        'url': r.get('href', '') or r.get('url', ''),
                        'snippet': r.get('body', '') or r.get('snippet', ''),
                    })
                return results
            except DuckDuckGoSearchException as e:
                last_error = e
                # If it's a rate limit, backoff and recreate the client
                if "Ratelimit" in str(e) or "429" in str(e):
                    # Switch backend to try a different endpoint
                    self._backend_idx = (self._backend_idx + 1) % len(self._backends_cycle)
                    self.ddgs = self._make_ddgs()
                    if attempt < 4:
                        self._retry_backoff(attempt)
                        continue
                # Non-rate-limit DDG errors: recreate once and retry
                self.ddgs = self._make_ddgs()
                if attempt < 4:
                    time.sleep(1)  # Shorter backoff for non-rate-limit errors
                    continue
            except Exception as e:
                last_error = e
                logging.debug(f"Search attempt {attempt + 1} failed: {e}")
                # Generic network error: recreate and retry
                self.ddgs = self._make_ddgs()
                if attempt < 4:
                    time.sleep(1)
                    continue
        # Exhausted retries: return empty and let caller show a friendly message
        logging.error(f"Search failed after retries: {last_error}")
        return []
    
    def news_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for news articles with retries on DuckDuckGo rate limits."""
        from duckduckgo_search.exceptions import DuckDuckGoSearchException
        max_results = max(1, min(max_results, 20))
        last_error: Optional[Exception] = None
        for attempt in range(5):
            try:
                results_raw = self.ddgs.news(
                    query,
                    max_results=max_results,
                    safesearch="moderate",
                    region="wt-wt",
                ) or []
                results: List[Dict] = []
                for r in results_raw:
                    results.append({
                        'title': r.get('title', ''),
                        'url': r.get('url', ''),
                        'snippet': r.get('body', '') or r.get('snippet', ''),
                        'date': r.get('date', ''),
                        'source': r.get('source', ''),
                    })
                return results
            except DuckDuckGoSearchException as e:
                last_error = e
                if "Ratelimit" in str(e) or "429" in str(e):
                    # Try switching text backend as a fallback if news keeps failing
                    self.ddgs = self._make_ddgs()
                    if attempt < 4:
                        self._retry_backoff(attempt)
                        continue
                self.ddgs = self._make_ddgs()
                if attempt < 4:
                    self._retry_backoff(attempt)
                    continue
            except Exception as e:
                last_error = e
                self.ddgs = self._make_ddgs()
                if attempt < 4:
                    self._retry_backoff(attempt)
                    continue
        logging.error(f"News search failed after retries: {last_error}")
        # Fallback: attempt a generic text search for recent results if news fails completely
        try:
            logging.info("Falling back to standard search for news")
            generic = self.search(f"{query} news", max_results=max_results)
            return generic
        except Exception as e:
            logging.error(f"News fallback search also failed: {e}")
            return []


class AIResearchAgent:
    """Main AI research agent coordinating search and analysis"""
    
    def __init__(self, use_ai: bool = True, ai_backend: str = 'ollama', search_engine: str = 'auto'):
        self.search_engine = SearchEngine(preferred_engine=search_engine)
        self.scraper = WebScraper()
        self.use_ai = use_ai
        self.ai_backend = ai_backend  # 'ollama' or 'transformers'
        self.research_history = []
    
    def set_search_engine(self, engine: str) -> None:
        """Set preferred search engine: 'google', 'duckduckgo', or 'auto'"""
        self.search_engine.set_preferred_engine(engine)
    
    def research(
        self,
        query: str,
        depth: str = 'standard',
        max_sources: int = 5,
        news: bool = False,
        page: int = 0,
        per_page: Optional[int] = None,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> Dict:
        """
        Conduct research on a topic
        
        Args:
            query: Research question or topic
            depth: 'quick' (search only), 'standard' (search + scrape), 'deep' (search + scrape + analysis)
            max_sources: Maximum number of sources to scrape (legacy). If per_page is None, this is used per page.
            news: Use news search instead of general web search
            page: Zero-based page index for pagination of search results & scraping
            per_page: Items per page (defaults to max_sources)
        """
        print(f"\n🔍 Researching: {query}")
        if progress_cb:
            progress_cb(f"Researching: {query}")
        
        # Resolve pagination sizing
        per_page = per_page or max_sources or 5
        page = max(0, int(page))
        start = page * per_page
        # Fetch a generous window so we can tell if a next page exists.
        # SearchEngine caps to 20 internally to reduce rate limits.
        fetch_n = max(per_page * (page + 2), per_page * 3)
        
        # Step 1: Web search
        step_msg = "Searching the news..." if news else "Searching the web..."
        print("📡 " + step_msg)
        if progress_cb:
            progress_cb(step_msg)
        if news:
            all_results = self.search_engine.news_search(query, max_results=fetch_n)
        else:
            all_results = self.search_engine.search(query, max_results=fetch_n)
        
        page_results = all_results[start:start + per_page] if all_results else []
        # has_more true if there are results beyond the current page slice
        has_more = bool(all_results and len(all_results) > (start + per_page))
        
        research_data = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'search_results': page_results,
            'sources': [],
            'page': page,
            'per_page': per_page,
            'has_more': has_more,
        }
        
        if not page_results:
            research_data['error'] = 'No search results found'
            self.research_history.append(research_data)
            return research_data
        
        if depth in ['standard', 'deep']:
            # Step 2: Scrape sources for the current page only
            msg = f"Scraping {len(page_results)} sources..."
            print(f"📄 {msg}")
            if progress_cb:
                progress_cb(msg)
            
            successful_scrapes = 0
            for i, result in enumerate(page_results, 1):
                url = result.get('url', '')
                prog = f"Scraping [{i}/{len(page_results)}] {url}"
                print(f"  [{i}/{len(page_results)}] {url}")
                if progress_cb:
                    progress_cb(prog)
                
                try:
                    scraped = self.scraper.scrape_url(url)
                    if scraped.get('success'):
                        research_data['sources'].append(scraped)
                        successful_scrapes += 1
                except Exception as e:
                    logging.error(f"Error scraping {url}: {e}")
            
            logging.info(f"Successfully scraped {successful_scrapes}/{len(page_results)} sources")
        
        if depth == 'deep' and self.use_ai:
            # Step 3: AI analysis with local models
            print(f"🤖 Analyzing with {self.ai_backend}...")
            if progress_cb:
                progress_cb(f"Analyzing with {self.ai_backend}...")
            research_data['analysis'] = self._analyze_with_ai(research_data)
        
        self.research_history.append(research_data)
        return research_data
    
    def _analyze_with_ai(self, research_data: Dict) -> str:
        """Analyze research data with local AI (Ollama or Transformers)"""
        try:
            # Try Ollama first (faster, requires Ollama installed)
            return self._analyze_with_ollama(research_data)
        except Exception as e1:
            try:
                # Fallback to Hugging Face transformers
                return self._analyze_with_transformers(research_data)
            except Exception as e2:
                return f"AI analysis unavailable. Install Ollama or use transformers. Errors: {e1}, {e2}"
    
    def _analyze_with_ollama(self, research_data: Dict) -> str:
        """Analyze using Ollama (local LLM)"""
        import ollama
        
        # Prepare context from sources
        context = f"Research Query: {research_data['query']}\n\n"
        context += "Sources:\n"
        for i, source in enumerate(research_data['sources'], 1):
            context += f"\n{i}. {source['title']}\n"
            context += f"{source['text'][:800]}...\n"
        
        prompt = f"""{context}

Based on the above sources, provide a comprehensive research summary that:
1. Synthesizes key findings
2. Identifies common themes
3. Highlights important insights
4. Remains factual and objective

Summary:"""
        
        response = ollama.generate(
            model='llama2',  # or 'mistral', 'phi', etc.
            prompt=prompt
        )
        
        return response['response']
    
    def _analyze_with_transformers(self, research_data: Dict) -> str:
        """Analyze using Hugging Face transformers (fallback)"""
        from transformers import pipeline
        
        # Use summarization pipeline
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        
        # Combine all source texts
        full_text = f"Research on: {research_data['query']}\n\n"
        for source in research_data['sources']:
            full_text += f"{source['title']}: {source['text'][:500]}... "
        
        # Summarize (BART has max length limits)
        text_chunk = full_text[:1024]
        summary = summarizer(text_chunk, max_length=300, min_length=100, do_sample=False)
        
        return summary[0]['summary_text']
    
    def save_research(self, filename: str = None):
        """Save research history to JSON file"""
        if not filename:
            filename = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.research_history, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Research saved to {filename}")
        return filename
