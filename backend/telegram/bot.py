"""
Telegram Bot with Inline Keyboard Buttons.

Features:
- No slash commands needed! Users interact via buttons
- Main menu with: Add Word, My Words, Review, Quiz, Stats
- Inline keyboards for all interactions
- Callback query handling
- Integration with all 3 agents

Commands (hidden from user, used internally):
- Start → Shows main menu with buttons
- All interactions via inline keyboards
"""

import asyncio
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from backend.config import settings
from backend.agents.example_search import example_search_agent
from backend.agents.review_quiz import review_quiz_agent
from backend.database.connection import get_db_session
from backend.database.models import Word, Review

# ============== KEYBOARD LAYOUTS ==============

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu with all primary actions."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Word", callback_data="menu_add"),
            InlineKeyboardButton("📚 My Words", callback_data="menu_words")
        ],
        [
            InlineKeyboardButton("🔄 Review", callback_data="menu_review"),
            InlineKeyboardButton("🎯 Quiz", callback_data="menu_quiz")
        ],
        [
            InlineKeyboardButton("📊 Statistics", callback_data="menu_stats"),
            InlineKeyboardButton("❓ Help", callback_data="menu_help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_add_word_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for add word flow."""
    keyboard = [
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_review_keyboard(word_id: int) -> InlineKeyboardMarkup:
    """SM-2 quality rating keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("😵 0", callback_data=f"review_{word_id}_0"),
            InlineKeyboardButton("😟 1", callback_data=f"review_{word_id}_1"),
            InlineKeyboardButton("😐 2", callback_data=f"review_{word_id}_2")
        ],
        [
            InlineKeyboardButton("🙂 3", callback_data=f"review_{word_id}_3"),
            InlineKeyboardButton("😊 4", callback_data=f"review_{word_id}_4"),
            InlineKeyboardButton("🤩 5", callback_data=f"review_{word_id}_5")
        ],
        [InlineKeyboardButton("⏭️ Skip", callback_data=f"review_{word_id}_skip")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quiz_keyboard(word_id: int, options: list, correct_index: int) -> InlineKeyboardMarkup:
    """Quiz multiple choice keyboard."""
    keyboard = []
    for i, option in enumerate(options):
        emoji = "🔘" if i == correct_index else "⚪"
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {option}",
            callback_data=f"quiz_{word_id}_{i}_{correct_index}"
        )])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)

def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Stats view keyboard."""
    keyboard = [
        [InlineKeyboardButton("📈 Overview", callback_data="stats_overview")],
        [InlineKeyboardButton("📅 Daily Progress", callback_data="stats_daily")],
        [InlineKeyboardButton("🔥 Streak", callback_data="stats_streak")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_words_list_keyboard(words: list, page: int = 0) -> InlineKeyboardMarkup:
    """Paginated word list keyboard."""
    keyboard = []
    per_page = 5
    start = page * per_page
    end = start + per_page

    for word in words[start:end]:
        keyboard.append([InlineKeyboardButton(
            f"📖 {word['word']} - {word['chinese_meaning'][:20] if word['chinese_meaning'] else '...'}",
            callback_data=f"word_detail_{word['id']}"
        )])

    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"words_page_{page-1}"))
    if end < len(words):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"words_page_{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)

def get_word_detail_keyboard(word_id: int) -> InlineKeyboardMarkup:
    """Word detail action keyboard."""
    keyboard = [
        [InlineKeyboardButton("🔊 Listen", callback_data=f"audio_{word_id}")],
        [InlineKeyboardButton("🔄 Review Now", callback_data=f"review_start_{word_id}")],
        [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{word_id}")],
        [InlineKeyboardButton("⬅️ Back to List", callback_data="menu_words")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============== AUDIO MESSAGE TRACKING ==============

async def _delete_audio_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Delete any tracked audio messages for this chat."""
    audio_message_ids = context.chat_data.get("audio_message_ids", [])
    for msg_id in audio_message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            # Message may already be deleted or too old
            print(f"Could not delete audio message {msg_id}: {e}")
    # Clear the list
    context.chat_data["audio_message_ids"] = []

async def _track_audio_message(context: ContextTypes.DEFAULT_TYPE, message_id: int):
    """Track an audio message ID so we can delete it later."""
    if "audio_message_ids" not in context.chat_data:
        context.chat_data["audio_message_ids"] = []
    context.chat_data["audio_message_ids"].append(message_id)

# ============== MESSAGE HANDLERS ==============

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - shows main menu."""
    # Clean up any lingering audio messages when starting fresh
    if update.effective_chat:
        await _delete_audio_messages(context, update.effective_chat.id)

    welcome_text = (
        "🎓 *Welcome to AI Vocabulary Assistant!*\n\n"
        "I help you learn English words with *real examples* from news sources like "
        "Reuters, BBC, The Guardian, and more.\n\n"
        "Choose an option below:"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode=None,
        reply_markup=get_main_menu_keyboard()
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle text messages based on user state.
    Used for: entering word to add, search, etc.
    """
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Check if user is in "waiting for word" state
    state = context.user_data.get("state")

    if state == "waiting_for_word_to_add":
        # User sent a word to add
        context.user_data["state"] = None
        await add_word_flow(update, context, text)

    elif state == "waiting_for_word_to_search":
        # User sent a word to search
        context.user_data["state"] = None
        await search_word_flow(update, context, text)

    else:
        # Default: treat as word to add with search
        await add_word_flow(update, context, text)

# ============== CALLBACK HANDLERS ==============

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all inline button callbacks."""
    query = update.callback_query
    await query.answer()  # Remove loading state

    data = query.data
    chat_id = query.message.chat_id

    # Main menu actions
    if data == "menu_main":
        await _delete_audio_messages(context, chat_id)
        await show_main_menu(query, context)
    elif data == "menu_add":
        await _delete_audio_messages(context, chat_id)
        await show_add_options(query, context)
    elif data == "menu_words":
        await _delete_audio_messages(context, chat_id)
        await show_words_list(query, context, page=0)
    elif data == "menu_review":
        await _delete_audio_messages(context, chat_id)
        await start_review_session(query, context)
    elif data == "menu_quiz":
        await _delete_audio_messages(context, chat_id)
        await start_quiz_session(query, context)
    elif data == "menu_stats":
        await _delete_audio_messages(context, chat_id)
        await show_stats_menu(query, context)
    elif data == "menu_help":
        await _delete_audio_messages(context, chat_id)
        await show_help(query, context)

    # Add word flow
    elif data == "add_search":
        await prompt_for_word(query, context, "search")
    elif data == "add_auto":
        await prompt_for_word(query, context, "auto")

    # Word list pagination
    elif data.startswith("words_page_"):
        page = int(data.split("_")[-1])
        await show_words_list(query, context, page=page)

    # Word detail
    elif data.startswith("word_detail_"):
        word_id = int(data.split("_")[-1])
        await show_word_detail(query, context, word_id)

    # Review
    elif data.startswith("review_start_"):
        word_id = int(data.split("_")[-1])
        await _delete_audio_messages(context, chat_id)
        await show_word_for_review(query, context, word_id)
    elif data.startswith("review_") and "_skip" not in data:
        parts = data.split("_")
        word_id = int(parts[1])
        quality = int(parts[2])
        await submit_review(query, context, word_id, quality)
    elif data.startswith("review_") and "_skip" in data:
        word_id = int(data.split("_")[1])
        await skip_review(query, context, word_id)

    # Quiz
    elif data.startswith("quiz_"):
        parts = data.split("_")
        word_id = int(parts[1])
        selected = int(parts[2])
        correct = int(parts[3])
        await handle_quiz_answer(query, context, word_id, selected, correct)

    # Audio
    elif data.startswith("audio_"):
        word_id = int(data.split("_")[-1])
        await send_audio(query, context, word_id)

    # Delete
    elif data.startswith("delete_"):
        word_id = int(data.split("_")[-1])
        await confirm_delete(query, context, word_id)
    elif data.startswith("confirm_delete_"):
        word_id = int(data.split("_")[-1])
        await delete_word(query, context, word_id)

    # Stats
    elif data == "stats_overview":
        await show_stats_overview(query, context)
    elif data == "stats_daily":
        await show_daily_stats(query, context)
    elif data == "stats_streak":
        await show_streak(query, context)

# ============== FLOW IMPLEMENTATIONS ==============

async def show_main_menu(query, context):
    """Show main menu."""
    text = (
        "🎓 *AI Vocabulary Assistant*\n\n"
        "What would you like to do?"
    )
    await query.edit_message_text(
        text,
        parse_mode=None,
        reply_markup=get_main_menu_keyboard()
    )

async def show_add_options(query, context):
    """Show add word options."""
    text = (
        "➕ *Add a New Word*\n\n"
        "🔍 *Search Real Examples* - Find authentic sentences from Reuters, BBC, etc.\n"
    )
    await query.edit_message_text(
        text,
        parse_mode=None,
        reply_markup=get_add_word_keyboard()
    )

async def prompt_for_word(query, context, mode: str):
    """Prompt user to enter a word."""
    context.user_data["add_mode"] = mode
    context.user_data["state"] = "waiting_for_word_to_add"

    text = (
        "✏️ *Enter a word*\n\n"
        "Type the English word you want to add:\n"
        "_Example: sanction, abandon, resilient_"
    )
    await query.edit_message_text(
        text,
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Cancel", callback_data="menu_main")]])
    )

async def add_word_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, word: str):
    """Execute add word flow with agent."""
    mode = context.user_data.get("add_mode", "search")

    # Send processing message
    processing_msg = await update.message.reply_text(
        f"🔍 Searching for real examples of '*{word}*'...\n"
        f"⏳ This may take 10-20 seconds...",
        parse_mode=None
    )

    try:
        # Run Example Search Agent
        result = example_search_agent.run(word=word)

        # Check for actual success (success=True AND word is a dict)
        if not result.get("success") or isinstance(result.get("word"), str):
            error_msg = result.get('error', f"No articles found for '{word}'")
            await processing_msg.edit_text(
                f"❌ *Error:* {error_msg}\n\n"
                f"Try another word or check your API keys.",
                parse_mode=None,
                reply_markup=get_main_menu_keyboard()
            )
            return

        # Now word_data is definitely a dict
        word_data = result["word"]

        # Format response
        response = (
            f"✅ *Word Added: {word_data['word'].upper()}*\n\n"
            f"📌 *Phonetic:* {word_data.get('phonetic', 'N/A')}\n"
            f"📌 *POS:* {word_data.get('part_of_speech', 'N/A')}\n"
            f"📌 *Meaning:* {word_data.get('chinese_meaning', 'N/A')}\n\n"
            f"📝 *Example:*\n"
            f"_{word_data.get('example_sentence', 'N/A')}_\n\n"
            f"🌐 *Translation:*\n"
            f"{word_data.get('chinese_translation', 'N/A')}\n\n"
            f"📰 *Source:* {word_data.get('source_name', 'N/A')}\n"
            f"🔗 [Read Article]({word_data.get('source_url', '')})\n"
        )

        if word_data.get("collocations"):
            response += f"\n🔗 *Collocations:* {', '.join(word_data['collocations'])}"
        if word_data.get("synonyms"):
            response += f"\n🔄 *Synonyms:* {', '.join(word_data['synonyms'])}"
        if word_data.get("antonyms"):
            response += f"\n🔀 *Antonyms:* {', '.join(word_data['antonyms'])}"

        await processing_msg.edit_text(
            response,
            parse_mode=None,
            reply_markup=get_main_menu_keyboard(),
            disable_web_page_preview=True
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        await processing_msg.edit_text(
            f"❌ *Error:* {str(e)}\n\nPlease try again.",
            parse_mode=None,
            reply_markup=get_main_menu_keyboard()
        )

async def search_word_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, word: str):
    """Search for existing word in database."""
    db = get_db_session()
    try:
        db_word = db.query(Word).filter(Word.word == word.lower()).first()

        if not db_word:
            await update.message.reply_text(
                f"❌ Word '*{word}*' not found in your vocabulary.\n\n"
                f"Would you like to add it?",
                parse_mode=None,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Add This Word", callback_data="menu_add")],
                    [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")]
                ])
            )
            return

        # Show word detail
        response = (
            f"📖 *{db_word.word.upper()}*\n\n"
            f"📌 *Phonetic:* {db_word.phonetic or 'N/A'}\n"
            f"📌 *POS:* {db_word.part_of_speech or 'N/A'}\n"
            f"📌 *Meaning:* {db_word.chinese_meaning or 'N/A'}\n\n"
            f"📝 *Example:*\n_{db_word.example_sentence or 'N/A'}_\n\n"
            f"🌐 *Translation:* {db_word.chinese_translation or 'N/A'}\n\n"
            f"📰 *Source:* {db_word.source_name or 'N/A'}"
        )

        await update.message.reply_text(
            response,
            parse_mode=None,
            reply_markup=get_word_detail_keyboard(db_word.id),
            disable_web_page_preview=True
        )

    finally:
        db.close()

async def show_words_list(query, context, page: int = 0):
    """Show paginated list of user's words."""
    db = get_db_session()
    try:
        words = db.query(Word).all()

        if not words:
            await query.edit_message_text(
                "📭 *Your vocabulary is empty!*\n\n"
                "Start by adding your first word.",
                parse_mode=None,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Add Word", callback_data="menu_add")],
                    [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")]
                ])
            )
            return

        word_list = [
            {
                "id": w.id,
                "word": w.word,
                "chinese_meaning": w.chinese_meaning or ""
            }
            for w in words
        ]

        total_pages = (len(word_list) + 4) // 5

        text = (
            f"📚 *Your Vocabulary* (Page {page + 1}/{total_pages})\n"
            f"Total: {len(word_list)} words\n\n"
            f"Tap a word to see details:"
        )

        await query.edit_message_text(
            text,
            parse_mode=None,
            reply_markup=get_words_list_keyboard(word_list, page)
        )

    finally:
        db.close()

async def show_word_detail(query, context, word_id: int):
    """Show detailed view of a word."""
    db = get_db_session()
    try:
        word = db.query(Word).filter(Word.id == word_id).first()
        if not word:
            await query.edit_message_text(
                "❌ Word not found.",
                reply_markup=get_main_menu_keyboard()
            )
            return

        text = (
            f"📖 *{word.word.upper()}*\n\n"
            f"📌 *Phonetic:* {word.phonetic or 'N/A'}\n"
            f"📌 *POS:* {word.part_of_speech or 'N/A'}\n"
            f"📌 *Meaning:* {word.chinese_meaning or 'N/A'}\n\n"
            f"📝 *Example:*\n_{word.example_sentence or 'N/A'}_\n\n"
            f"🌐 *Translation:* {word.chinese_translation or 'N/A'}\n\n"
            f"📰 *Source:* {word.source_name or 'N/A'}"
        )

        if word.collocations:
            text += f"\n🔗 *Collocations:* {', '.join(word.collocations)}"
        if word.synonyms:
            text += f"\n🔄 *Synonyms:* {', '.join(word.synonyms)}"
        if word.antonyms:
            text += f"\n🔀 *Antonyms:* {', '.join(word.antonyms)}"

        await query.edit_message_text(
            text,
            parse_mode=None,
            reply_markup=get_word_detail_keyboard(word_id),
            disable_web_page_preview=True
        )

    finally:
        db.close()

async def start_review_session(query, context):
    """Start review session with due words."""
    result = review_quiz_agent.run(action="get_due")

    if not result.get("success") or result.get("due_count", 0) == 0:
        await query.edit_message_text(
            "🎉 *No words due for review!*\n\n"
            "You've completed all your reviews. Great job! 🌟",
            parse_mode=None,
            reply_markup=get_main_menu_keyboard()
        )
        return

    due_words = result["due_words"]
    context.user_data["review_queue"] = due_words
    context.user_data["review_index"] = 0

    await show_next_review_word(query, context)
async def show_word_for_review(query, context, word_id: int):
    """Show a specific word for review (from word detail 'Review Now' button)."""
    db = get_db_session()
    try:
        word = db.query(Word).filter(Word.id == word_id).first()
        if not word:
            await query.edit_message_text(
                "❌ Word not found.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Get or create review record
        review = db.query(Review).filter(Review.word_id == word_id).first()
        if not review:
            review = Review(
                word_id=word_id,
                interval=1,
                ease_factor=2.5,
                repetitions=0,
                is_due=True,
                next_review_date=None
            )
            db.add(review)
            db.commit()
        
        # Set up single-word review queue
        context.user_data["review_queue"] = [{
            "word_id": word.id,
            "word": word.word,
            "chinese_meaning": word.chinese_meaning or "",
            "example_sentence": word.example_sentence or ""
        }]
        context.user_data["review_index"] = 0
        
        # Show the word for review
        await show_next_review_word(query, context)
        
    finally:
        db.close()
async def show_next_review_word(query, context):
    """Show the next word in review queue."""
    queue = context.user_data.get("review_queue", [])
    index = context.user_data.get("review_index", 0)

    if index >= len(queue):
        # Review session complete
        await query.edit_message_text(
            f"🎉 *Review Complete!*\n\n"
            f"You reviewed {len(queue)} words today.\n"
            f"Keep up the great work! 🌟",
            parse_mode=None,
            reply_markup=get_main_menu_keyboard()
        )
        context.user_data["review_queue"] = []
        context.user_data["review_index"] = 0
        return

    word = queue[index]

    text = (
        f"🔄 *Review ({index + 1}/{len(queue)})*\n\n"
        f"📖 *{word['word'].upper()}*\n"
        f"📌 {word['chinese_meaning']}\n\n"
        f"📝 *Example:*\n_{word['example_sentence']}_\n\n"
        f"How well did you remember this word?"
    )

    await query.edit_message_text(
        text,
        parse_mode=None,
        reply_markup=get_review_keyboard(word["word_id"])
    )

async def submit_review(query, context, word_id: int, quality: int):
    """Submit review quality and show next word."""
    result = review_quiz_agent.run(
        action="review",
        word_id=word_id,
        quality=quality
    )

    # Move to next word
    context.user_data["review_index"] = context.user_data.get("review_index", 0) + 1

    # Show brief feedback
    emoji = ["😵", "😟", "😐", "🙂", "😊", "🤩"][quality]

    await query.edit_message_text(
        f"{emoji} *Rated {quality}/5*\n\n"
        f"{result.get('message', 'Review saved!')}\n\n"
        f"Loading next word...",
        parse_mode=None
    )

    await asyncio.sleep(1)
    await show_next_review_word(query, context)

async def skip_review(query, context, word_id: int):
    """Skip current review word."""
    context.user_data["review_index"] = context.user_data.get("review_index", 0) + 1
    await show_next_review_word(query, context)

async def start_quiz_session(query, context):
    """Start quiz session."""
    result = review_quiz_agent.run(action="quiz")

    if not result.get("success") or not result.get("quiz"):
        await query.edit_message_text(
            "🎯 *No quiz available!*\n\n"
            "Add some words first to generate quizzes.",
            parse_mode=None,
            reply_markup=get_main_menu_keyboard()
        )
        return

    quiz_questions = result["quiz"]
    context.user_data["quiz_queue"] = quiz_questions
    context.user_data["quiz_index"] = 0
    context.user_data["quiz_score"] = 0

    await show_next_quiz_question(query, context)

async def show_next_quiz_question(query, context):
    """Show next quiz question."""
    queue = context.user_data.get("quiz_queue", [])
    index = context.user_data.get("quiz_index", 0)

    if index >= len(queue):
        # Quiz complete
        score = context.user_data.get("quiz_score", 0)
        total = len(queue)
        percentage = round(score / total * 100) if total > 0 else 0

        await query.edit_message_text(
            f"🎯 *Quiz Complete!*\n\n"
            f"Score: {score}/{total} ({percentage}%)\n\n"
            f"{'🌟 Excellent!' if percentage >= 80 else '👍 Good job!' if percentage >= 60 else '💪 Keep practicing!'}\n\n"
            f"Review the words you missed to improve!",
            parse_mode=None,
            reply_markup=get_main_menu_keyboard()
        )
        context.user_data["quiz_queue"] = []
        return

    question = queue[index]

    text = (
        f"🎯 *Quiz Question {index + 1}/{len(queue)}*\n\n"
        f"{question['question']}\n\n"
        f"Choose the correct answer:"
    )

    await query.edit_message_text(
        text,
        parse_mode=None,
        reply_markup=get_quiz_keyboard(
            question["word_id"],
            question["options"],
            question["correct_index"]
        )
    )

async def handle_quiz_answer(query, context, word_id: int, selected: int, correct: int):
    """Handle quiz answer selection."""
    is_correct = selected == correct

    if is_correct:
        context.user_data["quiz_score"] = context.user_data.get("quiz_score", 0) + 1
        emoji = "✅"
        text = f"{emoji} *Correct!* 🎉\n\n"
    else:
        emoji = "❌"
        text = f"{emoji} *Incorrect*\n\n"

    # Get current question for explanation
    queue = context.user_data.get("quiz_queue", [])
    index = context.user_data.get("quiz_index", 0)

    if index < len(queue):
        question = queue[index]
        text += f"💡 *Explanation:* {question.get('explanation', 'Review this word for better understanding.')}\n\n"

    text += "Loading next question..."

    await query.edit_message_text(
        text,
        parse_mode=None
    )

    # Update review based on correctness
    quality = 4 if is_correct else 1
    review_quiz_agent.run(action="review", word_id=word_id, quality=quality)

    await asyncio.sleep(2)
    context.user_data["quiz_index"] = index + 1
    await show_next_quiz_question(query, context)

async def show_stats_menu(query, context):
    """Show statistics menu."""
    text = (
        "📊 *Statistics*\n\n"
        "Choose what to view:"
    )
    await query.edit_message_text(
        text,
        parse_mode=None,
        reply_markup=get_stats_keyboard()
    )

async def show_stats_overview(query, context):
    """Show overview statistics."""
    result = review_quiz_agent.run(action="stats")

    if not result.get("success"):
        await query.edit_message_text(
            "❌ Failed to load statistics.",
            reply_markup=get_stats_keyboard()
        )
        return

    stats = result["stats"]

    text = (
        f"📊 *Learning Overview*\n\n"
        f"📚 Total Words: {stats['total_words']}\n"
        f"✅ Learned: {stats['learned_words']}\n"
        f"📈 Learning Rate: {stats['learning_rate']}%\n\n"
        f"🔄 Due Today: {stats['due_today']}\n"
        f"📅 Weekly Reviews: {stats['weekly_reviews']}\n"
        f"⭐ Average Quality: {stats['average_quality']}\n\n"
        f"🔥 Current Streak: {stats['current_streak']} days\n"
        f"🏆 Mastery Level: {stats['mastery_level']}"
    )

    await query.edit_message_text(
        text,
        parse_mode=None,
        reply_markup=get_stats_keyboard()
    )

async def show_daily_stats(query, context):
    """Show daily progress chart (text-based)."""
    text = (
        "📅 *Daily Progress*\n\n"
        "Last 7 days activity:\n\n"
        "📈 Coming soon: detailed daily charts!\n\n"
        "Use the web app for full visual statistics."
    )
    await query.edit_message_text(
        text,
        parse_mode=None,
        reply_markup=get_stats_keyboard()
    )

async def show_streak(query, context):
    """Show streak information."""
    result = review_quiz_agent.run(action="stats")
    streak = result.get("stats", {}).get("current_streak", 0) if result.get("success") else 0

    text = (
        f"🔥 *Learning Streak*\n\n"
        f"Current Streak: *{streak} days*\n\n"
        f"{'🌟 Amazing consistency! Keep it up!' if streak >= 7 else '💪 Keep reviewing daily to build your streak!' if streak >= 3 else '📚 Start your streak by reviewing words today!'}"
    )

    await query.edit_message_text(
        text,
        parse_mode=None,
        reply_markup=get_stats_keyboard()
    )

async def send_audio(query, context, word_id: int):
    """Send TTS audio for a word as Telegram voice message."""
    db = get_db_session()
    try:
        word = db.query(Word).filter(Word.id == word_id).first()
        if not word:
            await query.answer("Word not found!")
            return

        # Use gTTS to generate audio
        try:
            from gtts import gTTS
            import tempfile
            import os

            # Create temporary MP3 file
            text_to_speak = f"{word.word}. {word.example_sentence or ''}"
            tts = gTTS(text=text_to_speak, lang='en', slow=False)

            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                tts.save(fp.name)
                audio_path = fp.name

            # Send as voice message to Telegram
            sent_message = await context.bot.send_voice(
                chat_id=query.message.chat_id,
                voice=open(audio_path, 'rb'),
                caption=f"🔊 {word.word.upper()} — [{word.phonetic or 'N/A'}]"
            )

            # TRACK the audio message ID so we can delete it later
            await _track_audio_message(context, sent_message.message_id)

            # Cleanup temp file
            os.remove(audio_path)

            # Answer the callback query
            await query.answer("Audio sent!")

        except ImportError:
            await query.answer("TTS not installed. Run: pip install gtts")

        except Exception as e:
            print(f"Audio error: {e}")
            await query.answer("Failed to generate audio")
    finally:
        db.close()

async def confirm_delete(query, context, word_id: int):
    """Show delete confirmation."""
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{word_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"word_detail_{word_id}")]
    ]

    await query.edit_message_text(
        "🗑️ *Delete Word?*\n\n"
        "Are you sure you want to delete this word?\n"
        "This action cannot be undone.",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def delete_word(query, context, word_id: int):
    """Delete word from database."""
    db = get_db_session()
    try:
        word = db.query(Word).filter(Word.id == word_id).first()
        if word:
            word_name = word.word
            db.delete(word)
            db.commit()

            await query.edit_message_text(
                f"✅ *Deleted:* {word_name}\n\n"
                f"Word removed from your vocabulary.",
                parse_mode=None,
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ Word not found.",
                reply_markup=get_main_menu_keyboard()
            )
    finally:
        db.close()

async def show_help(query, context):
    """Show help information."""
    text = (
        "❓ *How to Use*\n\n"
        "*Add Words:*\n"
        "Tap 'Add Word' → Choose 'Search Real Examples' → Type your word\n"
        "The bot will find real sentences from news sources!\n\n"
        "*Review:*\n"
        "Tap 'Review' to see words due today.\n"
        "Rate how well you remembered each word (0-5).\n\n"
        "*Quiz:*\n"
        "Tap 'Quiz' for multiple choice questions.\n\n"
        "*Stats:*\n"
        "Track your learning progress and streak.\n\n"
        "*Tips:*\n"
        "• Review daily to build your streak 🔥\n"
        "• Use real examples for better memory\n"
        "• Quiz yourself regularly"
    )

    await query.edit_message_text(
        text,
        parse_mode=None,
        reply_markup=get_main_menu_keyboard()
    )

# ============== WEBHOOK HANDLER ==============

async def handle_update(update_data: dict):
    """Handle webhook updates from Telegram."""
    application = create_bot_application()
    await application.initialize()
    update = Update.de_json(update_data, application.bot)
    await application.process_update(update)

# ============== BOT INITIALIZATION ==============

def create_bot_application() -> Application:
    """Create and configure the bot application."""
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))

    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(handle_callback))

    return application

async def start_bot():
    """Start the bot with polling."""
    application = create_bot_application()

    print("🤖 Telegram Bot starting...")
    print(" Use /start to see the main menu with buttons!")

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await application.stop()

if __name__ == "__main__":
    asyncio.run(start_bot())