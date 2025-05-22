import os
from dotenv import load_dotenv
import asyncio
from flask import Flask
from threading import Thread
from bot_selector import BotSelector
from run_bots import CharacterBot
from database_manager import DatabaseManager
from config import CHARACTER_INFO

# Load environment variables
load_dotenv()

# Get bot tokens from environment variables
SELECTOR_TOKEN = os.getenv('SELECTOR_TOKEN')
KAGARI_TOKEN = os.getenv('KAGARI_TOKEN')
EROS_TOKEN = os.getenv('EROS_TOKEN')
ELYSIA_TOKEN = os.getenv('ELYSIA_TOKEN')

# Create Flask app for keep-alive
app = Flask('')

@app.route('/')
def home():
    return "Bots are running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

async def run_bot(bot, token, name):
    """봇 실행 함수 (재시도 로직 추가)"""
    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            print(f"Starting {name} bot...")
            await bot.start(token)
            break
        except Exception as e:
            print(f"Error starting {name} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                print(f"Max retries reached. {name} failed to start.")
                raise

async def run_all_bots():
    db = DatabaseManager()
    character_bots = {}

    # Initialize character bots
    for char_name in CHARACTER_INFO.keys():
        character_bots[char_name] = CharacterBot(char_name, db)

    # Initialize selector bot
    selector_bot = BotSelector()
    selector_bot.character_bots = character_bots

    try:
        print("Starting bot initialization...")
        tasks = []

        # Start selector bot
        tasks.append(run_bot(selector_bot, SELECTOR_TOKEN, "Selector"))

        # Start character bots
        for name, bot in character_bots.items():
            token = globals()[f"{name.upper()}_TOKEN"]
            tasks.append(run_bot(bot, token, name))

        # Wait for all bots to start
        await asyncio.gather(*tasks)
        print("All bots started successfully!")

        # Keep the program running
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        print(f"Fatal error in run_all_bots: {e}")
        raise e
    finally:
        # Cleanup in case of error
        try:
            if 'selector_bot' in locals():
                await selector_bot.close()
            if 'character_bots' in locals():
                for bot in character_bots.values():
                    await bot.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")

def check_tokens():
    tokens = {
        'SELECTOR_TOKEN': SELECTOR_TOKEN,
        'KAGARI_TOKEN': KAGARI_TOKEN,
        'EROS_TOKEN': EROS_TOKEN,
        'ELYSIA_TOKEN': ELYSIA_TOKEN
    }

    for name, token in tokens.items():
        if not token:
            print(f"Error: {name} is not set!")
            return False
        if len(token) < 50:  # 토큰 길이 체크
            print(f"Error: {name} seems invalid (too short)")
            return False
    return True

if __name__ == "__main__":
    if not check_tokens():
        print("Token validation failed. Please check your environment variables.")
        exit(1)
    try:
        keep_alive()
        asyncio.run(run_all_bots())
    except KeyboardInterrupt:
        print("Program terminated by user")
    except Exception as e:
        print(f"Program crashed: {e}")