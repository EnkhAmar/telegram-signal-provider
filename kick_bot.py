import logging
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application,
    ChatMemberHandler,
    ContextTypes,
    PicklePersistence,
)
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TG_KICKER_BOT_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

# Dictionary to store join dates for users
# Will be persisted between restarts
USER_JOIN_DATES = {}


async def track_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new channel joins"""
    try:
        chat_member = update.chat_member
        if not chat_member:
            return

        if str(chat_member.chat.id) != CHAT_ID:
            return

        user = chat_member.new_chat_member.user
        if chat_member.new_chat_member.status == "member":
            user_id = user.id
            join_time = datetime.now(pytz.utc)
            join_date_str = join_time.strftime("%Y-%m-%d %H:%M:%S %Z")

            # Enhanced logging with border
            logger.info("\n" + "=" * 50)
            logger.info(f"\U0001f6a8 NEW USER DETECTED \U0001f6a8")
            logger.info(f"\U0001f194 User ID: {user_id}")
            logger.info(f"\U0001f4c5 Joined At: {join_date_str}")
            logger.info("=" * 50 + "\n")

            # Store join date in our dictionary
            USER_JOIN_DATES[user_id] = join_time

            # Save the data in context.bot_data which is persisted
            context.bot_data["user_join_dates"] = USER_JOIN_DATES

            # Schedule removal using the job queue
            context.job_queue.run_once(
                callback=remove_user,
                when=timedelta(days=30),  # Schedule for 30 days later
                data={"user_id": user_id, "chat_id": CHAT_ID},
                name=f"remove_user_{user_id}",
            )
            logger.info(f"Scheduled removal for user {user_id} in 30 days")

    except Exception as e:
        logger.error(f"Error in track_join: {e}", exc_info=True)


async def remove_user(context: ContextTypes.DEFAULT_TYPE):
    """Remove user after scheduled time"""
    try:
        job_data = context.job.data
        user_id = job_data["user_id"]
        chat_id = job_data["chat_id"]

        logger.info(f"Removing user {user_id} from chat {chat_id}")

        # Ban and then unban to remove from group
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)

        # Remove from our tracking dictionary
        if user_id in USER_JOIN_DATES:
            del USER_JOIN_DATES[user_id]
            # Update the persisted data
            context.bot_data["user_join_dates"] = USER_JOIN_DATES
            logger.info(f"Successfully removed user {user_id}")

    except Exception as e:
        logger.error(f"Remove user error: {e}", exc_info=True)


async def check_expired_users(context: ContextTypes.DEFAULT_TYPE):
    """Safety check for expired users"""
    try:
        now = datetime.now(pytz.utc)

        # Get our dictionary from bot_data
        join_dates = context.bot_data.get("user_join_dates", {})

        # Make a copy to avoid modification during iteration
        for user_id, join_time in list(join_dates.items()):
            # Check if it's past the expiration time
            if (now - join_time) > timedelta(days=30):  # 30 days for production
                try:
                    logger.info(f"Found expired user {user_id}, removing")
                    await context.bot.ban_chat_member(chat_id=CHAT_ID, user_id=user_id)
                    await context.bot.unban_chat_member(
                        chat_id=CHAT_ID, user_id=user_id
                    )

                    # Remove from our tracking dictionary
                    del USER_JOIN_DATES[user_id]
                    # Update the persisted data
                    context.bot_data["user_join_dates"] = USER_JOIN_DATES

                    logger.info(f"Cleaned up expired user {user_id}")
                except Exception as e:
                    logger.error(
                        f"Cleanup error for user {user_id}: {e}", exc_info=True
                    )

    except Exception as e:
        logger.error(f"Error in check_expired_users: {e}", exc_info=True)


async def post_init(application: Application):
    """Run after application initialization to handle any startup tasks"""
    logger.info("Performing post-initialization tasks")

    # Restore the user join dates from persisted bot_data
    global USER_JOIN_DATES
    USER_JOIN_DATES = application.bot_data.get("user_join_dates", {})

    logger.info(f"Restored {len(USER_JOIN_DATES)} user join dates from persistence")

    # Reschedule any pending removals based on stored user data
    now = datetime.now(pytz.utc)

    for user_id, join_time in list(USER_JOIN_DATES.items()):
        # Calculate remaining time
        elapsed = now - join_time
        removal_time = timedelta(days=30) - elapsed  # 30 days for production

        # If time has already passed, remove immediately
        if removal_time.total_seconds() <= 0:
            logger.info(f"User {user_id} already expired, removing now")
            try:
                await application.bot.ban_chat_member(chat_id=CHAT_ID, user_id=user_id)
                await application.bot.unban_chat_member(
                    chat_id=CHAT_ID, user_id=user_id
                )

                # Remove from our tracking dictionary
                del USER_JOIN_DATES[user_id]
                # Update the persisted data
                application.bot_data["user_join_dates"] = USER_JOIN_DATES

                logger.info(f"Removed expired user {user_id} on startup")
            except Exception as e:
                logger.error(
                    f"Error removing user {user_id} on startup: {e}", exc_info=True
                )
        else:
            # Schedule remaining time
            logger.info(f"Rescheduling removal for user {user_id} in {removal_time}")
            application.job_queue.run_once(
                callback=remove_user,
                when=removal_time,
                data={"user_id": user_id, "chat_id": CHAT_ID},
                name=f"remove_user_{user_id}",
            )


def main():
    """Start the bot with persistence support"""
    # Initialize persistence with a pickle file
    persistence = PicklePersistence(filepath="bot_data.pickle")

    # Build the application with persistence enabled
    application = (
        Application.builder()
        .token(TOKEN)
        .persistence(persistence)
        .post_init(post_init)
        .build()
    )

    # Add the ChatMemberHandler
    application.add_handler(
        ChatMemberHandler(track_join, ChatMemberHandler.CHAT_MEMBER)
    )

    # Add a repeating job to check for expired users
    application.job_queue.run_repeating(
        check_expired_users, interval=timedelta(days=1), first=10
    )

    logger.info("Bot started with job queue support and persistence")
    application.run_polling(allowed_updates=["message", "chat_member"])


if __name__ == "__main__":
    main()
