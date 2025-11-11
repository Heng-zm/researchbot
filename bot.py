"""
Optimized Telegram bot for AI Research Agent
Bug fixes and enhanced UI/UX with countdown and better error handling
"""
import os
import asyncio
import html
import logging
from typing import Dict, List, Optional, Tuple
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

from research_agent import AIResearchAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from telegram import Update, constants, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.error import BadRequest, TimedOut, NetworkError, TelegramError
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        CallbackQueryHandler,
        filters,
    )
except ImportError as e:
    raise SystemExit(
        "python-telegram-bot required. Install: pip install python-telegram-bot"
    ) from e

# Constants
MAX_MESSAGE_LEN = 3800  # Reduced for safety margin
DEFAULT_SOURCES = 3
ANALYSIS_MAX_LEN = 1000
CACHE_SIZE = 128
COUNTDOWN_SECONDS = 5
MIN_SEARCH_DELAY = 1  # Minimum delay to avoid rate limits

# UI Emojis
EMOJI = {
    'search': '🔍',
    'quick': '⚡',
    'news': '📰',
    'deep': '🧠',
    'loading': '⏳',
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'settings': '⚙️',
    'help': '💡',
    'back': '◀️',
    'next': '▶️',
    'prev': '◀️',
    'auto': '🔄',
    'google': '🔴',
    'ddg': '🦆',
    'sparkle': '✨',
    'rocket': '🚀',
}

# Agent cache
_agent_cache: Dict[str, AIResearchAgent] = {}


class UIText:
    """Centralized UI text for consistency"""
    
    @staticmethod
    def welcome() -> str:
        return (
            f"{EMOJI['rocket']} <b>AI Research Assistant</b>\n\n"
            "💬 <b>Just type your question!</b>\n"
            "<i>Example: What's new in AI?</i>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"{EMOJI['quick']} <b>Quick</b> - Fast web search\n"
            f"{EMOJI['news']} <b>News</b> - Latest articles\n"
            f"{EMOJI['deep']} <b>Deep</b> - AI analysis\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "👇 <b>Choose mode below:</b>"
        )
    
    @staticmethod
    def help_text(mode: str, engine: str) -> str:
        mode_names = {
            'standard': f"{EMOJI['quick']} Quick",
            'news': f"{EMOJI['news']} News",
            'deep': f"{EMOJI['deep']} Deep"
        }
        engine_names = {
            'auto': f"{EMOJI['auto']} Auto",
            'google': f"{EMOJI['google']} Google",
            'duckduckgo': f"{EMOJI['ddg']} DuckDuckGo"
        }
        
        return (
            f"{EMOJI['help']} <b>Quick Guide</b>\n\n"
            "<b>How to use:</b>\n"
            "1️⃣ Type any question\n"
            "2️⃣ Get instant results\n"
            "3️⃣ Navigate with buttons\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Search Modes:</b>\n\n"
            f"{EMOJI['quick']} <b>Quick Search</b>\n"
            "Fast results from the web\n\n"
            f"{EMOJI['news']} <b>News Search</b>\n"
            "Latest news articles only\n\n"
            f"{EMOJI['deep']} <b>Deep Research</b>\n"
            "AI-powered analysis & summary\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Search Engines:</b>\n\n"
            f"{EMOJI['auto']} <b>Auto:</b> Smart selection\n"
            f"{EMOJI['google']} <b>Google:</b> Google API\n"
            f"{EMOJI['ddg']} <b>DuckDuckGo:</b> Privacy\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Current:</b> {mode_names.get(mode)} • {engine_names.get(engine)}"
        )
    
    @staticmethod
    def settings(mode: str, engine: str) -> str:
        mode_names = {
            'standard': f"{EMOJI['quick']} Quick Search",
            'news': f"{EMOJI['news']} News Search",
            'deep': f"{EMOJI['deep']} Deep Research"
        }
        engine_names = {
            'auto': f"{EMOJI['auto']} Auto Selection",
            'google': f"{EMOJI['google']} Google Search",
            'duckduckgo': f"{EMOJI['ddg']} DuckDuckGo"
        }
        
        return (
            f"{EMOJI['settings']} <b>Settings</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Current Configuration:</b>\n\n"
            f"<b>Mode:</b> {mode_names.get(mode, mode)}\n"
            f"<b>Engine:</b> {engine_names.get(engine, engine)}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👇 <b>Change settings below:</b>"
        )


