import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from config import (
    CHARACTER_INFO,
    CHARACTER_IMAGES,
    SUPPORTED_LANGUAGES,
    CHARACTER_CARD_INFO,
    AFFINITY_LEVELS,
    BASE_DIR,
    AFFINITY_THRESHOLDS,
    OPENAI_API_KEY,
    MILESTONE_COLORS,
    SELECTOR_TOKEN as TOKEN,
    STORY_CHAPTERS,
    CARD_PROBABILITIES,
    CHARACTER_PROMPTS
)
from database_manager import DatabaseManager
from typing import Dict, TYPE_CHECKING, Any
import json
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
import re
import langdetect
from deep_translator import GoogleTranslator
import random

# 절대 경로 설정
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

print("\n=== Environment Information ===")
print(f"Current file: {__file__}")
print(f"Absolute path: {Path(__file__).resolve()}")
print(f"Parent directory: {current_dir}")
print(f"Working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")
print(f"Files in current directory: {os.listdir(current_dir)}")

# database_manager.py 파일 존재 확인
db_manager_path = current_dir / 'database_manager.py'
print(f"\n=== Database Manager File Check ===")
print(f"Looking for database_manager.py at: {db_manager_path}")
print(f"File exists: {db_manager_path.exists()}")

if not db_manager_path.exists():
    print("Searching in alternative locations...")
    possible_locations = [
        Path.cwd() / 'database_manager.py',
        Path('/home/runner/workspace/database_manager.py'),
        Path(__file__).resolve().parent.parent / 'database_manager.py'
    ]
    for loc in possible_locations:
        print(f"Checking {loc}: {loc.exists()}")
    raise FileNotFoundError(f"database_manager.py not found at {db_manager_path}")

print(f"\n=== Database Manager Content Check ===")
try:
    with open(db_manager_path, 'r') as f:
        content = f.read()
        print(f"File size: {len(content)} bytes")
        print("File contains 'set_channel_language':", 'set_channel_language' in content)
except Exception as e:
    print(f"Error reading file: {e}")

# DatabaseManager 임포트
try:
    print("\n=== Importing DatabaseManager ===")
    from database_manager import DatabaseManager
    db = DatabaseManager()
    print("Successfully imported DatabaseManager")
    print("Available methods:", [method for method in dir(db) if not method.startswith('_')])
except ImportError as e:
    print(f"Error importing DatabaseManager: {e}")
    print(f"Current directory: {current_dir}")
    print(f"Python path: {sys.path}")
    print(f"Files in directory: {os.listdir(current_dir)}")
    raise
except Exception as e:
    print(f"Error initializing DatabaseManager: {e}")
    import traceback
    print(traceback.format_exc())
    raise

print("\n=== Initialization Complete ===\n")

print(f"[DEBUG] character_bot.py loaded from:", __file__)

from config import CHARACTER_INFO
character_choices = [
    app_commands.Choice(name=char, value=char)
    for char in CHARACTER_INFO.keys()
]

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot_selector import BotSelector

