import logging
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from translate import Translator  # Using translate library instead of deep_translator
from dotenv import load_dotenv
import json
import os

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Read variables from .env
TOKEN = os.getenv("API")
SOURCE_CHANNEL = int(os.getenv("Orchuulagch"))
DESTINATION_CHANNEL = int(os.getenv("Huleen_Avagch"))

# Translator instance using the translate library
translator = Translator(from_lang="en", to_lang="mn")


# Load forex terms from external JSON file
def load_forex_terms(file_path="forex_terms.json"):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            forex_terms = json.load(file)
            return forex_terms
    except FileNotFoundError:
        logger.error(f"Forex terms file '{file_path}' not found.")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON in '{file_path}': {e}")
        return {}


# Load terms and create reverse mapping
forex_terms = load_forex_terms()
forex_terms_reverse = {v: k for k, v in forex_terms.items()}


def custom_translate(text: str) -> str:
    """
    Translate the text to Mongolian by splitting into chunks if necessary.
    """
    # If text is within the limit, translate directly
    if len(text) <= 500:
        return translator.translate(text)

    # Split the text by newlines to create logical chunks
    lines = text.split("\n")
    translated_lines = []
    current_chunk = ""

    for line in lines:
        # If adding this line would exceed our limit, translate what we have so far
        if len(current_chunk) + len(line) + 1 > 450:  # Leave some margin
            if current_chunk:
                translated_lines.append(translator.translate(current_chunk))
                current_chunk = line
            else:
                # If a single line is too long, split it further
                for i in range(0, len(line), 400):
                    chunk = line[i : i + 400]
                    translated_lines.append(translator.translate(chunk))
        else:
            # Add to current chunk if it fits
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line

    # Don't forget to translate the last chunk
    if current_chunk:
        translated_lines.append(translator.translate(current_chunk))

    # Join all translated parts
    return "\n".join(translated_lines)


def replace_forex_terms(text: str) -> str:
    """
    Replace the translated forex terms back to English.
    """
    for term_mn, term_en in forex_terms.items():
        # For terms containing special characters like emojis, we need a different approach
        # than word boundaries
        if any(char in term_mn for char in "💰📊🔥👉📈✅🔴🟢🔹"):
            # Use literal string replacement instead of regex with word boundaries
            text = text.replace(term_mn, term_en)
        else:
            # For normal terms use word boundaries to avoid partial matches
            text = re.sub(rf"\b{re.escape(term_mn)}\b", term_en, text)
    return text


def is_nullified_trade_message(text: str) -> bool:
    """
    Checks if the message is a nullified trade message.
    """
    text = text.replace("\n", " ")
    pattern = re.compile(r"will be considered as NULL", re.UNICODE)
    return bool(pattern.search(text))


def extract_trade_details(text: str) -> dict:
    """
    Extracts trade details from the message.
    """
    # Try to find pattern with ➕ first
    trade_pair_match = re.search(
        r"\➕(.*?) will be considered as NULL", text, re.DOTALL
    )

    # If not found, try without the ➕ symbol
    if not trade_pair_match:
        trade_pair_match = re.search(
            r"([\w]+/[\w]+) will be considered as NULL", text, re.DOTALL
        )

    if trade_pair_match:
        trade_pair = trade_pair_match.group(1).strip()
        if "/" in trade_pair:
            base_currency, quote_currency = trade_pair.split("/")
        else:
            base_currency = trade_pair
            quote_currency = "Unknown"
    else:
        trade_pair = "Unknown"
        base_currency = "Unknown"
        quote_currency = "Unknown"

    profit_percent_match = re.search(r"\((.*?)%\s+PROFIT", text)
    if profit_percent_match:
        profit_percent = profit_percent_match.group(1).strip()
    else:
        profit_percent = "Unknown"

    return {
        "trade_pair": trade_pair,
        "base_currency": base_currency,
        "profit_percent": profit_percent,
    }