def get_user_defaults(context: ContextTypes.DEFAULT_TYPE) -> Tuple[str, str]:
    """Get user's current mode and search engine with defaults"""
    mode = context.user_data.get('mode', 'standard')
    engine = context.user_data.get('search_engine', 'auto')
    return mode, engine


def init_user_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initialize user data with defaults"""
    defaults = {
        'mode': 'standard',
        'search_engine': 'auto',
        'page': 0,
    }
    for key, value in defaults.items():
        if key not in context.user_data:
            context.user_data[key] = value


async def safe_edit_message(query, **kwargs) -> bool:
    """Safely edit message with comprehensive error handling"""
    try:
        await query.edit_message_text(**kwargs)
        return True
    except BadRequest as e:
        error_str = str(e)
        if "Message is not modified" in error_str:
            return True  # Not really an error
        if "Message to edit not found" in error_str:
            logger.debug("Message already deleted")
            return False
        logger.warning(f"Failed to edit message: {e}")
        return False
    except (TimedOut, NetworkError) as e:
        logger.error(f"Network error editing message: {e}")
        return False
    except TelegramError as e:
        logger.error(f"Telegram error editing message: {e}")
        return False


async def safe_delete_message(bot, chat_id: int, message_id: int) -> bool:
    """Safely delete a message"""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception as e:
        logger.debug(f"Could not delete message: {e}")
        return False


def format_results(data: Dict) -> str:
    """Format research results with enhanced readability"""
    parts: List[str] = []
    
    # Header
    query = html.escape(data.get('query', ''))
    page = int(data.get('page', 0)) + 1
    
    parts.append(f"{EMOJI['search']} <b>Search Results</b>")
    parts.append(f"<b>Query:</b> <code>{query}</code>")
    
    if page > 1:
        parts.append(f"<b>Page:</b> {page}")
    
    parts.append("\n━━━━━━━━━━━━━━━━━━━━")
    
    # Results
    results = data.get('search_results', [])
    if results:
        parts.append(f"\n🔗 <b>Found {len(results)} results:</b>\n")
        for i, r in enumerate(results, 1):
            title = html.escape(r.get('title', 'Untitled')[:100])  # Truncate long titles
            url = html.escape(r.get('url', ''))
            # Clean display
            parts.append(f"{i}. <a href=\"{url}\">{title}</a>")
    else:
        parts.append(f"\n{EMOJI['warning']} <b>No results found</b>")
    
    # Sources
    sources = data.get('sources', [])
    if sources:
        parts.append(f"\n📄 <b>Analyzed:</b> {len(sources)} source(s)")
    
    # AI Analysis
    analysis = data.get('analysis')
    if analysis:
        parts.append("\n━━━━━━━━━━━━━━━━━━━━")
        text = html.escape(analysis.strip())
        if len(text) > ANALYSIS_MAX_LEN:
            text = text[:ANALYSIS_MAX_LEN].rsplit(' ', 1)[0] + "…"
        parts.append(f"\n{EMOJI['deep']} <b>AI Analysis:</b>\n\n{text}")
    
    # Error/Warning
    error = data.get('error')
    if error:
        parts.append(f"\n\n{EMOJI['warning']} <i>{html.escape(str(error)[:200])}</i>")
    
    msg = "\n".join(parts)
    
    # Final length check
    if len(msg) > MAX_MESSAGE_LEN:
        msg = msg[:MAX_MESSAGE_LEN].rsplit('\n', 1)[0] + "\n\n<i>...truncated</i>"
    
    return msg


@lru_cache(maxsize=CACHE_SIZE)
def get_agent(use_ai: bool, search_engine: str) -> AIResearchAgent:
    """Get or create cached agent instance"""
    cache_key = f"{use_ai}_{search_engine}"
    
    if cache_key not in _agent_cache:
        logger.info(f"Creating new agent: {cache_key}")
        _agent_cache[cache_key] = AIResearchAgent(
            use_ai=use_ai,
            ai_backend="ollama",
            search_engine=search_engine
        )
    
    agent = _agent_cache[cache_key]
    agent.set_search_engine(search_engine)
    return agent


async def run_research(
    query: str,
    depth: str,
    news: bool,
    sources: int,
    page: int,
    search_engine: str
) -> Dict:
    """Execute research in thread pool with proper error handling"""
    loop = asyncio.get_running_loop()
    use_ai = (depth == 'deep')
    
    try:
        agent = get_agent(use_ai, search_engine)
    except Exception as e:
        logger.error(f"Failed to get agent: {e}")
        return {
            'query': query,
            'error': 'Service initialization failed',
            'search_results': [],
            'sources': [],
            'page': page,
            'has_more': False
        }
    
    def _execute() -> Dict:
        try:
            return agent.research(
                query=query,
                depth=depth,
                max_sources=sources,
                news=news,
                page=page,
                per_page=sources
            )
        except Exception as e:
            logger.error(f"Research error for '{query}': {e}", exc_info=True)
            error_msg = str(e)
            if 'rate' in error_msg.lower() or 'limit' in error_msg.lower():
                error_msg = 'Rate limited - please wait'
            elif 'timeout' in error_msg.lower():
                error_msg = 'Search timeout - try again'
            else:
                error_msg = 'Search failed'
            
            return {
                'query': query,
                'error': error_msg,
                'search_results': [],
                'sources': [],
                'page': page,
                'has_more': False
            }
    
    return await loop.run_in_executor(None, _execute)


async def countdown_status(
    bot,
    chat_id: int,
    message_id: int,
    query_text: str,
    mode_emoji: str,
    seconds: int = COUNTDOWN_SECONDS
) -> None:
    """Update status message with animated countdown"""
    animation = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
    
    for i in range(seconds, 0, -1):
        try:
            spinner = animation[i % len(animation)]
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=(
                    f"{mode_emoji} <b>Searching...</b>\n\n"
                    f"<code>{html.escape(query_text[:50])}</code>\n\n"
                    f"{spinner} <b>Please wait {i}s</b>"
                ),
                parse_mode=constants.ParseMode.HTML,
            )
            await asyncio.sleep(1)
        except (BadRequest, TelegramError) as e:
            logger.debug(f"Countdown update failed: {e}")
            break
    
    # Final update with sparkle
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                f"{mode_emoji} <b>Searching...</b>\n\n"
                f"<code>{html.escape(query_text[:50])}</code>\n\n"
                f"{EMOJI['sparkle']} <b>Processing results...</b>"
            ),
            parse_mode=constants.ParseMode.HTML,
        )
    except (BadRequest, TelegramError):
        pass


def build_keyboard(
    mode: str,
    page: int,
    has_more: bool,
    engine: str,
    context: str = 'results'
) -> InlineKeyboardMarkup:
    """Build context-appropriate keyboard with enhanced visual design"""
    
    def active_mark(current: str, target: str, emoji: str, label: str) -> str:
        """Create button text with active indicator"""
        if current == target:
            return f"● {emoji} {label}"
        return f"○ {emoji} {label}"
    
    def compact_mark(current: str, target: str, emoji: str) -> str:
        """Compact button for results page"""
        return f"[{emoji}]" if current == target else emoji
    
    # Main menu - single mode selector + utilities
    if context == 'main':
        # Get current mode display
        mode_display = {
            'standard': f"{EMOJI['quick']} Quick",
            'news': f"{EMOJI['news']} News",
            'deep': f"{EMOJI['deep']} Deep"
        }
        
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"● {mode_display.get(mode, 'Quick')} Mode",
                    callback_data='choose_mode'
                ),
            ],
            [
                InlineKeyboardButton(
                    f"⚙️ Settings",
                    callback_data='show_settings'
                ),
                InlineKeyboardButton(
                    f"💡 Help",
                    callback_data='help'
                ),
            ],
        ])
    
    # Mode chooser menu
    if context == 'choose_mode':
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    active_mark(mode, 'standard', EMOJI['quick'], 'Quick Search'),
                    callback_data='mode_standard'
                )
            ],
            [
                InlineKeyboardButton(
                    active_mark(mode, 'news', EMOJI['news'], 'News Search'),
                    callback_data='mode_news'
                )
            ],
            [
                InlineKeyboardButton(
                    active_mark(mode, 'deep', EMOJI['deep'], 'Deep Research'),
                    callback_data='mode_deep'
                )
            ],
            [
                InlineKeyboardButton(
                    f"◀️ Back",
                    callback_data='back_to_main'
                )
            ],
        ])
    
    # Settings menu - organized by category
    if context == 'settings':
        return InlineKeyboardMarkup([
            # Search Mode Section
            [
                InlineKeyboardButton(
                    active_mark(mode, 'standard', EMOJI['quick'], 'Quick'),
                    callback_data='mode_standard'
                )
            ],
            [
                InlineKeyboardButton(
                    active_mark(mode, 'news', EMOJI['news'], 'News'),
                    callback_data='mode_news'
                )
            ],
            [
                InlineKeyboardButton(
                    active_mark(mode, 'deep', EMOJI['deep'], 'Deep'),
                    callback_data='mode_deep'
                )
            ],
            # Divider
            [
                InlineKeyboardButton(
                    "━━━ Search Engine ━━━",
                    callback_data='noop'
                )
            ],
            # Engine Selection
            [
                InlineKeyboardButton(
                    active_mark(engine, 'auto', EMOJI['auto'], 'Auto'),
                    callback_data='engine_auto'
                ),
            ],
            [
                InlineKeyboardButton(
                    active_mark(engine, 'google', EMOJI['google'], 'Google'),
                    callback_data='engine_google'
                ),
            ],
            [
                InlineKeyboardButton(
                    active_mark(engine, 'duckduckgo', EMOJI['ddg'], 'DuckDuckGo'),
                    callback_data='engine_duckduckgo'
                ),
            ],
            # Navigation
            [
                InlineKeyboardButton(
                    f"◀️ Back to Main",
                    callback_data='back_to_main'
                )
            ],
        ])
    
    # Results keyboard - compact and functional
    rows = []
    
    # Pagination with page indicator (first row)
    if page > 0 or has_more:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(
                f"⏮ Page {page}",
                callback_data='page_prev'
            ))
        
        # Current page indicator (non-clickable visual)
        nav.append(InlineKeyboardButton(
            f"• {page + 1} •",
            callback_data='noop'
        ))
        
        if has_more:
            nav.append(InlineKeyboardButton(
                f"Page {page + 2} ⏭",
                callback_data='page_next'
            ))
        
        rows.append(nav)
    
    # Action buttons row - New Search, Settings, Help
    rows.append([
        InlineKeyboardButton(
            f"🔎 New Search",
            callback_data='back_to_main'
        ),
        InlineKeyboardButton(
            f"⚙️",
            callback_data='show_settings'
        ),
        InlineKeyboardButton(
            f"💡",
            callback_data='help'
        ),
    ])
    
    return InlineKeyboardMarkup(rows)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    init_user_data(context)
    mode, engine = get_user_defaults(context)
    
    await update.message.reply_text(
        text=UIText.welcome(),
        parse_mode=constants.ParseMode.HTML,
        reply_markup=build_keyboard(mode, 0, False, engine, 'main'),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    init_user_data(context)
    mode, engine = get_user_defaults(context)
    
    await update.message.reply_text(
        text=UIText.help_text(mode, engine),
        parse_mode=constants.ParseMode.HTML,
        reply_markup=build_keyboard(mode, 0, False, engine, 'main'),
    )


async def handle_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query_text: str
) -> None:
    """Process search query with enhanced UX"""
    init_user_data(context)
    mode, engine = get_user_defaults(context)
    
    # Validate query
    query_text = query_text.strip()
    if not query_text or len(query_text) < 2:
        await update.message.reply_text(
            f"{EMOJI['warning']} Please enter a valid search query (min 2 characters)"
        )
        return
    
    # Determine search parameters
    news = (mode == 'news')
    depth = 'deep' if mode == 'deep' else 'standard'
    
    mode_emoji = {
        'standard': EMOJI['quick'],
        'news': EMOJI['news'],
        'deep': EMOJI['deep']
    }
    emoji = mode_emoji.get(mode, EMOJI['search'])
    
    # Send initial status
    status_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"{emoji} <b>Searching...</b>\n\n"
            f"<code>{html.escape(query_text[:50])}</code>\n\n"
            f"{EMOJI['loading']} <b>Please wait {COUNTDOWN_SECONDS}s</b>"
        ),
        parse_mode=constants.ParseMode.HTML,
    )
    
    countdown_task = None
    
    try:
        # Store query for pagination
        context.user_data.update({
            'last_query': query_text,
            'depth': depth,
            'news': news,
            'page': 0,
        })
        
        # Start countdown and search concurrently
        countdown_task = asyncio.create_task(
            countdown_status(
                context.bot,
                update.effective_chat.id,
                status_msg.message_id,
                query_text,
                emoji
            )
        )
        
        # Execute search
        data = await run_research(
            query=query_text,
            depth=depth,
            news=news,
            sources=DEFAULT_SOURCES,
            page=0,
            search_engine=engine
        )
        
        # Wait for countdown
        try:
            await countdown_task
        except asyncio.CancelledError:
            pass
        
        # Small delay for smooth UX
        await asyncio.sleep(0.5)
        
        # Format results
        msg = format_results(data)
        
        # Delete status and send results
        await safe_delete_message(context.bot, update.effective_chat.id, status_msg.message_id)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=False,
            reply_markup=build_keyboard(
                mode=mode,
                page=0,
                has_more=bool(data.get('has_more')),
                engine=engine,
                context='results'
            ),
        )
        
    except Exception as e:
        logger.error(f"Query handling error: {e}", exc_info=True)
        
        # Cancel countdown
        if countdown_task and not countdown_task.done():
            countdown_task.cancel()
        
        # Determine error message
        error_msg = "Search failed. Please try again."
        if any(word in str(e).lower() for word in ['rate', 'limit', 'quota']):
            error_msg = "⏳ Rate limited. Please wait a moment and try again."
        elif 'timeout' in str(e).lower():
            error_msg = "⏱️ Search timeout. Please try a simpler query."
        elif 'network' in str(e).lower():
            error_msg = "🌐 Network error. Please check your connection."
        
        await safe_delete_message(context.bot, update.effective_chat.id, status_msg.message_id)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"{EMOJI['error']} <b>Error</b>\n\n{error_msg}",
            parse_mode=constants.ParseMode.HTML,
            reply_markup=build_keyboard(mode, 0, False, engine, 'main'),
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages as queries"""
    text = (update.message.text or '').strip()
    if text:
        await handle_query(update, context, text)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses with improved feedback"""
    query = update.callback_query
    data = query.data
    
    # Handle noop (non-interactive buttons)
    if data == 'noop':
        await query.answer()
        return
    
    init_user_data(context)
    mode, engine = get_user_defaults(context)
    
    # Choose mode menu
    if data == 'choose_mode':
        await query.answer()
        mode_display = {
            'standard': f"{EMOJI['quick']} Quick Search",
            'news': f"{EMOJI['news']} News Search",
            'deep': f"{EMOJI['deep']} Deep Research"
        }
        
        await safe_edit_message(
            query,
            text=(
                f"🎯 <b>Choose Search Mode</b>\n\n"
                f"<b>Current:</b> {mode_display.get(mode)}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Select your preferred mode:"
            ),
            parse_mode=constants.ParseMode.HTML,
            reply_markup=build_keyboard(mode, 0, False, engine, 'choose_mode')
        )
        return
    
    # Settings menu
    if data == 'show_settings':
        await query.answer()
        await safe_edit_message(
            query,
            text=UIText.settings(mode, engine),
            parse_mode=constants.ParseMode.HTML,
            reply_markup=build_keyboard(mode, 0, False, engine, 'settings')
        )
        return
    
    # Back to main
    if data == 'back_to_main':
        await query.answer()
        await safe_edit_message(
            query,
            text=UIText.welcome(),
            parse_mode=constants.ParseMode.HTML,
            reply_markup=build_keyboard(mode, 0, False, engine, 'main')
        )
        return
    
    # Help
    if data == 'help':
        await query.answer()
        await safe_edit_message(
            query,
            text=UIText.help_text(mode, engine),
            parse_mode=constants.ParseMode.HTML,
            reply_markup=build_keyboard(mode, 0, False, engine, 'main')
        )
        return
    
    # Mode selection
    if data.startswith('mode_'):
        new_mode = data.replace('mode_', '')
        old_mode = context.user_data.get('mode', 'standard')
        context.user_data['mode'] = new_mode
        
        mode_names = {
            'standard': f"{EMOJI['quick']} Quick Search",
            'news': f"{EMOJI['news']} News Search",
            'deep': f"{EMOJI['deep']} Deep Research"
        }
        
        # If mode actually changed, show confirmation and return to main
        if new_mode != old_mode:
            await query.answer(
                f"{EMOJI['success']} {mode_names.get(new_mode, new_mode)} activated!",
                show_alert=False
            )
            
            # Return to main menu to show updated mode
            await safe_edit_message(
                query,
                text=UIText.welcome(),
                parse_mode=constants.ParseMode.HTML,
                reply_markup=build_keyboard(new_mode, 0, False, engine, 'main')
            )
        else:
            await query.answer(
                f"Already in {mode_names.get(new_mode, new_mode)} mode",
                show_alert=False
            )
        return
    
    # Engine selection
    if data.startswith('engine_'):
        new_engine = data.replace('engine_', '')
        context.user_data['search_engine'] = new_engine
        
        engine_names = {
            'auto': f"{EMOJI['auto']} Auto",
            'google': f"{EMOJI['google']} Google",
            'duckduckgo': f"{EMOJI['ddg']} DuckDuckGo"
        }
        
        await query.answer(
            f"{EMOJI['success']} {engine_names.get(new_engine, new_engine)} selected!",
            show_alert=False
        )
        return
    
    # Pagination
    if data in ('page_next', 'page_prev'):
        last_query = context.user_data.get('last_query')
        if not last_query:
            await query.answer(
                f"{EMOJI['warning']} Send a search query first!",
                show_alert=True
            )
            return
        
        page = int(context.user_data.get('page', 0))
        old_page = page
        page = page + 1 if data == 'page_next' else max(0, page - 1)
        
        # Don't go back if already at page 0
        if old_page == 0 and data == 'page_prev':
            await query.answer(f"{EMOJI['warning']} Already at first page!", show_alert=False)
            return
        
        context.user_data['page'] = page
        
        depth = context.user_data.get('depth', 'standard')
        news = context.user_data.get('news', False)
        
        # Show loading
        await query.answer()
        await safe_edit_message(
            query,
            text=f"📄 <b>Loading page {page + 1}...</b>\n\n{EMOJI['loading']} Please wait...",
            parse_mode=constants.ParseMode.HTML,
        )
        
        try:
            data_obj = await run_research(
                query=last_query,
                depth=depth,
                news=news,
                sources=DEFAULT_SOURCES,
                page=page,
                search_engine=engine
            )
            
            msg = format_results(data_obj)
            await safe_edit_message(
                query,
                text=msg,
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=False,
                reply_markup=build_keyboard(
                    mode=mode,
                    page=page,
                    has_more=bool(data_obj.get('has_more')),
                    engine=engine,
                    context='results'
                )
            )
        except Exception as e:
            logger.error(f"Pagination error: {e}")
            await safe_edit_message(
                query,
                text=f"{EMOJI['error']} <b>Error loading page</b>\n\nPlease try again.",
                parse_mode=constants.ParseMode.HTML,
            )


def main() -> None:
    """Run the bot with proper initialization"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise SystemExit(
            f"{EMOJI['error']} Set TELEGRAM_BOT_TOKEN environment variable"
        )
    
    # Build application
    app = ApplicationBuilder().token(token).build()
    
    # Register handlers
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('help', cmd_help))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info(f"{EMOJI['rocket']} Bot started successfully!")
    
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info(f"{EMOJI['success']} Bot stopped by user")
    finally:
        # Cleanup
        logger.info("Cleaning up resources...")
        _agent_cache.clear()
        get_agent.cache_clear()


if __name__ == '__main__':
    main()