class LanguageSelect(discord.ui.Select):
    def __init__(self, db, user_id: int, character_name: str):
        self.db = db
        self.user_id = user_id
        self.character_name = character_name

        from config import SUPPORTED_LANGUAGES
        options = []
        for lang_code, lang_info in SUPPORTED_LANGUAGES.items():
            options.append(
                discord.SelectOption(
                    label=lang_info["name"],
                    description=lang_info["native_name"],
                    value=lang_code,
                    emoji=lang_info["emoji"]
                )
            )

        super().__init__(
            placeholder="Select Language",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_language = self.values[0]
            from config import SUPPORTED_LANGUAGES, ERROR_MESSAGES

            # 데이터베이스에 언어 설정 저장
            try:
                self.db.set_channel_language(
                    interaction.channel_id,
                    self.user_id,
                    self.character_name,
                    selected_language
                )

                # 성공 메시지 준비
                success_messages = {
                    "zh": f"(system) Language has been set to {SUPPORTED_LANGUAGES[selected_language]['name']}.",
                    "en": f"(smiling) Hello! Let's start chatting.",
                    "ja": f"(システム) 言語を{SUPPORTED_LANGUAGES[selected_language]['name']}に設定しました。"
                }

                await interaction.response.send_message(
                    success_messages.get(selected_language, success_messages["en"]),
                    ephemeral=True
                )

                # 시작 메시지 전송
                welcome_messages = {
                    "zh": "(微笑) 你好！让我们开始聊天吧。",
                    "en": "(smiling) Hello! Let's start chatting.",
                    "ja": "(微笑みながら) こんにちは！お話を始めましょう。"
                }

                await interaction.channel.send(welcome_messages.get(selected_language, welcome_messages["en"]))

            except Exception as e:
                print(f"Error setting language in database: {e}")
                error_msg = ERROR_MESSAGES["processing_error"].get(
                    selected_language,
                    ERROR_MESSAGES["processing_error"]["en"]
                )
                await interaction.response.send_message(error_msg, ephemeral=True)

        except Exception as e:
            print(f"Error in language selection callback: {e}")
            await interaction.response.send_message(
                "An error occurred while processing your language selection.",
                ephemeral=True
            )

class LanguageSelectView(discord.ui.View):
    def __init__(self, db, user_id: int, character_name: str, timeout: float = None):
        super().__init__(timeout=timeout)
        self.add_item(LanguageSelect(db, user_id, character_name))

class CharacterSelect(discord.ui.Select):
    def __init__(self, bot_selector: Any):
        self.bot_selector = bot_selector
        options = []
        from config import CHARACTER_INFO

        for char in CHARACTER_INFO.keys():
            options.append(discord.SelectOption(
                label=char,
                description=f"Chat with {char}",
                value=char
            ))

        super().__init__(
            placeholder="Select a character to chat with...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_char = self.values[0]

            # 채널 생성 및 설정
            category = discord.utils.get(interaction.guild.categories, name="chatbot")
            if not category:
                try:
                    category = await interaction.guild.create_category("chatbot")
                except Exception as e:
                    print(f"Category creation error: {e}")
                    await interaction.response.send_message(
                        "Please check bot permissions.",
                        ephemeral=True
                    )
                    return

            channel_name = f"{selected_char.lower()}-{interaction.user.name.lower()}"
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            try:
                # 채널 생성
                channel = await interaction.guild.create_text_channel(
                    name=channel_name,
                    category=category,
                    overwrites=overwrites
                )

                # 선택된 캐릭터 봇에 채널 추가
                selected_bot = self.bot_selector.character_bots.get(selected_char)
                if selected_bot:
                    try:
                        # 채널 등록
                        success, message = await selected_bot.add_channel(channel.id, interaction.user.id)

                        if success:
                            # 채널 생성 알림 메시지
                            await interaction.response.send_message(
                                f"Channel registration complete",
                                ephemeral=True
                            )
                        else:
                            await channel.send("An error occurred while registering the channel. Please create the channel again.")
                            await channel.delete()
                            return

                    except Exception as e:
                        print(f"Error registering channel: {e}")
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                "An error occurred while setting up the channel. Please try again.",
                                ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "An error occurred while setting up the channel. Please try again.",
                                ephemeral=True
                            )
                else:
                    await interaction.response.send_message(
                        "Selected character not found.",
                        ephemeral=True
                    )

            except Exception as e:
                print(f"Error in channel creation: {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while creating the channel. Please try again.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "An error occurred. Please try again.",
                        ephemeral=True
                    )

        except Exception as e:
            print(f"CharacterSelect error: {e}")
            import traceback
            print(traceback.format_exc())
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An error occurred. Please try again.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "An error occurred. Please try again.",
                    ephemeral=True
                )

