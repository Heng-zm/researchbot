# 🔬 AI Research Agent

A powerful AI-powered internet research tool that searches, scrapes, and analyzes web content with optional AI-powered synthesis.

## ✨ Features

- 🌐 **Web Search**: Search the internet using DuckDuckGo (no API key needed)
- 📄 **Smart Scraping**: Extract clean content from web pages with fallback mechanisms
- 🤖 **Local AI Analysis**: Uses Ollama or Hugging Face (no API keys needed!)
- 💾 **Research History**: Save and load research sessions
- 🎨 **Beautiful CLI**: Rich terminal interface with tables and formatted output
- 📊 **Multiple Depth Levels**: Choose between quick, standard, or deep research
- 🔄 **Batch Processing**: Research multiple topics and save results

## 🚀 Quick Start

### Installation

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Optional: Install Ollama for AI analysis** (recommended):
```bash
# Download from ollama.ai and install
# Then pull a model:
ollama pull phi  # Fast, 1.5GB
# or
ollama pull mistral  # Better quality, 4GB
```

Alternatively, use Hugging Face transformers (no extra install needed).

See [SETUP_AI.md](SETUP_AI.md) for detailed setup.

### Basic Usage

**Command Line Interface**:
```bash
# Quick search (search only, no scraping)
python cli.py "What is artificial intelligence?"

# Standard research (search + scrape top 5 sources)
python cli.py "Climate change solutions" --depth standard

# Deep research with local AI analysis
python cli.py "Future of quantum computing" --depth deep --sources 10

# Use specific AI backend
python cli.py "AI trends" --depth deep --ai-backend ollama
python cli.py "Tech news" --depth deep --ai-backend transformers

# Save results to file
python cli.py "Python best practices" --save my_research.json
```

**Python API**:
```python
from research_agent import AIResearchAgent

# Initialize agent
agent = AIResearchAgent()

# Conduct research
results = agent.research(
    query="What are transformers in machine learning?",
    depth="standard",
    max_sources=5
)

# Access results
for source in results['sources']:
    print(f"Title: {source['title']}")
    print(f"URL: {source['url']}")
    print(f"Content: {source['text'][:200]}...\n")

# Save research
agent.save_research("ml_research.json")
```

## 📖 Documentation

### Research Depth Levels

| Depth | Description | Speed | Detail |
|-------|-------------|-------|--------|
| `quick` | Search only, no scraping | ⚡ Fast | Basic |
| `standard` | Search + scrape sources | 🚀 Medium | Good |
| `deep` | Search + scrape + AI analysis | 🔬 Slower | Excellent |

### CLI Arguments

```
python cli.py <query> [options]

Arguments:
  query                 Research query or question

Options:
  --depth {quick,standard,deep}
                        Research depth (default: standard)
  --sources N          Maximum sources to scrape (default: 5)
  --save FILE          Save results to JSON file
  --ai-backend {ollama,transformers,none}
                        AI backend: ollama (local), transformers (HuggingFace), none
  --news               Search news articles instead of general web
```

### Python API

#### AIResearchAgent

```python
class AIResearchAgent:
    def __init__(self, use_ai: bool = True, ai_backend: str = 'ollama')
    
    def research(self, query: str, depth: str = 'standard', max_sources: int = 5) -> Dict
    
    def save_research(self, filename: str = None) -> str
```

**Parameters**:
- `query`: Research question or topic
- `depth`: 'quick', 'standard', or 'deep'
- `max_sources`: Number of sources to scrape (1-20 recommended)

**Returns**: Dictionary with:
- `query`: Original query
- `timestamp`: When research was conducted
- `search_results`: List of search results
- `sources`: Scraped content from sources
- `analysis`: AI-generated summary (if depth='deep')

## 🔧 Advanced Usage

### Multi-Query Research

