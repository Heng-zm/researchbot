"""
Command-line interface for AI Research Agent
"""
import argparse
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from research_agent import AIResearchAgent

console = Console()


def display_results(research_data: dict):
    """Display research results in a formatted way"""
    
    # Header
    console.print(Panel(
        f"[bold cyan]Research Query:[/bold cyan] {research_data['query']}\n"
        f"[dim]Timestamp: {research_data['timestamp']}[/dim]",
        title="🔬 Research Results"
    ))
    
    if research_data.get('error'):
        console.print(f"\n[bold red]⚠️ {research_data['error']}[/bold red]")
    
    # Search Results
    if research_data.get('search_results'):
        console.print("\n[bold yellow]📊 Search Results:[/bold yellow]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="cyan")
        table.add_column("URL", style="blue")
        
        for i, result in enumerate(research_data['search_results'], 1):
            table.add_row(
                str(i),
                result['title'][:60] + "..." if len(result['title']) > 60 else result['title'],
                result['url'][:50] + "..." if len(result['url']) > 50 else result['url']
            )
        
        console.print(table)
    
    # Scraped Sources
    if research_data.get('sources'):
        console.print(f"\n[bold green]📄 Scraped {len(research_data['sources'])} Sources:[/bold green]")
        for i, source in enumerate(research_data['sources'], 1):
            console.print(f"\n[bold]{i}. {source['title']}[/bold]")
            console.print(f"   URL: [link]{source['url']}[/link]")
            if source.get('authors'):
                console.print(f"   Authors: {', '.join(source['authors'])}")
            if source.get('publish_date'):
                console.print(f"   Published: {source['publish_date']}")
            
            # Show excerpt
            text = source.get('text', '')
            excerpt = text[:300] + "..." if len(text) > 300 else text
            console.print(f"   [dim]{excerpt}[/dim]")
    
    # AI Analysis
    if research_data.get('analysis'):
        console.print("\n[bold magenta]🤖 AI Analysis:[/bold magenta]")
        console.print(Panel(research_data['analysis'], border_style="magenta"))


def main():
    parser = argparse.ArgumentParser(
        description='AI Research Agent - Powerful internet research tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py "What are the latest AI developments?"
  python cli.py "Climate change impacts" --depth deep --sources 10
  python cli.py "Python best practices" --save results.json
  python cli.py "AI trends" --depth deep --ai-backend ollama
  python cli.py "Machine learning" --depth deep --ai-backend transformers
        """
    )
    
    parser.add_argument(
        'query',
        type=str,
        help='Research query or question'
    )
    
    parser.add_argument(
        '--depth',
        type=str,
        choices=['quick', 'standard', 'deep'],
        default='standard',
        help='Research depth: quick (search only), standard (search+scrape), deep (search+scrape+AI)'
    )
    
    parser.add_argument(
        '--sources',
        type=int,
        default=5,
        help='Maximum number of sources to scrape (default: 5)'
    )
    
    parser.add_argument(
        '--save',
        type=str,
        metavar='FILE',
        help='Save results to JSON file'
    )
    
    parser.add_argument(
        '--ai-backend',
        type=str,
        choices=['ollama', 'transformers', 'none'],
        default='ollama',
        help='AI backend for analysis: ollama (local), transformers (Hugging Face), or none'
    )
    
    parser.add_argument(
        '--news',
        action='store_true',
        help='Search for news articles instead of general web results'
    )
    
    args = parser.parse_args()
    
    # Initialize agent
    console.print("[bold green]🚀 Initializing AI Research Agent...[/bold green]")
    use_ai = args.ai_backend != 'none'
    agent = AIResearchAgent(use_ai=use_ai, ai_backend=args.ai_backend)
    
    # Conduct research
    try:
        results = agent.research(
            query=args.query,
            depth=args.depth,
            max_sources=args.sources,
            news=args.news
        )
        
        # Display results
        display_results(results)
        
        # Save if requested
        if args.save:
            agent.save_research(args.save)
        
        console.print("\n[bold green]✅ Research completed successfully![/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Research interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")


if __name__ == "__main__":
    main()