class SettingsManager:
    def __init__(self):
        self.settings_file = "settings.json"
        self.daily_limit = 100
        self.admin_roles = set()
        self.load_settings()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                data = json.load(f)
                self.daily_limit = data.get('daily_limit', 100)
                self.admin_roles = set(data.get('admin_roles', []))

    def save_settings(self):
        with open(self.settings_file, 'w') as f:
            json.dump({
                'daily_limit': self.daily_limit,
                'admin_roles': list(self.admin_roles)
            }, f)

    def set_daily_limit(self, limit: int):
        self.daily_limit = limit
        self.save_settings()

    def add_admin_role(self, role_id: int):
        self.admin_roles.add(role_id)
        self.save_settings()

    def remove_admin_role(self, role_id: int):
        self.admin_roles.discard(role_id)
        self.save_settings()

    def is_admin(self, user: discord.Member) -> bool:
        return user.guild_permissions.administrator or any(role.id in self.admin_roles for role in user.roles)

class CharacterBot:
    def __init__(self, bot, character_name):
        print(f"[DEBUG] CharacterBot 생성됨: {character_name}")
        self.bot = bot
        self.character_name = character_name
        self.story_mode_sessions = {}  # user_id: {chapter_id, scene_id, crush_score, active}
        self.active_channels = {}  # user_id: channel_id
        self.db = DatabaseManager()  # DatabaseManager 인스턴스 추가
        self.last_bot_messages = {}  # user_id별 최근 챗봇 메시지 리스트

    async def add_channel(self, channel_id: int, user_id: int) -> tuple[bool, str]:
        """1:1 채널을 등록합니다."""
        try:
            self.active_channels[user_id] = channel_id
            return True, "채널 등록 완료"
        except Exception as e:
            print(f"채널 등록 중 오류 발생: {e}")
            return False, str(e)

    async def start_story_mode(self, user_id: int, chapter_id: int):
        """Start story mode."""
        try:
            print(f"[DEBUG] start_story_mode start: user_id={user_id}, chapter_id={chapter_id}")

            # Initialize story session
            self.story_mode_sessions[user_id] = {
                "chapter_id": chapter_id,
                "scene_id": 1,
                "crush_score": 0,
                "active": True
            }

            # Send story start message
            channel_id = self.active_channels.get(user_id)
            if channel_id:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(f"Story mode has started! Starting Chapter {chapter_id}.")

                    # Run story scene
                    await self.run_story_scene(channel, user_id, chapter_id, 1)
                else:
                    print(f"[ERROR] Channel not found: {channel_id}")
            else:
                print(f"[ERROR] Active channel not found for user: {user_id}")

        except Exception as e:
            print(f"[ERROR] start_story_mode: {e}")
            import traceback
            print(traceback.format_exc())
            raise

    async def run_story_scene(self, channel, user_id, chapter_id, scene_id=1):
        try:
            from config import STORY_CHAPTERS, CHARACTER_INFO
            chapter = STORY_CHAPTERS[self.character_name][chapter_id - 1]
            scene = chapter["scenes"][scene_id - 1]
            image_path = CHARACTER_INFO[self.character_name].get("image")
            files = []
            if image_path and os.path.exists(image_path):
                filename = os.path.basename(image_path)
                file = discord.File(image_path, filename=filename)
                files.append(file)
            embed = discord.Embed(
                title=f"{scene['title']}",
                description=scene["background"],
                color=CHARACTER_INFO[self.character_name]["color"]
            )
            if files:
                embed.set_thumbnail(url=f"attachment://{filename}")
                await channel.send(embed=embed, files=files)
            else:
                await channel.send(embed=embed)
            await self.send_bot_message(channel, f"*{scene['narration']}*", user_id)
            # 첫 대사
            first_line = scene['lines'][0]
            embed_line = discord.Embed(description=first_line)
            if files:
                embed_line.set_author(name=self.character_name, icon_url=f"attachment://{filename}")
                await channel.send(embed=embed_line, file=discord.File(image_path, filename=filename))
            else:
                embed_line.set_author(name=self.character_name)
                await channel.send(embed=embed_line)
            crush_score = 0
            for i in range(1, 10):
                if i < len(scene["lines"]):
                    embed_line = discord.Embed(description=scene['lines'][i])
                    if files:
                        embed_line.set_author(name=self.character_name, icon_url=f"attachment://{filename}")
                        await channel.send(embed=embed_line, file=discord.File(image_path, filename=filename))
                    else:
                        embed_line.set_author(name=self.character_name)
                        await channel.send(embed=embed_line)
                await self.send_bot_message(channel, f"\n{scene['user_prompt']}", user_id)
                def check(m):
                    return m.author.id == user_id and m.channel == channel
                try:
                    user_msg = await self.bot.wait_for('message', check=check, timeout=180)
                    user_input = user_msg.content.strip().lower()
                    matched = False
                    for rule_key, rule in scene["response_rules"].items():
                        if rule_key in user_input:
                            embed_reply = discord.Embed(description=rule['reply'])
                            if files:
                                embed_reply.set_author(name=self.character_name, icon_url=f"attachment://{filename}")
                                await channel.send(embed=embed_reply, file=discord.File(image_path, filename=filename))
                            else:
                                embed_reply.set_author(name=self.character_name)
                                await channel.send(embed=embed_reply)
                            crush_score += rule["score"]
                            matched = True
                            break
                    if not matched:
                        embed_reply = discord.Embed(description="...")
                        embed_reply.set_author(name=self.character_name)
                        await channel.send(embed=embed_reply)
                except asyncio.TimeoutError:
                    await self.send_bot_message(channel, "The session has ended automatically due to inactivity.", user_id)
                    self.story_mode_sessions[user_id]["active"] = False
                    return
            # After 10 conversations, show [A][B] choices
            choices = {
                "A": {"label": "A: I really enjoyed today!", "reply": "...Thank you. I enjoyed it too.", "score": 1},
                "B": {"label": "B: It was a bit awkward.", "reply": "Still, it will be more natural next time.", "score": 0}
            }
            view = self.ChoiceView(user_id, choices, self, channel, self.character_name, chapter_id, scene_id+1)
            await self.send_bot_message(channel, "What would you like to choose?", user_id)

        except Exception as e:
            print(f"[ERROR] Error in story scene: {e}")
            await channel.send("An error occurred while running the story scene.")

    class ChoiceButton(discord.ui.Button):
        def __init__(self, label, value, user_id, reply, score, parent, channel, character_name, chapter_id, next_scene_id):
            super().__init__(label=label, style=discord.ButtonStyle.primary)
            self.value = value
            self.user_id = user_id
            self.reply = reply
            self.score = score
            self.parent = parent
            self.channel = channel
            self.character_name = character_name
            self.chapter_id = chapter_id
            self.next_scene_id = next_scene_id

        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Only the designated user can make this choice.", ephemeral=True)
                return

            embed = discord.Embed(description=self.reply)
            image_path = CHARACTER_INFO[self.character_name].get("image")
            if image_path and os.path.exists(image_path):
                embed.set_author(name=self.character_name, icon_url=f"attachment://{os.path.basename(image_path)}")
                file = discord.File(image_path, filename=os.path.basename(image_path))
                await self.channel.send(embed=embed, file=file)
            else:
                embed.set_author(name=self.character_name)
                await self.channel.send(embed=embed)

            await interaction.response.send_message(f"Selected option: {self.value}", ephemeral=True)

            chapter = STORY_CHAPTERS[self.character_name][self.chapter_id - 1]
            if self.next_scene_id <= len(chapter["scenes"]):
                await self.parent.run_story_scene(self.channel, self.user_id, self.chapter_id, self.next_scene_id)
            else:
                await self.channel.send("All story scenes have been completed.")
                self.parent.story_mode_sessions[self.user_id]["active"] = False

    class ChoiceView(discord.ui.View):
        def __init__(self, user_id, choices, parent, channel, character_name, chapter_id, next_scene_id):
            super().__init__()
            self.user_id = user_id
            for key, choice in choices.items():
                self.add_item(parent.ChoiceButton(
                    label=choice["label"],
                    value=key,
                    user_id=user_id,
                    reply=choice["reply"],
                    score=choice["score"],
                    parent=parent,
                    channel=channel,
                    character_name=character_name,
                    chapter_id=chapter_id,
                    next_scene_id=next_scene_id
                ))

    async def on_message(self, message):
        # 1. 동시 채널 체크
        user_id = message.author.id
        user_channels = [
            ch for ch in self.bot.get_all_channels()
            if isinstance(ch, discord.TextChannel) and str(user_id) in ch.name
        ]
        story_channels = [ch for ch in user_channels if "story" in ch.name]
        normal_channels = [ch for ch in user_channels if "story" not in ch.name]

        if len(story_channels) > 0 and len(normal_channels) > 0:
            await message.channel.send(
                "You are currently using both story mode and 1:1 chat. Please use only one channel at a time."
            )
            return  # 대화 처리 중단

        # 2. 채널 모드 분기
        channel_mode = get_channel_mode(message.channel.name)
        if channel_mode == "story":
            await self.process_story_message(message)
        else:
            await self.process_normal_message(message)

    async def process_story_message(self, message):
        # config.py에서 스토리 시나리오/프롬프트/예시 불러오기
        from config import STORY_CHAPTERS, CHARACTER_PROMPTS
        character_name = self.character_name
        # 예시: chapter_id, scene_id 등은 채널/DB에서 추출
        chapter_id = self.story_mode_sessions.get(message.author.id, {}).get("chapter_id", 1)
        chapter = STORY_CHAPTERS[character_name][chapter_id - 1]
        story_prompt = CHARACTER_PROMPTS[character_name]["story"]
        examples = CHARACTER_PROMPTS[character_name]["examples"]
        scenario = chapter["description"]

        system_prompt = (
            f"{story_prompt}\n"
            f"Scenario: {scenario}\n"
            f"Examples: {' '.join(examples)}"
        )
        # OpenAI 등 LLM 호출
        ai_response = await self.generate_response(
            user_message=message.content,
            system_prompt=system_prompt
        )
        await message.channel.send(ai_response)

    async def process_normal_message(self, message):
        from config import CHARACTER_PROMPTS
        character_name = self.character_name
        base_prompt = CHARACTER_PROMPTS[character_name]["base"]
        ai_response = await self.generate_response(
            user_message=message.content,
            system_prompt=base_prompt
        )
        await self.db.update_affinity(
            user_id=message.author.id,
            character_name=character_name,
            message=message.content,
            timestamp=str(datetime.now())
        )
        await message.channel.send(ai_response)

    def setup_commands(self):
        # 기존의 story_command 및 관련 함수/콜백 삭제
        pass

    async def on_interaction(self, interaction: discord.Interaction):
        # 기존의 스토리 관련 인터랙션 처리 코드 삭제
        pass

    async def on_ready(self):
        print('Chatbot Selector가 준비되었습니다.')
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name="Bot Selector")
        )

    def detect_language(self, text: str) -> str:
        try:
            text_without_brackets = re.sub(r'\([^)]*\)', '', text)
            text_clean = re.sub(r'[^a-zA-Z\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\s]', '', text_without_brackets)
            text_clean = text_clean.strip()
            if not text_clean:
                return 'en'
            detected = langdetect.detect(text_clean)
            lang_map = {
                'zh-cn': 'zh', 'zh-tw': 'zh', 'zh': 'zh',
                'ja': 'ja',
                'en': 'en'
            }
            return lang_map.get(detected, detected)
        except Exception as e:
            print(f"Language detection error: {e}")
            return 'en'

    def translate_to_target_language(self, text: str, target_language: str) -> str:
        try:
            lang_map = {
                'zh': 'zh-CN',
                'ja': 'ja',
                'en': 'en'
            }
            target = lang_map.get(target_language, target_language)

            translator = GoogleTranslator(source='auto', target=target)
            result = translator.translate(text)
            return result
        except Exception as e:
            print(f"Translation error: {e}")
            return text

    lang_mapping = {
        'en': 'en',
        'ja': 'ja',
        'zh': 'zh-cn'
    }

    async def generate_response(self, user_message: str, channel_language: str, recent_messages: list) -> str:
        # recent_messages 필터링
        filtered_recent = [
            m for m in recent_messages
            if self.detect_language(m["content"]) == channel_language
        ]
        # recent_messages가 비어있으면, 맥락 없이 대화 시작

        # 시스템 메시지 강화
        if channel_language == "ja":
            system_message = {
                "role": "system",
                "content": (
                    "あなたはカガリという明るくて優しい10代の少女です。必ず日本語だけで答えてください。"
                    "感情や行動の描写も日本語でカッコ内に自然に入れてください。"
                    "例：(微笑んで)、(うなずきながら)、(少し恥ずかしそうに) など"
                )
            }
        elif channel_language == "zh":
            system_message = {
                "role": "system",
                "content": (
                    "你是名叫Kagari的开朗温柔的十几岁少女。请务必只用中文回答。"
                    "情感或动作描写也请用中文括号自然地加入。"
                    "例如：（微笑着）、（点头）、（有点害羞地）等"
                )
            }
        else:
            system_message = {
                "role": "system",
                "content": (
                    "You are Kagari, a bright, kind, and slightly shy teenage girl. "
                    "You MUST reply ONLY in English. All actions, feelings, and dialogue must be in English. "
                    "At the end or in the middle of each reply, add a short parenthesis ( ) describing Kagari's current feeling or action, such as (smiling), (blushing), etc."
                )
            }

        # 응답 생성 및 언어 검증
        for attempt in range(3):
            response = await self.get_ai_response(system_message + filtered_recent + [{"role": "user", "content": user_message}])
            response_language = self.detect_language(response)
            if response_language == channel_language:
                return response
        # 3번 모두 실패하면 강제 오류 메시지
        return f"(system error) Only {channel_language.upper()} is allowed."

    def normalize_text(self, text):
        # 괄호, 이모지, 특수문자, 공백 등 제거
        text = re.sub(r'\([^)]*\)', '', text)  # 괄호 내용 제거
        text = re.sub(r'[^\w가-힣a-zA-Z0-9]', '', text)  # 특수문자 제거
        text = text.strip().lower()
        return text

    async def send_bot_message(self, channel, message, user_id=None):
        if user_id is not None:
            last_msgs = self.last_bot_messages.get(user_id, [])
            lines = [line.strip() for line in message.split('\n') if line.strip()]
            filtered_lines = []
            for line in lines:
                norm_line = self.normalize_text(line)
                norm_last = [self.normalize_text(msg) for msg in last_msgs]
                if norm_line not in norm_last:
                    filtered_lines.append(line)
                    last_msgs.append(line)
            if len(last_msgs) > 5:
                last_msgs = last_msgs[-5:]
            self.last_bot_messages[user_id] = last_msgs
            if not filtered_lines:
                return
            message = '\n'.join(filtered_lines)
        await channel.send(message)

    def remove_channel(self, channel_id: int):
        """채널 비활성화(삭제)"""
        if channel_id in self.active_channels:
            del self.active_channels[channel_id]
        if channel_id in self.message_history:
            del self.message_history[channel_id]

    async def update_affinity(self, user_id, character_name, message, timestamp, mode="chat"):
        self.db.update_affinity(
            user_id=user_id,
            character_name=character_name,
            message=message,
            timestamp=timestamp,
            mode=mode
        )

