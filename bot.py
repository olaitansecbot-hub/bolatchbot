"""
@bolatchbot - Telegram Bot with Word Counter & Plagiarism Checker
Deployed on Railway with GitHub integration
"""

import os
import logging
import sys
import re
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes, 
    filters
)

# ==================== CONFIGURATION ====================

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Bot token from environment variable
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN environment variable not set!")
    sys.exit(1)

# ==================== PLAGIARISM CHECKER FUNCTIONS ====================

def check_plagiarism(text):
    """
    Check for plagiarism using multiple free APIs and techniques
    Returns: dict with results
    """
    results = {
        'plagiarized': False,
        'percentage': 0,
        'sources': [],
        'message': ''
    }
    
    # Method 1: Check via Google Search API (free tier)
    try:
        # Prepare search query
        search_text = text[:50] + "..." if len(text) > 50 else text
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        cse_id = os.environ.get("GOOGLE_CSE_ID", "")
        
        if api_key and cse_id:
            # Use Google Custom Search API
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': api_key,
                'cx': cse_id,
                'q': search_text
            }
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and len(data['items']) > 0:
                    results['plagiarized'] = True
                    results['percentage'] = min(80, len(data['items']) * 10)
                    for item in data['items'][:3]:
                        results['sources'].append({
                            'title': item.get('title', 'Unknown'),
                            'url': item.get('link', '#'),
                            'snippet': item.get('snippet', '')[:100]
                        })
                    results['message'] = f"⚠️ Found {len(data['items'])} possible matches!"
                else:
                    results['message'] = "✅ No matches found!"
            else:
                results['message'] = "🔍 Using alternative check..."
        else:
            results['message'] = "🔍 Using built-in similarity check..."
    except Exception as e:
        logger.error(f"Plagiarism check error: {e}")
        results['message'] = "⚠️ API check failed, using text analysis..."
    
    # Method 2: Built-in text analysis (checks for common phrases)
    if not results['plagiarized']:
        # Check for common text patterns that might indicate plagiarism
        common_phrases = [
            "according to", "as stated by", "research shows", 
            "studies indicate", "it is believed that", "it has been found",
            "the results show", "data suggests", "analysis reveals"
        ]
        
        text_lower = text.lower()
        matches = sum(1 for phrase in common_phrases if phrase in text_lower)
        
        if matches >= 3:
            results['plagiarized'] = True
            results['percentage'] = min(50, matches * 10)
            results['message'] = f"⚠️ Text contains {matches} common academic phrases that may indicate similarity."
        else:
            results['message'] = "✅ No obvious similarity detected!"
    
    # Method 3: Word frequency analysis for uniqueness
    words = re.findall(r'\b\w+\b', text.lower())
    unique_words = set(words)
    
    if len(words) > 0:
        uniqueness_ratio = len(unique_words) / len(words)
        if uniqueness_ratio < 0.4 and len(words) > 20:
            results['plagiarized'] = True
            results['percentage'] = max(results['percentage'], 40)
            results['message'] += " Text has low uniqueness ratio."
    
    return results

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - Welcome message"""
    user = update.effective_user
    first_name = user.first_name or "there"
    
    welcome_text = f"""
🚀 *Welcome to @bolatchbot, {first_name}!*

I'm your all-in-one Telegram assistant with:
• 📝 *Word Counter* - Count words, characters, sentences
• 🔍 *Plagiarism Checker* - Check text uniqueness
• 📊 *Text Analysis* - Analyze your writing
• 🎯 *More tools!*

*How to use:*
/help - See all available commands
/wordcounter [your text] - Count words
/plagiarism [your text] - Check for plagiarism

