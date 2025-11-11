"""
Example usage of AI Research Agent
"""
from research_agent import AIResearchAgent
import json


def main():
    # Initialize the agent
    print("Initializing AI Research Agent...")
    agent = AIResearchAgent()
    
    # Example 1: Quick search (no scraping)
    print("\n" + "="*60)
    print("EXAMPLE 1: Quick Search")
    print("="*60)
    results1 = agent.research(
        query="What is quantum computing?",
        depth="quick",
        max_sources=5
    )
    print(f"\nFound {len(results1['search_results'])} results")
    for i, result in enumerate(results1['search_results'][:3], 1):
        print(f"{i}. {result['title']}")
        print(f"   {result['url']}")
    
    # Example 2: Standard research (search + scraping)
    print("\n" + "="*60)
    print("EXAMPLE 2: Standard Research")
    print("="*60)
    results2 = agent.research(
        query="Latest developments in renewable energy 2024",
        depth="standard",
        max_sources=3
    )
    print(f"\nScraped {len(results2['sources'])} sources")
    for i, source in enumerate(results2['sources'], 1):
        print(f"\n{i}. {source['title']}")
        print(f"   URL: {source['url']}")
        text_preview = source['text'][:200] + "..." if len(source['text']) > 200 else source['text']
        print(f"   Preview: {text_preview}")
    
    # Example 3: Deep research with AI analysis (requires OpenAI API key)
    print("\n" + "="*60)
    print("EXAMPLE 3: Deep Research with AI")
    print("="*60)
    print("Note: Set OPENAI_API_KEY environment variable for AI analysis")
    results3 = agent.research(
        query="Best practices for Python microservices",
        depth="deep",
        max_sources=5
    )
    if 'analysis' in results3:
        print("\nAI Analysis:")
        print(results3['analysis'])
    
    # Save all research
    filename = agent.save_research("my_research.json")
    print(f"\n✅ All research saved to {filename}")
    
    # Example: Load and use saved research
    print("\n" + "="*60)
    print("LOADING SAVED RESEARCH")
    print("="*60)
    with open(filename, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    print(f"Loaded {len(loaded_data)} research sessions")


if __name__ == "__main__":
    main()