def custom_translate_nullified_trade(text: str) -> str:
    """
    Translates a nullified trade message into the desired format.
    """
    details = extract_trade_details(text)
    trade_pair = details["trade_pair"]
    profit_percent = details["profit_percent"]
    base_currency = details["base_currency"]

    translated_message = (
        f"➕{trade_pair}-г арилжаа цуцлагдсан. ({profit_percent}% Aшиг/Aлдагдал)\n\n"
        f"➡️{base_currency} нь арилжаанд орох ханшинд хүрэхээс өмнө SL цохьсон байна."
    )
    return translated_message


def process_text(message_text: str) -> str:
    """
    Process the message text to filter out unwanted content.
    """
    # Filter out promotional messages
    if re.search(
        r"\b(Ad|altcoin|apology|sorry|support|recover|candle|risk|luck|refer|paypal|positive|subscription|appreciating|movements|market|markets|tests|test|yes)\b",
        message_text,
        re.IGNORECASE,
    ):
        logger.info("Skipping promotional message.")
        return None

    # Replace green hearts with dollar emojis (if needed)
    filtered_text = message_text.replace("💚", "💵")

    # Remove content below the horizontal line
    parts = re.split(r"[-—_]{3,}", filtered_text)
    filtered_text = parts[0].strip()

    # Remove the 📊 emoji
    filtered_text = filtered_text.replace("📊", "")

    # Remove content after fire emoji (if needed)
    if "🔥" in filtered_text:
        parts = filtered_text.split("🔥", 1)
        filtered_text = parts[0].strip() + "🔥"

    # Remove guide and weblink
    filtered_text = re.sub(
        r"📚Guide:.*$", "", filtered_text, flags=re.MULTILINE
    ).strip()

    # Remove everything after the ⚠️ emoji (including the emoji itself)
    filtered_text = re.sub(
        r"^(?=.*⚠️)(?!.*\bSL\b)(?!.*Stop Loss)(?!.*Take Profit)(?!.*\bTP\b).*$",
        "",
        filtered_text,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    # Remove everything after the 👋 emoji (including the emoji itself)
    filtered_text = re.sub(r"👋.*$", "", filtered_text, flags=re.MULTILINE).strip()

    # Remove everything after the 🐺 emoji (including the emoji itself)
    filtered_text = re.sub(r"🐺.*$", "", filtered_text, flags=re.MULTILINE).strip()

    # Remove everything after the ⭐️ emoji (including the emoji itself)
    filtered_text = re.sub(r"⭐️.*$", "", filtered_text, flags=re.MULTILINE).strip()

    # Remove everything after the 👉 emoji (including the emoji itself)
    filtered_text = re.sub(r"👉.*$", "", filtered_text, flags=re.MULTILINE).strip()

    # Remove everything after the • emoji (including the emoji itself)
    filtered_text = re.sub(r"•.*$", "", filtered_text, flags=re.MULTILINE).strip()

    # Remove everything after the ✉️ emoji (including the emoji itself)
    filtered_text = re.sub(r"✉️.*$", "", filtered_text, flags=re.MULTILINE).strip()

    # Remove everything after the 🟢 emoji (including the emoji itself)
    filtered_text = re.sub(r"🟢.*$", "", filtered_text, flags=re.MULTILINE).strip()

    # Remove any text that contains 'WOLFXSIGNALS.COM'
    filtered_text = re.sub(r"(?i).*WOLFXSIGNALS\.COM.*", "", filtered_text).strip()

    # Remove any line that contains '@WOLFX_SIGNALS'
    filtered_text = re.sub(r"(?i)^.*@WOLFX_SIGNALS.*\n?", "", filtered_text)

    # Remove any line that contains '@WolFX_Signals' (case-insensitive)
    filtered_text = re.sub(
        r"(?i)^.*@WolFX_Signals.*\n?", "", filtered_text, flags=re.MULTILINE
    )

    # Remove any line containing the word "wolf" (case-insensitive, even as part of a larger word)
    filtered_text = re.sub(r"(?i)^.*wolf.*\n?", "", filtered_text, flags=re.MULTILINE)

    # Remove trailing or unnecessary whitespace
    filtered_text = filtered_text.strip()

    return filtered_text if filtered_text else None


def is_signal_message(text: str) -> bool:
    """
    Determine if a message is a signal message based on its format.
    """
    return bool(re.search(r"\b(BUY|SELL|Buy|Sell\d+)\b", text))


async def copy_and_translate_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    try:
        if update.channel_post and update.channel_post.chat_id == SOURCE_CHANNEL:
            original_message = update.channel_post

            if original_message.text:
                processed_text = process_text(original_message.text)
                if processed_text:
                    if is_nullified_trade_message(processed_text):
                        logger.info("Nullified trade message detected.")
                        translated_text = custom_translate_nullified_trade(
                            processed_text
                        )
                        logger.info(f"Translated text: {translated_text}")
                    else:
                        logger.info("Default translation path.")
                        translated_text = custom_translate(processed_text)
                        translated_text = replace_forex_terms(translated_text)
                        logger.info(f"Translated text: {translated_text}")

                    # Check if the message is a signal message
                    if is_signal_message(translated_text):
                        translated_text += " \n\n ❗️Арилжаанд орох хамгийн дээд ханшнаас дээгүүр орсон тохиолдолд энэхүү арилжаа нь манай сувгийн signal-тай нийцэхгүй."

                    # Append the promotional text
                    translated_text = translated_text.replace(" -г ", "")
                    translated_text = translated_text.replace("-г ", "")
                    translated_text = translated_text.replace("📉", "")
                    translated_text = translated_text.replace("📈", "")
                    # First, remove checkmarks at the beginning of any line
                    translated_text = re.sub(
                        r"(^|\n)\s*✅✅\s+", r"\1", translated_text
                    )

                    # Then, ensure that any "Take Profit" lines that have checkmarks at the end keep them
                    # (this is just to maintain the pattern you showed)
                    translated_text = re.sub(
                        r"(Take Profit \d+)(?!\s*✅✅)$",
                        r"\1 ✅✅",
                        translated_text,
                        flags=re.MULTILINE,
                    )
                    # Add the closing part
                    translated_text += " \n\n 💸💸💸 Plus-Mongolia-Signal 💰💰💰"

                    await context.bot.send_message(
                        chat_id=DESTINATION_CHANNEL,
                        text=translated_text,
                        parse_mode=None,
                    )
            elif original_message.caption and original_message.photo:
                processed_caption = process_text(original_message.caption)
                if processed_caption:
                    if is_nullified_trade_message(processed_caption):
                        translated_caption = custom_translate_nullified_trade(
                            processed_caption
                        )
                        logger.info(f"Translated caption: {translated_caption}")
                    else:
                        translated_caption = custom_translate(processed_caption)
                        translated_caption = replace_forex_terms(translated_caption)
                        logger.info(f"Translated caption: {translated_caption}")

                    # Check if the message is a signal message
                    if is_signal_message(translated_caption):
                        translated_caption += " \n\n ❗️Арилжаанд орох хамгийн дээд ханшнаас дээгүүр орсон тохиолдолд энэхүү арилжаа нь манай сувгийн signal-тай нийцэхгүй."

                    # Append the promotional text
                    translated_caption += " \n\n 💸💸💸 Plus-Mongolia-Signal 💰💰💰"

                    await context.bot.send_message(
                        chat_id=DESTINATION_CHANNEL,
                        text=translated_caption,
                        parse_mode=None,
                    )
            logger.info("Message processed, translated, and copied successfully.")
    except Exception as e:
        logger.error(f"Error translating or copying message: {e}")


def main():
    # Create the bot application
    application = Application.builder().token(TOKEN).build()

    # Add a message handler to handle posts in the source channel
    application.add_handler(
        MessageHandler(filters.UpdateType.CHANNEL_POST, copy_and_translate_message)
    )

    # Run the bot
    logger.info("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