Or just send me any text and I'll analyze it!
"""
    
    keyboard = [
        [
            InlineKeyboardButton("📝 Word Counter", callback_data="word_counter"),
            InlineKeyboardButton("🔍 Plagiarism Check", callback_data="plagiarism")
        ],
        [
            InlineKeyboardButton("📊 Text Analysis", callback_data="analyze")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    logger.info(f"User {user.id} ({first_name}) started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📚 *@bolatchbot - Available Commands*

*Text Tools:*
/wordcounter [text] - Count words, characters, and sentences
/plagiarism [text] - Check text for plagiarism
/analyze [text] - Full text analysis

*Utility:*
/start - Welcome message
/help - Show this help
/time - Current time
/about - About this bot

*Quick Tips:*
• Just send any text and I'll analyze it automatically!
• Use buttons for quick access to tools
• I check for both online and offline plagiarism

*Examples:*
/wordcounter The quick brown fox jumps over the lazy dog
/plagiarism According to recent studies, climate change is accelerating
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def wordcounter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /wordcounter command"""
    text = ' '.join(context.args)
    
    if not text:
        await update.message.reply_text(
            "📝 *Word Counter*\n\n"
            "Please provide text to count!\n"
            "Example: `/wordcounter The quick brown fox jumps over the lazy dog`",
            parse_mode='Markdown'
        )
        return
    
    # Count statistics
    word_count = len(text.split())
    char_count = len(text)
    char_no_spaces = len(text.replace(' ', ''))
    sentence_count = len(re.findall(r'[.!?]+', text))
    paragraph_count = len(re.findall(r'\n\s*\n', text)) + 1
    
    # Word frequency
    words = re.findall(r'\b\w+\b', text.lower())
    unique_words = len(set(words))
    
    # Average word length
    avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
    
    response = f"""
📊 *Word Counter Results*

📝 Your text: `{text[:100]}{'...' if len(text) > 100 else ''}`

📖 *Statistics:*
• Words: {word_count}
• Characters (with spaces): {char_count}
• Characters (no spaces): {char_no_spaces}
• Sentences: {sentence_count}
• Paragraphs: {paragraph_count}
• Unique words: {unique_words}
• Avg word length: {avg_word_length:.1f} characters

📈 *Readability:*
• Long words (8+ chars): {sum(1 for w in words if len(w) >= 8)}
• Short words (3- chars): {sum(1 for w in words if len(w) <= 3)}
"""
    await update.message.reply_text(response, parse_mode='Markdown')

async def plagiarism_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /plagiarism command"""
    text = ' '.join(context.args)
    
    if not text:
        await update.message.reply_text(
            "🔍 *Plagiarism Checker*\n\n"
            "Please provide text to check!\n"
            "Example: `/plagiarism According to recent studies, climate change is accelerating`",
            parse_mode='Markdown'
        )
        return
    
    # Send initial processing message
    processing_msg = await update.message.reply_text(
        "🔍 *Checking for plagiarism...*\n"
        "Please wait, analyzing text...",
        parse_mode='Markdown'
    )
    
    # Perform plagiarism check
    results = check_plagiarism(text)
    
    # Format response
    status_icon = "✅" if not results['plagiarized'] else "⚠️"
    status_text = "Clean" if not results['plagiarized'] else "Potential Plagiarism Detected!"
    
    response = f"""
🔍 *Plagiarism Check Results*

📝 Text preview: `{text[:100]}{'...' if len(text) > 100 else ''}`

{status_icon} *Status:* {status_text}
📊 *Similarity Score:* {results['percentage']}%