```python
agent = AIResearchAgent()

queries = [
    "Latest AI developments 2024",
    "Machine learning best practices",
    "Neural network architectures"
]

for query in queries:
    results = agent.research(query, depth="standard", max_sources=3)
    print(f"Completed: {query}")

# Save all research
agent.save_research("batch_research.json")
```

### Custom Analysis

```python
from research_agent import AIResearchAgent, WebScraper, SearchEngine

# Use individual components
scraper = WebScraper()
content = scraper.scrape_url("https://example.com")

search = SearchEngine()
results = search.search("Python tutorials", max_results=10)
news = search.news_search("AI news", max_results=5)
```

### Loading Saved Research

```python
import json

with open("research_20240101_120000.json", 'r') as f:
    past_research = json.load(f)

for session in past_research:
    print(f"Query: {session['query']}")
    print(f"Sources: {len(session['sources'])}")
```

## 🎯 Use Cases

- 📚 **Academic Research**: Gather sources for papers and literature reviews
- 💼 **Market Research**: Analyze industry trends and competitors
- 📰 **News Monitoring**: Track developments on specific topics
- 🔍 **Fact Checking**: Verify claims with multiple sources
- 📊 **Data Collection**: Gather information for analysis
- 🧠 **Learning**: Deep dive into new topics with AI summaries

## 📝 Examples

Run the example script to see all features:
```bash
python example.py
```

This demonstrates:
1. Quick search without scraping
2. Standard research with content extraction
3. Deep research with AI analysis
4. Saving and loading research data

## ⚙️ Configuration

### AI Backend Configuration

Choose your AI backend in `research_agent.py`:
```python
# Line 194 - Change Ollama model
model='llama2'  # Options: 'phi', 'mistral', 'llama2', 'codellama'

# Line 205 - Change Transformers model
model="facebook/bart-large-cnn"  # Or other summarization models
```

### Customization

Edit `research_agent.py` to customize:
- User agent strings
- Timeout values
- Text extraction limits
- AI model selection

## 🔒 Privacy & Safety

- **No tracking**: DuckDuckGo search respects privacy
- **Local processing**: All data stored locally
- **Rate limiting**: Built-in delays to respect websites
- **Error handling**: Graceful fallbacks for failed requests

## 🐛 Troubleshooting

**Issue**: "No search results found"
- Check internet connection
- Try different search terms
- DuckDuckGo may have rate limits

**Issue**: "AI analysis unavailable"
- Verify OPENAI_API_KEY is set correctly
- Check API key has sufficient credits
- Ensure openai package is installed

**Issue**: Scraping fails
- Some websites block scrapers
- Try different sources
- Check firewall/proxy settings

## 🛠️ Requirements

- Python 3.8+
- Internet connection
- Optional: Ollama (for best AI analysis)
- Optional: 8GB+ RAM (for local AI models)

## 📦 Dependencies

Core packages:
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `duckduckgo-search` - Web search
- `newspaper3k` - Article extraction
- `rich` - Terminal formatting
- `transformers` - Hugging Face models
- `ollama` - Local LLM interface
- `torch` - PyTorch for AI models

See `requirements.txt` for full list.

## 🚧 Limitations

- Rate limits from search engines
- Some websites block scraping
- Local AI models require disk space (1.5-7GB)
- Text extraction quality varies by site
- AI analysis speed depends on hardware

## 🔮 Future Enhancements

- [ ] Support for more search engines
- [ ] PDF and document research
- [ ] Multi-language support
- [ ] Research templates
- [ ] Automated citation generation
- [ ] Integration with research databases
- [ ] Browser automation for JavaScript sites
- [ ] Research comparison tools

## 📄 License

This project is provided as-is for research and educational purposes.

## 🤝 Contributing

Suggestions and improvements welcome! This is a powerful tool for anyone needing comprehensive internet research capabilities.

---

**Built with**: Python, DuckDuckGo, OpenAI, BeautifulSoup, and ❤️
#   r e s e a r c h b o t  
 