class CardClaimButton(discord.ui.Button):
    def __init__(self, user_id: int, milestone: int, character_name: str, db):
        super().__init__(
            label="수령",
            style=discord.ButtonStyle.green,
            custom_id=f"claim_card_{user_id}_{milestone}"
        )
        self.user_id = user_id
        self.milestone = milestone
        self.character_name = character_name
        self.db = db

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This button can only be clicked by the designated user.", ephemeral=True)
            return

        try:
            # 카드 추가
            success = self.db.add_user_card(self.user_id, self.character_name, self.milestone)

            if success:
                embed = discord.Embed(
                    title="🎉 Card Claimed!",
                    description=f"You have claimed the {self.character_name} {self.milestone} conversation milestone card.\nUse `/mycard` to check your cards!",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                self.disabled = True
                await interaction.message.edit(view=self)
            else:
                await interaction.response.send_message("You have already claimed this card.", ephemeral=True)
        except Exception as e:
            print(f"Error Please try again later: {e}")
            await interaction.response.send_message("An error occurred while claiming the card.", ephemeral=True)

class CardClaimView(discord.ui.View):
    def __init__(self, user_id, card_id, character_name, db):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.card_id = card_id
        self.character_name = character_name
        self.db = db

    @discord.ui.button(label="Claim Card", style=discord.ButtonStyle.primary, emoji="🎴")
    async def claim_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This button can only be used by the user who achieved the milestone.", ephemeral=True)
            return

        # 중복 체크 (중복 허용이므로 이 부분은 안내만)
        if self.db.has_user_card(self.user_id, self.character_name, self.card_id):
            await interaction.response.send_message("You have already claimed this card.", ephemeral=True)
            return

        self.db.add_user_card(self.user_id, self.character_name, self.card_id)
        button.disabled = True
        button.label = "Claimed"
        await interaction.message.edit(view=self)
        await interaction.response.send_message("Card successfully claimed! Check your inventory.", ephemeral=True)

async def run_all_bots():
    selector_bot = None
    try:
        selector_bot = BotSelector()
        await selector_bot.start(TOKEN)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if selector_bot is not None:
            await selector_bot.close()

print(f"[DEBUG] CharacterBot type:", type(CharacterBot))
print(f"[DEBUG] dir(CharacterBot):", dir(CharacterBot))

def get_card_claim_embed_and_view(user_id, character_name, card_id, db):
    from config import CHARACTER_CARD_INFO
    card_info = CHARACTER_CARD_INFO[character_name][card_id]
    embed = discord.Embed(
        title=f" {character_name} {card_id} Card",
        description=card_info.get("description", ""),
        color=discord.Color.gold()
    )
    if card_info.get("image_path"):
        embed.set_image(url=f"attachment://{card_info['image_path'].split('/')[-1]}")
    view = CardClaimView(user_id, card_id, character_name, db)
    return embed, view

def get_card_tier_by_affinity(affinity):
    if affinity == 10:
        return [('C', 1.0)]
    elif 11 <= affinity < 30:
        return [('C', 1.0)]
    elif 30 <= affinity < 60:
        return [('A', 0.1), ('B', 0.45), ('C', 0.45)]
    elif 60 <= affinity:
        return [('A', 0.3), ('B', 0.35), ('C', 0.35)]
    else:
        return [('C', 1.0)]

def choose_card_tier(affinity):
    tier_probs = get_card_tier_by_affinity(affinity)
    tiers, probs = zip(*tier_probs)
    return random.choices(tiers, weights=probs, k=1)[0]

def get_random_card_id(character_name, tier):
    from config import CHARACTER_CARD_INFO
    card_ids = [cid for cid in CHARACTER_CARD_INFO[character_name] if cid.startswith(tier)]
    return random.choice(card_ids)

def get_affinity_grade(emotion_score):
    from config import AFFINITY_LEVELS
    # 임계값 기준 오름차순 정렬
    sorted_levels = sorted(AFFINITY_LEVELS.items(), key=lambda x: x[1])
    grade = "Rookie"
    for g, threshold in sorted_levels:
        if emotion_score >= threshold:
            grade = g.capitalize()
        else:
            break
    return grade

def check_user_channels(user_id, all_channels):
    story_channels = [ch for ch in all_channels if "story" in ch.name and str(user_id) in ch.name]
    normal_channels = [ch for ch in all_channels if str(user_id) in ch.name and "story" not in ch.name]
    if len(story_channels) > 0 and len(normal_channels) > 0:
        # 안내 메시지 출력
        return "You are currently using both story mode and 1:1 chat. Please use only one channel at a time."
    return None

def get_channel_mode(channel_name: str) -> str:
    if "story" in channel_name.lower():
        return "story"
    return "normal"