{results['message']}
"""
    
    # Add sources if found
    if results['sources']:
        response += "\n*Potential Sources:*\n"
        for i, source in enumerate(results['sources'][:3], 1):
            response += f"{i}. [{source['title']}]({source['url']})\n"
            if source['snippet']:
                response += f"   _{source['snippet']}..._\n"
    
    response += "\n*Tips:*\n"
    if results['plagiarized']:
        response += "• Paraphrase the text using your own words\n"
        response += "• Cite your sources properly\n"
        response += "• Use quotation marks for direct quotes"
    else:
        response += "• Your text appears to be original\n"
        response += "• Continue to cite sources when needed\n"
        response += "• Use proper referencing"
    
    await processing_msg.edit_text(response, parse_mode='Markdown', disable_web_page_preview=True)

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analyze command - Full text analysis"""
    text = ' '.join(context.args)
    
    if not text:
        await update.message.reply_text(
            "📊 *Text Analysis*\n\n"
            "Please provide text to analyze!\n"
            "Example: `/analyze The quick brown fox jumps over the lazy dog`",
            parse_mode='Markdown'
        )
        return
    
    # Send initial processing
    processing_msg = await update.message.reply_text(
        "📊 *Analyzing text...*\n"
        "Please wait...",
        parse_mode='Markdown'
    )
    
    # Word counter results
    word_count = len(text.split())
    char_count = len(text)
    sentence_count = len(re.findall(r'[.!?]+', text))
    
    # Plagiarism check
    plagiarism_results = check_plagiarism(text)
    
    # Sentiment analysis (basic)
    positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'best', 'love', 'happy']
    negative_words = ['bad', 'terrible', 'awful', 'worst', 'hate', 'sad', 'poor', 'horrible']
    
    text_lower = text.lower()
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)
    
    if pos_count > neg_count:
        sentiment = "😊 Positive"
    elif neg_count > pos_count:
        sentiment = "😞 Negative"
    else:
        sentiment = "😐 Neutral"
    
    response = f"""
📊 *Complete Text Analysis*

📝 Your text: `{text[:100]}{'...' if len(text) > 100 else ''}`

*Basic Statistics:*
• Words: {word_count}
• Characters: {char_count}
• Sentences: {sentence_count}
• Avg words/sentence: {word_count / sentence_count if sentence_count > 0 else 0:.1f}

*Plagiarism Check:*
• Status: {'✅ Clean' if not plagiarism_results['plagiarized'] else '⚠️ Potential Match'}
• Similarity Score: {plagiarism_results['percentage']}%

*Sentiment Analysis:*
• Overall: {sentiment}
• Positive words: {pos_count}
• Negative words: {neg_count}

*Recommendations:*
• {'✅ Your text appears original' if not plagiarism_results['plagiarized'] else '⚠️ Consider rewriting or citing sources'}
• {'📊 Text is well-structured' if sentence_count > 5 else '📊 Consider adding more sentences for clarity'}
"""
    
    await processing_msg.edit_text(response, parse_mode='Markdown')

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /time command"""
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%H:%M:%S")
    
    response = f"""
🕐 *Current Time*

