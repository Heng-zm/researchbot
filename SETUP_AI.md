# Local AI Setup Guide

This research agent uses **local AI models** - no API keys or cloud services required!

## Option 1: Ollama (Recommended - Fastest)

### Install Ollama

**Windows:**
1. Download from [ollama.ai](https://ollama.ai)
2. Run the installer
3. Open PowerShell and test: `ollama --version`

**Linux/Mac:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Download Models

```bash
# Lightweight and fast (1.5GB)
ollama pull phi

# Balanced performance (4GB)
ollama pull mistral

# Most capable (7GB)
ollama pull llama2
```

### Use with Research Agent

```powershell
# Default uses Ollama with llama2
python cli.py "What is AI?" --depth deep

# Or specify explicitly
python cli.py "Machine learning" --depth deep --ai-backend ollama
```

### Edit Model Choice

In `research_agent.py`, line 194, change:
```python
model='llama2'  # Change to 'phi', 'mistral', 'codellama', etc.
```

Available models: `phi`, `mistral`, `llama2`, `codellama`, `vicuna`, `orca-mini`

## Option 2: Transformers (No Extra Install)

Uses Hugging Face models that download automatically.

```powershell
# Uses facebook/bart-large-cnn for summarization
python cli.py "Research topic" --depth deep --ai-backend transformers
```

**Pros:**
- No Ollama installation needed
- Works out of the box
- Good for summarization

**Cons:**
- Slower first run (downloads model ~1.6GB)
- Less flexible than Ollama
- Limited to summarization

## Option 3: No AI (Search & Scrape Only)

```powershell
python cli.py "Research topic" --depth standard --ai-backend none
```

## Performance Comparison

| Backend | Speed | Quality | Disk Space | Internet |
|---------|-------|---------|------------|----------|
| **Ollama (phi)** | ⚡⚡⚡ Fast | Good | 1.5GB | Download once |
| **Ollama (mistral)** | ⚡⚡ Medium | Excellent | 4GB | Download once |
| **Ollama (llama2)** | ⚡ Slower | Excellent | 7GB | Download once |
| **Transformers** | ⚡⚡ Medium | Good | 1.6GB | Download once |
| **None** | ⚡⚡⚡ Instant | N/A | 0 | Always |

## Troubleshooting

### "Ollama not found"
- Windows: Make sure Ollama is installed and in PATH
- Check: `ollama --version`
- Restart terminal after installation

### "Model not found"
```bash
ollama pull llama2
```

### Out of memory
Use a smaller model:
```bash
ollama pull phi  # Only 1.5GB, works on 8GB RAM
```

### Slow performance
- Use `phi` for faster results
- Reduce `max_sources` in research
- Use `--ai-backend transformers` or `none`

## Recommended Setup

**For most users:**
```bash
ollama pull phi
python cli.py "Your query" --depth deep
```

**For best quality:**
```bash
ollama pull mistral
python cli.py "Your query" --depth deep
```

**For no installation:**
```powershell
python cli.py "Your query" --depth deep --ai-backend transformers
```

## Privacy Note

✅ **100% Local & Private:**
- All AI runs on your computer
- No data sent to cloud services
- No API keys needed
- Complete privacy

---

**Quick Start:**
1. `ollama pull phi`
2. `python cli.py "What is quantum computing?" --depth deep`
3. Done! 🎉