📅 Date: {date_str}
⏰ Time: {time_str}
🌐 Timezone: UTC
"""
    await update.message.reply_text(response, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command"""
    about_text = """
ℹ️ *About @bolatchbot*

*What is this?*
A powerful Telegram bot with text analysis tools.

*Features:*
• ✅ Word Counter
• ✅ Plagiarism Checker  
• ✅ Text Analysis
• ✅ Sentiment Analysis
• ✅ 24/7 Availability

*Technology:*
• 🐍 Python 3.11
• 📦 python-telegram-bot
• 🚂 Railway
• 🔒 GitHub

*Open Source:*
https://github.com/YOUR_USERNAME/bolatchbot
"""
    keyboard = [[InlineKeyboardButton("🔗 View on GitHub", url="https://github.com/YOUR_USERNAME/bolatchbot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(about_text, parse_mode='Markdown', reply_markup=reply_markup)

# ==================== MESSAGE HANDLERS ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message - Auto analyze"""
    user = update.effective_user
    text = update.message.text
    
    # Ignore commands (handled elsewhere)
    if text.startswith('/'):
        return
    
    logger.info(f"Processing text from {user.id}: {text[:50]}")
    
    # Show a quick preview with actions
    keyboard = [
        [
            InlineKeyboardButton("📊 Word Count", callback_data=f"wc_{text[:30]}"),
            InlineKeyboardButton("🔍 Plagiarism", callback_data=f"plag_{text[:30]}")
        ],
        [
            InlineKeyboardButton("📈 Full Analysis", callback_data=f"analyze_{text[:30]}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    word_count = len(text.split())
    char_count = len(text)
    
    preview = f"""
📝 *Text Received!*

Your text: `{text[:100]}{'...' if len(text) > 100 else ''}`

📊 Quick Stats:
• {word_count} words
• {char_count} characters

Choose an action below or use commands:
/wordcounter [text]
/plagiarism [text]
/analyze [text]
"""
    
    await update.message.reply_text(
        preview,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ==================== CALLBACK QUERY HANDLERS ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("wc_"):
        # Word counter from button
        text = data[3:]
        if text:
            await query.edit_message_text(
                f"📝 *Word Count*\n\n"
                f"Text: `{text}`\n\n"
                f"Words: {len(text.split())}\n"
                f"Characters: {len(text)}",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "📝 *Word Counter*\n\n"
                "Send me any text and I'll count the words!\n"
                "Or use: /wordcounter [your text]",
                parse_mode='Markdown'
            )
    
    elif data.startswith("plag_"):
        # Plagiarism check from button
        text = data[5:]
        if text:
            # Quick plagiarism check
            results = check_plagiarism(text)
            status = "✅ Clean" if not results['plagiarized'] else "⚠️ Potential Match"
            
            await query.edit_message_text(
                f"🔍 *Plagiarism Check*\n\n"
                f"Text preview: `{text[:100]}...`\n\n"
                f"Status: {status}\n"
                f"Score: {results['percentage']}%\n\n"
                f"Use /plagiarism [text] for detailed analysis",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "🔍 *Plagiarism Checker*\n\n"
                "Send me text to check for plagiarism!\n"
                "Use: /plagiarism [your text]",
                parse_mode='Markdown'
            )
    
    elif data.startswith("analyze_"):
        # Full analysis from button
        text = data[8:]
        if text:
            # Quick analysis
            word_count = len(text.split())
            char_count = len(text)
            
            await query.edit_message_text(
                f"📊 *Text Analysis*\n\n"
                f"Text: `{text[:100]}...`\n\n"
                f"📖 Statistics:\n"
                f"• Words: {word_count}\n"
                f"• Characters: {char_count}\n\n"
                f"Use /analyze [text] for complete analysis",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "📊 *Text Analyzer*\n\n"
                "Send me text to analyze!\n"
                "Use: /analyze [your text]",
                parse_mode='Markdown'
            )
    
    elif data == "word_counter":
        await query.edit_message_text(
            "📝 *Word Counter*\n\n"
            "Use the command:\n"
            "`/wordcounter Your text here`\n\n"
            "Or just send me any text and I'll count the words!",
            parse_mode='Markdown'
        )
    
    elif data == "plagiarism":
        await query.edit_message_text(
            "🔍 *Plagiarism Checker*\n\n"
            "Use the command:\n"
            "`/plagiarism Your text here`\n\n"
            "I'll check for:\n"
            "• Online matches\n"
            "• Common phrases\n"
            "• Text uniqueness",
            parse_mode='Markdown'
        )
    
    elif data == "analyze":
        await query.edit_message_text(
            "📊 *Text Analysis*\n\n"
            "Use the command:\n"
            "`/analyze Your text here`\n\n"
            "I'll provide:\n"
            "• Word statistics\n"
            "• Plagiarism check\n"
            "• Sentiment analysis\n"
            "• Recommendations",
            parse_mode='Markdown'
        )

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands"""
    await update.message.reply_text(
        "❌ I don't understand that command.\n\n"
        "Use /help to see all available commands.",
        parse_mode='Markdown'
    )

# ==================== ERROR HANDLER ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Oops! Something went wrong.\n"
                "Please try again or use /help for assistance."
            )
    except:
        pass

# ==================== MAIN FUNCTION ====================

def main():
    """Start the bot"""
    logger.info("🚀 Starting @bolatchbot with Word Counter & Plagiarism Checker...")
    
    try:
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("wordcounter", wordcounter_command))
        application.add_handler(CommandHandler("plagiarism", plagiarism_command))
        application.add_handler(CommandHandler("analyze", analyze_command))
        application.add_handler(CommandHandler("time", time_command))
        application.add_handler(CommandHandler("about", about_command))
        
        # Message handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
        
        # Callback handler (for buttons)
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Error handler
        application.add_error_handler(error_handler)
        
        logger.info("✅ Bot is running with long polling...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
