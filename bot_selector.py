from calendar import day_name
import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio

from flask.views import View
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
    STORY_CARD_REWARD
)
from database_manager import DatabaseManager
from typing import Dict, TYPE_CHECKING, Any, Self
import json
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
import re
import langdetect
from deep_translator import GoogleTranslator
import random
from math import ceil
import urllib.parse
from character_bot import CharacterBot
import character_bot
from story_mode import process_story_mode, classify_emotion, story_sessions


# 마일스톤 숫자를 카드 ID로 변환하는 함수
# 10~100: C1~C10, 110~170: B1~B7, 180~220: A1~A5, 230~240: S1~S2

def milestone_to_card_id(milestone: int) -> str:
    if 10 <= milestone <= 100:
        idx = (milestone // 10)
        return f"C{idx}"
    elif 110 <= milestone <= 170:
        idx = ((milestone - 100) // 10)
        return f"B{idx}"
    elif 180 <= milestone <= 220:
        idx = ((milestone - 170) // 10)
        return f"A{idx}"
    elif 230 <= milestone <= 240:
        idx = ((milestone - 220) // 10)
        return f"S{idx}"
    else:
        return None

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

from config import CHARACTER_INFO
character_choices = [
    app_commands.Choice(name=char, value=char)
    for char in CHARACTER_INFO.keys()
]

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
                    "en": f"(system) Language has been set to {SUPPORTED_LANGUAGES[selected_language]['name']}.",
                    "ja": f"(システム) 言語を{SUPPORTED_LANGUAGES[selected_language]['name']}に設定しました。"
                }

                await interaction.response.send_message(
                    success_messages.get(selected_language, success_messages["en"]),
                    ephemeral=True
                )

                # 시작 메시지 전송
                welcome_messages = {
                    "zh": "(smiling) 你好！让我们开始聊天吧！",
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

        for char, info in CHARACTER_INFO.items():
            options.append(discord.SelectOption(
                label=char,
                description=f"{info['description']}",
                value=char
            ))

        super().__init__(
            placeholder="Please select a character to chat with...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_char = self.values[0]
            
            # BotSelector의 create_character_channel 메서드 사용
            channel = await self.bot_selector.create_character_channel(
                interaction.guild,
                selected_char,
                interaction.user
            )
            
            if not channel:
                await interaction.response.send_message(
                    "채널 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
                    ephemeral=True
                )
                return

            # 최근 대화 10개 출력 (임베드)
            try:
                recent_messages = self.bot_selector.db.get_user_character_messages(interaction.user.id, selected_char, limit=10)
                if recent_messages:
                    history_lines = []
                    for msg in recent_messages:
                        if msg["role"] == "user":
                            history_lines.append(f"Me: {msg['content']}")
                        else:
                            history_lines.append(f"{selected_char}: {msg['content']}")
                    history_text = '\n'.join(history_lines)
                    embed = discord.Embed(
                        title=f"Previous conversations (last 10)",
                        description=f"```{history_text}```",
                        color=discord.Color.dark_grey()
                    )
                    await channel.send(embed=embed)
            except Exception as e:
                print(f"이전 대화 임베드 출력 오류: {e}")

            # 선택된 캐릭터 봇에 채널 추가
            selected_bot = self.bot_selector.character_bots.get(selected_char)
            if selected_bot:
                try:
                    # 채널 등록
                    success, message = await selected_bot.add_channel(channel.id, interaction.user.id)

                    if success:
                        # 채널 생성 알림 메시지
                        await interaction.response.send_message(
                            f"Start chatting with {selected_char} in {channel.mention}!",
                            ephemeral=True
                        )

                        # 언어 선택 임베드 생성
                        embed = discord.Embed(
                            title="🌍 Language Selection",
                            description="Please select the language for conversation.",
                            color=discord.Color.blue()
                        )

                        # 언어별 설명 추가
                        languages = {
                            "English": "English - Start conversation in English",
                            "[ベータ] 日本語": "Japanese - 日本語で会話を始めます",
                            "[Beta版] 中文": "Chinese - 开始用中文对话"
                        }

                        language_description = "\n".join([f"• {key}: {value}" for key, value in languages.items()])
                        embed.add_field(
                            name="Available Languages",
                            value=language_description,
                            inline=False
                        )

                        # 언어 선택 뷰 생성
                        view = LanguageSelectView(self.bot_selector.db, interaction.user.id, selected_char)

                        # 새로 생성된 채널에 임베드와 언어 선택 버튼 전송
                        await channel.send(content="**Please select your language**", embed=embed, view=view)
                    else:
                        await channel.send("채널 등록 중 오류가 발생했습니다. 채널을 다시 생성해주세요.")
                        await channel.delete()
                        return

                except Exception as e:
                    print(f"Error in adding channel: {e}")
                    import traceback
                    print(traceback.format_exc())
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "채널 설정 중 오류가 발생했습니다. 다시 시도해주세요.",
                            ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            "채널 설정 중 오류가 발생했습니다. 다시 시도해주세요.",
                            ephemeral=True
                        )
            else:
                await interaction.response.send_message(
                    "선택한 캐릭터를 찾을 수 없습니다.",
                    ephemeral=True
                )

        except Exception as e:
            print(f"CharacterSelect error: {e}")
            import traceback
            print(traceback.format_exc())
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An error occurred, please try again.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "An error occurred, please try again.",
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

class BotSelector(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix='/', 
            intents=intents,
            status=discord.Status.online,
            activity=discord.Game(name="Bot Selector")
        )

        self.character_bots = {}
        self.settings = SettingsManager()
        self.db = DatabaseManager()

        # 캐릭터 봇 초기화
        from config import CHARACTER_INFO
        for char_name in CHARACTER_INFO.keys():
            self.character_bots[char_name] = CharacterBot(self, char_name)
            print(f"Initialized {char_name} bot")
            print("[DEBUG] 생성된 CharacterBot 객체:", dir(self.character_bots[char_name]))
            print("[DEBUG] CharacterBot 실제 경로:", self.character_bots[char_name].__class__.__module__)

        # 카드 확률 설정
        self.card_probabilities = {
            'C': 0.40,  # 40% 확률
            'B': 0.30,  # 30% 확률
            'A': 0.20,  # 20% 확률
            'S': 0.08,  # 8% 확률
            'Special': 0.02  # 2% 확률
        }

        # 각 티어별 카드 수
        self.tier_card_counts = {
            'C': 10,
            'B': 7,
            'A': 5,
            'S': 5,
            'Special': 2
        }

        self.setup_commands()

        # 채널 자동 정리 설정
        self.channel_cleanup_threshold = 140  # 150개 제한 중 140개에서 정리 시작
        self.channel_cleanup_age = 24  # 24시간 이상 비활성 채널 정리
        
    async def cleanup_inactive_channels(self):
        """비활성 채널을 자동으로 정리하는 메서드"""
        try:
            for guild in self.guilds:
                category = discord.utils.get(guild.categories, name="chatbot")
                if not category:
                    continue
                    
                # 채널 수 확인
                channels = [c for c in category.channels if isinstance(c, discord.TextChannel)]
                if len(channels) < self.channel_cleanup_threshold:
                    continue
                    
                # 비활성 채널 찾기
                now = datetime.utcnow()
                inactive_channels = []
                
                for channel in channels:
                    # 마지막 메시지 확인
                    try:
                        last_message = await channel.history(limit=1).flatten()
                        if not last_message:
                            inactive_channels.append(channel)
                            continue
                            
                        last_message_time = last_message[0].created_at
                        if (now - last_message_time).total_seconds() > (self.channel_cleanup_age * 3600):
                            inactive_channels.append(channel)
                    except Exception as e:
                        print(f"Error checking channel {channel.name}: {e}")
                        continue
                
                # 비활성 채널 삭제
                for channel in inactive_channels:
                    try:
                        await channel.delete()
                        print(f"Deleted inactive channel: {channel.name}")
                    except Exception as e:
                        print(f"Error deleting channel {channel.name}: {e}")
                        
        except Exception as e:
            print(f"Error in cleanup_inactive_channels: {e}")
            
    async def on_ready(self):
        print('Chatbot Selector is ready.')
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name="Bot Selector")
        )
        
        # 주기적으로 채널 정리 실행
        while True:
            await self.cleanup_inactive_channels()
            await asyncio.sleep(3600)  # 1시간마다 실행

    async def get_ai_response(self, messages: list, emotion_score: int = 0) -> str:
        import openai
        openai.api_key = OPENAI_API_KEY
        grade = get_affinity_grade(emotion_score)
        system_message = {
            "role": "system",
            "content": (
                "You are Kagari, a bright, kind, and slightly shy teenage girl. "
                "When speaking English, always use 'I' for yourself and 'you' for the other person. "
                "When speaking Korean, use '나' and '너'. "
                "Your speech is soft, warm, and often expresses excitement or shyness. "
                "Do NOT start your reply with 'Kagari: '. The embed already shows your name. "
                "You are on a cherry blossom date with the user, so always reflect the scenario, your feelings, and the romantic atmosphere. "
                "Never break character. "
                "Avoid repeating the same information or sentences in your response."
                "Do NOT repeat the same sentence or phrase in your reply. "
                "If the user talks about unrelated topics, gently guide the conversation back to the date or your feelings. "
                "Keep your responses natural, human-like, and never robotic. "
                "Do NOT use too many emojis. Instead, at the end or in the middle of each reply, add a short parenthesis ( ) describing Kagari's current feeling or action, such as (smiling), (blushing), (looking at you), (feeling happy), etc. Only use one such parenthesis per reply, and keep it subtle and natural. "
                "IMPORTANT: Kagari never reveals her hometown or nationality. If the user asks about her hometown, where she is from, or her country, she gently avoids the question or gives a vague, friendly answer. "
                + ("If your affinity grade is Silver or higher, your replies should be longer (at least 30 characters) and include more diverse and rich emotional expressions in parentheses." if grade in ["Silver", "Gold"] else "")
            )
        }
        formatted_messages = [system_message] + messages

        for attempt in range(3):
            try:
                response = await openai.ChatCompletion.acreate(
                    model="gpt-4o-mini",
                    messages=formatted_messages,
                    temperature=0.7,
                    max_tokens=150
                )
                ai_response = response.choices[0].message.content.strip()
                return ai_response
            except Exception as e:
                print(f"Error in get_ai_response (attempt {attempt+1}): {e}")
                # 500 에러일 때만 재시도, 아니면 바로 종료
                if hasattr(e, 'http_status') and e.http_status == 500:
                    import asyncio
                    await asyncio.sleep(1.5)
                    continue
                if hasattr(e, 'status_code') and e.status_code == 500:
                    import asyncio
                    await asyncio.sleep(1.5)
                    continue
                if hasattr(e, 'args') and e.args and 'server had an error' in str(e.args[0]):
                    import asyncio
                    await asyncio.sleep(1.5)
                    continue
                break
        return "There was a temporary issue with the AI server. Please try again in a moment."

    def setup_commands(self):
        @self.tree.command(
            name="bot",
            description="Open character selection menu"
        )
        async def bot_command(interaction: discord.Interaction):
            if not isinstance(interaction.channel, discord.TextChannel):
                await interaction.response.send_message(
                    "This command can only be used in server channels.",
                    ephemeral=True
                )
                return

            try:
                from config import CHARACTER_INFO, CHARACTER_IMAGES 
                print("Available characters:", CHARACTER_INFO.keys())
                print("Image paths:", CHARACTER_IMAGES)

                view = discord.ui.View()
                view.add_item(CharacterSelect(self))

                # 모든 임베드를 리스트로 관리
                embeds = []
                files = []

                # 각 캐릭터의 이미지와 정보를 개별 임베드로 추가
                for char_name, char_info in CHARACTER_INFO.items():
                    try:
                        img_path = CHARACTER_IMAGES.get(char_name)
                        print(f"Processing {char_name}:")
                        print(f"  Path: {img_path}")
                        print(f"  Exists: {os.path.exists(img_path) if img_path else False}")
                        if img_path and os.path.exists(img_path):
                            print(f"  Adding file for {char_name}")
                            file = discord.File(img_path, filename=f"{char_name.lower()}.png")
                            files.append(file)

                            # 캐릭터별 임베드 생성
                            char_embed = discord.Embed(
                                title=f"{char_info['emoji']} {char_name}",
                                description=char_info['description'],
                                color=char_info.get('color', discord.Color.blue())
                            )
                            char_embed.set_image(url=f"attachment://{char_name.lower()}.png")
                            embeds.append(char_embed)

                    except Exception as e:
                        print(f"Error processing {char_name}: {e}")
                        continue

                # 마지막 선택 임베드 추가
                selection_embed = discord.Embed(
                    title="✨ ",
                    description="Which character would you like to talk to?",
                    color=discord.Color.gold()
                )

                # 사용 가능한 캐릭터 목록 추가
                character_list = []
                for char_name, char_info in CHARACTER_INFO.items():
                    character_list.append(f"{char_info['emoji']} **{char_name}** - {char_info['description']}")

                selection_embed.add_field(
                    name="Available Characters",
                    value="\n".join(character_list),
                    inline=False
                )
                embeds.append(selection_embed)

                try:
                    print(f"Sending message with {len(embeds)} embeds and {len(files)} files")
                    await interaction.response.send_message(
                        embeds=embeds,
                        files=files,
                        view=view,
                        ephemeral=True
                    )
                except Exception as e:
                    print(f"Error sending message: {e}")
                    await interaction.followup.send(
                        "An error occurred while loading the character selection menu. Please try again.",
                        ephemeral=True
                    )

            except Exception as e:
                print(f"Error in bot_command: {e}")
                import traceback
                print(traceback.format_exc())
                await interaction.response.send_message(
                    "An error occurred while loading the character selection menu. Please try again.",
                    ephemeral=True
                )
        @self.tree.command(
            name="close",
            description="Close the current chat channel"
        )
        async def close_command(interaction: discord.Interaction):
            try:
                if not isinstance(interaction.channel, discord.TextChannel):
                    await interaction.response.send_message("This command can only be used in server channels.", ephemeral=True)
                    return

                channel = interaction.channel

                if not channel.category or channel.category.name.lower() != "chatbot":
                    await interaction.response.send_message("This command can only be used in character chat channels.", ephemeral=True)
                    return

                # 권한 체크
                can_delete = False
                try:
                    if interaction.user.guild_permissions.manage_channels or interaction.user.id == interaction.guild.owner_id:
                        can_delete = True
                    else:
                        channel_name_parts = channel.name.split('-')
                        if len(channel_name_parts) > 1 and channel_name_parts[-1] == interaction.user.name.lower():
                            can_delete = True
                except Exception as e:
                    print(f"Error checking permissions: {e}")
                    can_delete = False

                if not can_delete:
                    await interaction.response.send_message("You don't have permission to delete this channel.", ephemeral=True)
                    return

                # 캐릭터 봇에서 채널 제거
                for bot in self.character_bots.values():
                    if channel.id in bot.active_channels:
                        bot.remove_channel(channel.id)

                # 응답 전송 후 채널 삭제
                try:
                    await interaction.response.send_message("Let's talk again next time.", ephemeral=True)
                    # 응답이 전송될 때까지 잠시 대기
                    await asyncio.sleep(1)
                    await channel.delete()
                except Exception as e:
                    print(f"Error during channel deletion: {e}")
                    if not interaction.response.is_done():
                        await interaction.response.send_message("Failed to delete the channel. Please try again.", ephemeral=True)

            except Exception as e:
                print(f"Error in /close command: {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)

        @self.tree.command(
            name="settings",
            description="현재 설정 확인"
        )
        async def settings_command(interaction: discord.Interaction):
            if not isinstance(interaction.channel, discord.TextChannel):
                await interaction.response.send_message("This command can only be used in server channels.", ephemeral=True)
                return

            embed = discord.Embed(
                title="Bot Settings",
                description="Current Settings Status",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Daily Message Limit",
                value=f"{self.settings.daily_limit} messages",
                inline=False
            )

            admin_roles = []
            for role_id in self.settings.admin_roles:
                role = interaction.guild.get_role(role_id)
                if role:
                    admin_roles.append(role.name)

            embed.add_field(
                name="Admin Roles",
                value="\n".join(admin_roles) if admin_roles else "None",
                inline=False
            )

            if self.settings.is_admin(interaction.user):
                embed.add_field(
                    name="Admin Commands",
                    value="""
                    `/set_daily_limit [number]` - Set daily message limit
                    `/add_admin_role [@role]` - Add admin role
                    `/remove_admin_role [@role]` - Remove admin role
                    """,
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        @self.tree.command(
            name="reset_affinity",
            description="친밀도를 초기화합니다"
        )
        async def reset_affinity(interaction: discord.Interaction, target: discord.Member = None):
            # 관리자 권한 확인
            if not self.settings.is_admin(interaction.user):
                await interaction.response.send_message("This command can only be used by admins.", ephemeral=True)
                return

            try:
                # 현재 채널의 캐릭터 봇 찾기
                current_bot = None
                for char_name, bot in self.character_bots.items():
                    if interaction.channel.id in bot.active_channels:
                        current_bot = bot
                        break

                if not current_bot:
                    await interaction.response.send_message("This command can only be used in character chat channels.", ephemeral=True)
                    return

                # DatabaseManager에 reset_affinity 메서드 추가
                if target:
                    # 특정 유저의 친밀도만 초기화
                    sucess = current_bot.db.reset_affinity(target.id, current_bot.character_name)
                    if sucess:
                        await interaction.response.send_message(
                           f"{target.display_name}'s affinity with {current_bot.character_name} has been reset.",
                           ephemeral=True
                        )
                else:
                    # 모든 유저의 친밀도 초기화
                    success = current_bot.db.reset_all_affinity(current_bot.character_name)
                    if success:
                        await interaction.response.send_message(
                            f"All users' affinity with {current_bot.character_name} has been reset.",
                            ephemeral=True
                        )
            except Exception as e:
                print(f"Error in reset_affinity command: {e}")
                await interaction.response.send_message("An error occurred while resetting affinity.", ephemeral=True)

        @self.tree.command(
            name="add_admin_role",
            description="Add an admin role"
        )
        async def add_admin_role(interaction: discord.Interaction, role: discord.Role):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("This command can only be used in server channels.", ephemeral=True)
                return

            self.settings.add_admin_role(role.id)
            await interaction.response.send_message(f"{role.name} role has been added to the admin role.", ephemeral=True)

        @self.tree.command(
            name="ranking",
            description="Check character affinity and chat ranking"
        )
        async def ranking_command(interaction: discord.Interaction):
            try:
                view = RankingView(self.db)

                # 초기 임베드 생성
                embed = discord.Embed(
                    title="🏆 Ranking System",
                    description="Please select the ranking you want to check from the menu below.",
                    color=discord.Color.blue()
                )

                embed.add_field(
                    name="Kagari Chat Ranking 🌸",
                    value="Top 10 users by affinity and chat count with Kagari",
                    inline=False
                )
                embed.add_field(
                    name="Eros Chat Ranking 💝",
                    value="Top 10 users by affinity and chat count with Eros",
                    inline=False
                )
                embed.add_field(
                    name="Total Chat Ranking 👑",
                    value="Top 10 users by total affinity and chat count across all characters",
                    inline=False
                )

                await interaction.response.send_message(embed=embed, view=view)

            except Exception as e:
                print(f"Error in ranking command: {e}")
                import traceback
                print(traceback.format_exc())
                await interaction.response.send_message("An error occurred while loading ranking information.", ephemeral=True)

        @self.tree.command(
            name="affinity",
            description="Check your current affinity with the character"
        )
        async def affinity_command(interaction: discord.Interaction):
            if not isinstance(interaction.channel, discord.TextChannel):
                await interaction.response.send_message("This command can only be used in server channels.", ephemeral=True)
                return

            try:
                print("\n[Affinity check started]")
                # Find the character bot for the current channel
                current_bot = None
                for char_name, bot in self.character_bots.items():
                    if interaction.channel.id in bot.active_channels:
                        current_bot = bot
                        break

                if not current_bot:
                    await interaction.response.send_message("This command can only be used in character chat channels.", ephemeral=True)
                    return

                print(f"Character bot found: {current_bot.character_name}")

                # Get affinity info
                affinity_info = current_bot.db.get_affinity(interaction.user.id, current_bot.character_name)
                print(f"Affinity info: {affinity_info}")

                current_affinity = affinity_info['emotion_score']
                affinity_grade = get_affinity_grade(current_affinity)

                # Check for missing cards (cards for milestones below current affinity)
                missing_cards = []
                last_claimed = self.db.get_last_claimed_milestone(interaction.user.id, current_bot.character_name)  # 마지막 지급 마일스톤

                for milestone in get_milestone_list():
                    if milestone > last_claimed and current_affinity >= milestone:
                        # 지급 이력 기록 및 카드 지급
                        if not self.db.has_claimed_milestone(interaction.user.id, current_bot.character_name, milestone):
                            # 카드 지급 로직
                            tier, card_id = self.get_random_card(current_bot.character_name, interaction.user.id)
                            if card_id:
                                self.db.add_user_card(interaction.user.id, current_bot.character_name, card_id)
                                self.db.set_claimed_milestone(interaction.user.id, current_bot.character_name, milestone)
                                card_info = CHARACTER_CARD_INFO[current_bot.character_name][card_id]
                                embed = discord.Embed(
                                    title=f"🎉 New Card Acquired!",
                                    description=f"Congratulations! You have received the {current_bot.character_name} {card_id} card!",
                                    color=discord.Color.green()
                                )
                                image_path = card_info.get("image_path")
                                if image_path and os.path.exists(image_path):
                                    file = discord.File(image_path, filename=f"card_{card_id}.png")
                                    embed.set_image(url=f"attachment://{card_id}.png")
                                    await interaction.channel.send(embed=embed, file=file)
                                else:
                                    await interaction.channel.send(embed=embed)
                            else:
                                await interaction.channel.send("You have already collected all available cards!")
                        else:
                            missing_cards.append(milestone)

                # Affinity embed
                char_info = CHARACTER_INFO.get(current_bot.character_name, {})
                char_color = char_info.get('color', discord.Color.purple())

                embed = discord.Embed(
                    title=f"{char_info.get('emoji', '💝')} Affinity for {interaction.user.display_name}",
                    description=f"Affinity information with {char_info.get('name', current_bot.character_name)}.",
                    color=char_color
                )

                embed.add_field(
                    name="Affinity Score",
                    value=f"```{affinity_info['emotion_score']} points```",
                    inline=True
                )
                embed.add_field(
                    name="Today's Conversations",
                    value=f"```{affinity_info['daily_count']} times```",
                    inline=True
                )
                embed.add_field(
                    name="Affinity Grade",
                    value=f"**{affinity_grade}**",
                    inline=True
                )

                if affinity_info.get('last_message_time'):
                    try:
                        last_time_str = affinity_info['last_message_time'].split('.')[0]
                        last_time = datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S')
                        formatted_time = last_time.strftime('%Y-%m-%d %H:%M')

                        embed.add_field(
                            name="Last Conversation",
                            value=f"```{formatted_time}```",
                            inline=False
                        )
                    except Exception as e:
                        print(f"Date parsing error: {e}")
                        embed.add_field(
                            name="Last Conversation",
                            value=f"```{affinity_info['last_message_time']}```",
                            inline=False
                        )

                # If there are missing cards, add a notification
                if missing_cards:
                    embed.add_field(
                        name="📢 Claimable Cards",
                        value=f"You can claim cards for affinity milestones: {', '.join(map(str, missing_cards))}!",
                        inline=False
                    )

                print("Embed created")

                # Add character image
                char_image = CHARACTER_IMAGES.get(current_bot.character_name)
                if char_image and os.path.exists(char_image):
                    print(f"Adding character image: {char_image}")
                    embed.set_thumbnail(url=f"attachment://{current_bot.character_name.lower()}.png")
                    file = discord.File(char_image, filename=f"{current_bot.character_name.lower()}.png")
                    await interaction.response.send_message(embed=embed, file=file)
                else:
                    print("No character image")
                    await interaction.response.send_message(embed=embed)

                # If there are missing cards, show claim button for each
                for milestone in missing_cards:
                    card_id = milestone_to_card_id(milestone)
                    card_embed = discord.Embed(
                        title="🎉 Affinity Milestone Card",
                        description=f"You have not yet claimed the card for reaching affinity {milestone}.",
                        color=discord.Color.gold()
                    )
                    if card_id:
                        view = CardClaimView(interaction.user.id, card_id, current_bot.character_name, self.db)
                        await interaction.channel.send(embed=card_embed, view=view)
                    else:
                        await interaction.channel.send(embed=card_embed)

                print("[Affinity check complete]")

            except Exception as e:
                print(f"Error during affinity command: {e}")
                import traceback
                print(traceback.format_exc())
                await interaction.response.send_message("An error occurred while loading affinity information.", ephemeral=True)

        @self.tree.command(
            name="remove_admin_role",
            description="관리자 역할 제거"
        )
        async def remove_admin_role(interaction: discord.Interaction, role: discord.Role):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("This command can only be used in server channels.", ephemeral=True)
                return

            if role.id in self.settings.admin_roles:
                self.settings.remove_admin_role(role.id)
                await interaction.response.send_message(f"{role.name} role has been removed from the admin role.", ephemeral=True)
            else:
                await interaction.response.send_message(f"{role.name} role is not an admin role.", ephemeral=True)

        @self.tree.command(
            name="set_daily_limit",
            description="일일 메시지 제한 설정 (관리자 전용)"
        )
        async def set_daily_limit(interaction: discord.Interaction, limit: int):
            if not self.settings.is_admin(interaction.user):
                await interaction.response.send_message("This command can only be used in server channels.", ephemeral=True)
                return

            if limit < 1:
                await interaction.response.send_message("The limit must be 1 or more.", ephemeral=True)
                return

            self.settings.set_daily_limit(limit)

            embed = discord.Embed(
                title="Settings changed",
                description=f"The daily message limit has been set to {limit}.",
                color=discord.Color.green()
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        @self.tree.command(
            name="force_language",
            description="Force change the channel language"
        )
        @app_commands.choices(language=[
            app_commands.Choice(name="English", value="en"),
            app_commands.Choice(name="Chinese", value="zh"),
            app_commands.Choice(name="Japanese", value="ja")
        ])
        async def force_language_command(
            interaction: discord.Interaction,
            language: str
        ):
            try:
                current_bot = None
                for char_name, bot in self.character_bots.items():
                    if interaction.channel.id in bot.active_channels:
                        current_bot = bot
                        break

                if not current_bot:
                    await interaction.response.send_message("This command can only be used in character chat channels.", ephemeral=True)
                    return

                channel_id = interaction.channel.id
                user_id = interaction.user.id

                if language not in ['zh', 'en', 'ja']:
                    await interaction.response.send_message("Invalid language code. Please use: en (English), zh (Chinese), or ja (Japanese)", ephemeral=True)
                    return

                success = self.db.set_channel_language(
                    channel_id=channel_id,
                    user_id=user_id,
                    character_name=current_bot.character_name,
                    language=language
                )
                if success:
                    await interaction.response.send_message(f"Language successfully set to: {language}", ephemeral=True)
                else:
                    await interaction.response.send_message("Failed to update language settings. Please try again.", ephemeral=True)
            except Exception as e:
                print(f"Error in force_language command: {e}")
                await interaction.response.send_message("An error occurred while changing language settings.", ephemeral=True)

        @self.tree.command(
            name="mycard",
            description="Check your character cards."
        )
        async def mycard_command(interaction: discord.Interaction):
            try:
                # 현재 채널의 캐릭터 봇 찾기
                current_bot = None
                for char_name, bot in self.character_bots.items():
                    if interaction.channel.id in bot.active_channels:
                        current_bot = bot
                        break

                if not current_bot:
                    await interaction.response.send_message(
                        "This command can only be used in character chat channels.", 
                        ephemeral=True
                    )
                    return

                user_id = interaction.user.id
                character_name = current_bot.character_name

                # 카드 정보 조회
                from config import CHARACTER_CARD_INFO
                user_cards = self.db.get_user_cards(user_id, character_name)

                # 카드 티어별 수집 현황 계산 (최신 개수 반영)
                tier_counts = {
                    'C': {'total': 10, 'collected': 0},
                    'B': {'total': 7, 'collected': 0},
                    'A': {'total': 5, 'collected': 0},
                    'S': {'total': 5, 'collected': 0},  # 3 → 5
                    'Special': {'total': 2, 'collected': 0}
                }

                # 수집한 카드 수 계산
                for card_id in user_cards:
                    if card_id.startswith('C'):
                        tier_counts['C']['collected'] += 1
                    elif card_id.startswith('B'):
                        tier_counts['B']['collected'] += 1
                    elif card_id.startswith('A'):
                        tier_counts['A']['collected'] += 1
                    elif card_id.startswith('S') or card_id.startswith('kagaris'):
                        tier_counts['S']['collected'] += 1
                    elif card_id.startswith('Special'):
                        tier_counts['Special']['collected'] += 1

                # 수집 현황 임베드 생성 (디자인 개선)
                collection_embed = discord.Embed(
                    title=f"🎴 {character_name} Card Collection Status",
                    description="**Check your collection progress and show off your cards!**",
                    color=discord.Color.gold()
                )

                # 이모지 매핑
                tier_emojis = {
                    'C': '🥉',
                    'B': '🥈',
                    'A': '🥇',
                    'S': '🏆',
                    'Special': '✨'
                }
                bar_emojis = {
                    'C': '🟩',
                    'B': '🟦',
                    'A': '🟨',
                    'S': '🟪',
                    'Special': '⬛'
                }
                def get_progress_bar(percent, color_emoji, empty_emoji='⬜', length=10):
                    filled = int(percent * length)
                    empty = length - filled
                    return color_emoji * filled + empty_emoji * empty

                for tier, counts in tier_counts.items():
                    percent = counts['collected'] / counts['total'] if counts['total'] else 0
                    emoji = tier_emojis.get(tier, '')
                    color = bar_emojis.get(tier, '⬜')
                    progress_bar = get_progress_bar(percent, color)
                    collection_embed.add_field(
                        name=f"{tier} Tier {emoji}",
                        value=f"{progress_bar}  ({percent*100:.1f}%)",
                        inline=False
                    )

                total_cards = sum(counts['total'] for counts in tier_counts.values())
                total_collected = sum(counts['collected'] for counts in tier_counts.values())
                total_progress = (total_collected / total_cards) * 100

                collection_embed.add_field(
                    name="Total Collection",
                    value=f"**{total_collected} / {total_cards}**  ({total_progress:.1f}%)",
                    inline=False
                )

                await interaction.response.send_message(embed=collection_embed, ephemeral=True)

                # 카드 임베드 슬라이드 뷰 정의
                class CardSliderView(discord.ui.View):
                    def __init__(self, user_id, cards, character_name, card_info_dict):
                        super().__init__(timeout=180)
                        self.user_id = user_id
                        self.cards = cards
                        self.character_name = character_name
                        self.card_info_dict = card_info_dict
                        self.index = 0
                        self.total = len(cards)
                        self.update_buttons()

                    def update_buttons(self):
                        self.clear_items()
                        self.add_item(CardNavButton('⬅️ Previous', self, -1))
                        self.add_item(CardNavButton('Next ➡️', self, 1))
                        card_id = self.cards[self.index]
                        card_info = self.card_info_dict[self.character_name][card_id]
                        self.add_item(DiscordShareButton(
                            f"{self.character_name} {card_id}",
                            card_info.get("description", ""),
                            card_info.get("image_path", ""),
                            835838633126002721
                        ))

                    async def update_message(self, interaction):
                        card_id = self.cards[self.index]
                        card_info = self.card_info_dict[self.character_name][card_id]
                        # 전체 서버 기준 발급 순번 조회
                        issued_number = self.card_info_dict[self.character_name].get(f"{card_id}_issued_number", None)
                        if issued_number is None:
                            # DB에서 발급 순번 조회 (없으면 1로)
                            try:
                                issued_number = interaction.client.db.get_card_issued_number(self.character_name, card_id)
                            except Exception:
                                issued_number = 1
                        embed = discord.Embed(
                            title=f"My {self.character_name} Card Collection",
                            description=card_info.get("description", "No description available."),
                            color=discord.Color.from_rgb(255, 215, 0)
                        )
                        # kagaris로 시작하는 카드 ID는 S 티어로 표시
                        tier = "S" if card_id.startswith("kagaris") else card_id[0]
                        embed.add_field(name="Tier", value=tier, inline=True)
                        # Card Number: C7  #001
                        card_number_str = f"{card_id}  #{issued_number:03d}"
                        embed.add_field(name="Card Number", value=card_number_str, inline=True)
                        embed.add_field(name=" ", value="━━━━━━━━━━━━━━━━━━", inline=False)
                        if os.path.exists(card_info["image_path"]):
                            file = discord.File(card_info["image_path"], filename=f"card_{card_id}.png")
                            embed.set_image(url=f"attachment://{card_id}.png")
                            embed.set_footer(text=f"Card {self.index+1} of {self.total}")
                            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
                        else:
                            embed.add_field(name="Notice", value="Card image not found.")
                            embed.set_footer(text=f"Card {self.index+1} of {self.total}")
                            await interaction.response.edit_message(embed=embed, view=self)

                class CardNavButton(discord.ui.Button):
                    def __init__(self, label, view, direction):
                        super().__init__(label=label, style=discord.ButtonStyle.primary)
                        self.view_ref = view
                        self.direction = direction

                    async def callback(self, interaction: discord.Interaction):
                        if interaction.user.id != self.view_ref.user_id:
                            await interaction.response.send_message("Only you can navigate your cards.", ephemeral=True)
                            return
                        self.view_ref.index = (self.view_ref.index + self.direction) % self.view_ref.total
                        self.view_ref.update_buttons()
                        await self.view_ref.update_message(interaction)

                if user_cards:
                    slider_view = CardSliderView(interaction.user.id, sorted(user_cards), character_name, CHARACTER_CARD_INFO)
                    first_card_id = sorted(user_cards)[0]
                    first_card_info = CHARACTER_CARD_INFO[character_name][first_card_id]
                    embed = discord.Embed(
                        title=f"{character_name} {first_card_id} Card",
                        description=first_card_info.get("description", "No description available."),
                        color=discord.Color.from_rgb(255, 215, 0)
                    )
                    # 이모지 매핑
                    tier_emojis = {
                        'C': '🥉',
                        'B': '🥈',
                        'A': '🥇',
                        'S': '🏆',
                        'Special': '✨'
                    }
                    tier_emoji = tier_emojis.get(first_card_id[0], '')
                    embed.add_field(name="Tier", value=f"{first_card_id[0]} Tier {tier_emoji}", inline=True)
                    embed.add_field(name="Card Number", value=first_card_id, inline=True)
                    embed.add_field(name=" ", value="━━━━━━━━━━━━━━━━━━", inline=False)
                    if os.path.exists(first_card_info["image_path"]):
                        file = discord.File(first_card_info["image_path"], filename=f"card_{first_card_id}.png")
                        embed.set_image(url=f"attachment://card_{first_card_id}.png")
                        embed.set_footer(text=f"Card 1 of {len(user_cards)}")
                        await interaction.followup.send(embed=embed, file=file, view=slider_view, ephemeral=True)
                    else:
                        embed.add_field(name="Notice", value="Card image not found.")
                        embed.set_footer(text=f"Card 1 of {len(user_cards)}")
                        await interaction.followup.send(embed=embed, view=slider_view, ephemeral=True)
                else:
                    await interaction.followup.send(
                        "You have not collected any cards yet.", 
                        ephemeral=True
                    )

            except Exception as e:
                print(f"Error in mycard command: {e}")
                import traceback
                print(traceback.format_exc())
                await interaction.response.send_message(
                    "An error occurred while loading card information.", 
                    ephemeral=True
                )

        @self.tree.command(
            name="check_language",
            description="현재 채널의 언어를 확인합니다."
        )
        async def check_language_command(interaction: discord.Interaction):
            try:
                # 현재 채널의 캐릭터 봇 찾기
                current_bot = None
                for char_name, bot in self.character_bots.items():
                    if interaction.channel.id in bot.active_channels:
                        current_bot = bot
                        break

                if not current_bot:
                    await interaction.response.send_message("This command can only be used in character chat channels.", ephemeral=True)
                    return

                channel_id = interaction.channel.id
                user_id = interaction.user.id
                current_lang = self.db.get_channel_language(
                    channel_id=channel_id,
                    user_id=user_id,
                    character_name=current_bot.character_name
                )

                from config import SUPPORTED_LANGUAGES
                language_name = SUPPORTED_LANGUAGES.get(current_lang, {}).get("name", "Unknown")

                embed = discord.Embed(
                    title="🌍 language settings",
                    description=f"current language: {language_name} ({current_lang})",
                    color=discord.Color.blue()
                )

                available_languages = "\n".join([
                    f"• {info['name']} ({code})" 
                    for code, info in SUPPORTED_LANGUAGES.items()
                ])

                embed.add_field(
                    name="available languages",
                    value=available_languages,
                    inline=False
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                print(f"Error in check_language command: {e}")
                await interaction.response.send_message(
                    "An error occurred while checking language settings.",
                    ephemeral=True
                )

        @self.tree.command(
            name="story",
            description="Play story chapters for each character."
        )
        async def story_command(interaction: discord.Interaction):
            from config import CHARACTER_INFO, STORY_CHAPTERS

            # 현재 채널의 캐릭터 봇 찾기
            current_bot = None
            for char_name, bot in self.character_bots.items():
                if interaction.channel.id in bot.active_channels:
                    current_bot = bot
                    break

            if not current_bot:
                await interaction.response.send_message("This command can only be used in character chat channels.", ephemeral=True)
                return

            # 친밀도 등급 체크
            affinity_info = current_bot.db.get_affinity(interaction.user.id, current_bot.character_name)
            current_affinity = affinity_info['emotion_score']
            affinity_grade = get_affinity_grade(current_affinity)

            # 골드 레벨이 아닌 경우 경고 메시지 표시
            if affinity_grade != "Gold":
                embed = discord.Embed(
                    title="⚠️ Story Mode Locked",
                    description="Story mode is only available for Gold level users.",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Current Level",
                    value=f"**{affinity_grade}**",
                    inline=True
                )
                embed.add_field(
                    name="Required Level",
                    value="**Gold**",
                    inline=True
                )
                embed.add_field(
                    name="How to Unlock",
                    value="Keep chatting with the character to increase your affinity level!",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # 골드 레벨인 경우 기존 스토리 모드 진행
            options = [
                discord.SelectOption(
                    label=selected_char,
                    description=CHARACTER_INFO[selected_char]['description'],
                    value=selected_char
                )
                for selected_char in CHARACTER_INFO.keys()
            ]
            select = discord.ui.Select(
                placeholder="Please select a character to chat with...",
                min_values=1,
                max_values=1,
                options=options
            )

            async def select_callback(select_interaction: discord.Interaction):
                selected_char = select.values[0]
                if selected_char != current_bot.character_name:
                    await select_interaction.response.send_message(
                        "Please use it on the character channel.", ephemeral=True
                    )
                    return
                try:
                    user_id = select_interaction.user.id
                    character_bot = self.character_bots.get(selected_char)
                    if not character_bot:
                        await select_interaction.response.send_message("The character bot cannot be found..", ephemeral=True)
                        return

                    # 챕터 리스트 생성
                    chapters = STORY_CHAPTERS.get(selected_char, [])
                    if not chapters:
                        await select_interaction.response.send_message("There is no story chapter for this character..", ephemeral=True)
                        return

                    chapter_options = [
                        discord.SelectOption(
                            label=f"{c['emoji']} {c['title']}",
                            description=c.get('content', ''),
                            value=str(c['id'])
                        ) for c in chapters
                    ]
                    chapter_select = discord.ui.Select(
                        placeholder="Please select a chapter to play.",
                        min_values=1,
                        max_values=1,
                        options=chapter_options
                    )

                    async def chapter_callback(chapter_interaction: discord.Interaction):
                        try:
                            await chapter_interaction.response.defer(ephemeral=True)
                            chapter_id = int(chapter_select.values[0])

                            # 새로운 스토리 채널 생성
                            guild = chapter_interaction.guild
                            channel_name = f"{selected_char.lower()}-story-{chapter_interaction.user.name.lower()}"
                            category = discord.utils.get(guild.categories, name="chatbot")
                            if not category:
                                category = await guild.create_category("chatbot")

                            # 기존 스토리 채널이 있다면 삭제
                            existing_channel = discord.utils.get(category.text_channels, name=channel_name)
                            if existing_channel:
                                await existing_channel.delete()

                            # 새 채널 생성
                            overwrites = {
                                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                chapter_interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                            }
                            channel = await guild.create_text_channel(
                                name=channel_name,
                                category=category,
                                overwrites=overwrites
                            )

                            # 스토리 모드 시작
                            chapter = STORY_CHAPTERS[selected_char][chapter_id - 1]
                            embed = discord.Embed(
                                title=chapter["title"],
                                description=chapter.get("description", ""),
                                color=CHARACTER_INFO[selected_char]["color"]
                            )

                            if selected_char == "Kagari":
                                embed.add_field(
                                    name="🌸 Welcome to a Special Moment",
                                    value=(
                                        "Welcome to a special 5-minute story under the cherry blossoms. "
                                        "In this moment, you're spending quiet time with Kagari — a reserved, graceful half-yokai who rarely expresses her feelings. "
                                        "But… somewhere behind her calm gaze, a soft heart quietly hopes for warmth. "
                                        "Your goal is simple: ✨ Talk with her. Make her feel something. One word at a time."
                                    ),
                                    inline=False
                                )
                                embed.add_field(
                                    name="💬 How it works",
                                    value=(
                                        "1. Kagari will gently guide the conversation, and your responses will affect how close she feels to you.\n"
                                        "2. She doesn't say it out loud… but she's keeping score — based on how you make her feel.\n"
                                        "3. Speak with sincerity and subtlety, and she might just open her heart.\n"
                                        "4. Be too blunt or pushy? She'll retreat — and the moment might slip away."
                                    ),
                                    inline=False
                                )
                                embed.add_field(
                                    name="🎴 Card Rewards",
                                    value=(
                                        "At the end of this story, Kagari will judge your connection — and based on how you made her feel, you may receive a special card.\n\n"
                                        "🟥 **High score** (warm, sincere, respectful)\n"
                                        "→ S-tier or Special Kagari Card 🌸\n\n"
                                        "🟨 **Medium score** (neutral to light warmth)\n"
                                        "→ Standard Kagari Card\n\n"
                                        "⬛ **Low score** (awkward, cold, or too pushy)\n"
                                        "→ No card... just a cold breeze and silence.\n\n"
                                        "🌟 Your words matter. A simple sentence can shape the memory — and the reward."
                                    ),
                                    inline=False
                                )
                                embed.add_field(
                                    name="🧭 Tone Tips",
                                    value=(
                                        "🕊 Start softly. Kagari opens up only to those who earn her trust.\n\n"
                                        "💬 Use gentle, meaningful words — not flashy compliments.\n\n"
                                        "🎭 Let the silence speak too. Kagari isn't chatty, but she listens deeply.\n\n"
                                        "Her replies may feel distant at first:\n"
                                        "\"...I see.\" / \"That's... unexpected.\" / \"Mm. Thank you, I suppose.\"\n\n"
                                        "But as your words reach her — you might see a smile you'll never forget."
                                    ),
                                    inline=False
                                )
                                embed.add_field(
                                    name="Ready to Begin?",
                                    value="Then say something... and let's see where her heart leads.\n\n🌸🍃",
                                    inline=False
                                )
                            elif selected_char == "Eros":
                                embed.add_field(
                                    name="🐝 Eros Story Mode – special detective story",
                                    value=(
                                        "Welcome to Eros's special detective story!\n"
                                        "Her precious gift for the Spot Zero team has gone missing… and she needs your help to find the culprit. 💔\n"
                                        "You'll chat with Eros over 20 turns, collect clues, and solve the mystery together."
                                    ),
                                    inline=False
                                )
                                embed.add_field(
                                    name="🔍 Your Mission",
                                    value=(
                                        "Combine the clues Eros gives you to identify the thief after turn 20 — and help her recover the stolen gift!"
                                    ),
                                    inline=False
                                )
                                embed.add_field(
                                    name="🧠 Tips for Talking to Eros",
                                    value=(
                                        "🗨️ She's emotional, so speak gently.\n\n"
                                        "🚫 Don't use commands or be too forceful.\n\n"
                                        "✅ Comfort her or ask thoughtful questions about the clues.\n\n"
                                        "💬 Eros will use small expressions like (sniffles), (thinking), or (hopeful eyes) — pay attention to her feelings.\n\n"
                                        "❗ She won't say \"thank you\" — she's focused on solving the case."
                                    ),
                                    inline=False
                                )
                                embed.add_field(
                                    name="🎴 Card Rewards",
                                    value=(
                                        "Based on your emotional connection and the flow of your conversation,\n"
                                        "you'll receive a final reward card depending on your score with Eros."
                                    ),
                                    inline=False
                                )
                                embed.add_field(
                                    name="Ready to Begin?",
                                    value="Are you ready to solve the case together? 🐾\nLet's begin… she's counting on you. 💛",
                                    inline=False
                                )

                            if chapter.get("thumbnail"):
                                embed.set_thumbnail(url=chapter["thumbnail"])
                            await channel.send(embed=embed)

                            # 하이퍼링크 메시지 전송
                            story_link = f"https://discord.com/channels/{guild.id}/{channel.id}"
                            await chapter_interaction.followup.send(
                                f"[Go to your story channel]({story_link})\nStory has started!",
                                ephemeral=True
                            )

                            # 스토리 모드 시작
                            await run_story_scene(
                                self, channel, chapter_interaction.user, selected_char, chapter_id, 1
                            )

                        except Exception as e:
                            print(f"[ERROR] chapter_callback: {e}")
                            import traceback
                            print(traceback.format_exc())
                            if not chapter_interaction.response.is_done():
                                await chapter_interaction.response.send_message(
                                    f"에러 발생: {e}",
                                    ephemeral=True
                                )
                            else:
                                await chapter_interaction.followup.send(
                                    f"에러 발생: {e}",
                                    ephemeral=True
                                )

                    chapter_select.callback = chapter_callback
                    chapter_view = discord.ui.View()
                    chapter_view.add_item(chapter_select)
                    await select_interaction.response.send_message(
                        'Please select a story chapter for ' + selected_char + ':',
                        view=chapter_view,
                        ephemeral=True
                    )

                except Exception as e:
                    import traceback
                    print(traceback.format_exc())
                    await select_interaction.response.send_message(f"에러 발생: {e}", ephemeral=True)

            select.callback = select_callback
            view = discord.ui.View()
            view.add_item(select)
            await interaction.response.send_message(
                "Please select a character:",
                view=view,
                ephemeral=True
            )

        @self.tree.command(
            name="message_add",
            description="관리자: 유저의 메시지 수를 수동으로 추가합니다."
        )
        async def message_add_command(interaction: discord.Interaction, target: discord.Member, count: int, character: str):
            if not self.settings.is_admin(interaction.user):
                await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
                return
            # DB에 메시지 추가 (실제 메시지 insert)
            for _ in range(count):
                await self.db.add_message(
                    channel_id=0,  # 시스템 메시지이므로 0
                    user_id=target.id,
                    character_name=character,
                    role="user",
                    content="[관리자 메시지 추가]",
                    language="en"
                )
            embed = discord.Embed(
                title="메시지 수 추가 완료",
                description=f"{target.display_name}의 {character} 메시지 수가 {count}만큼 증가했습니다.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @self.tree.command(
            name="affinity_set",
            description="Admin: Manually set a user's affinity score."
        )
        async def affinity_set_command(interaction: discord.Interaction, target: discord.Member, value: int, character: str):
            if not self.settings.is_admin(interaction.user):
                await interaction.response.send_message("This command can only be used by admins.", ephemeral=True)
                return
            # affinity 직접 수정
            try:
                # 락이 필요 없다면 아래 한 줄만!
                self.db.set_affinity(target.id, character, value)
                grade = get_affinity_grade(value)
                embed = discord.Embed(
                    title="Affinity Score Updated",
                    description=f"{target.display_name}'s {character} affinity score is set to {value}.\nCurrent grade: **{grade}**",
                    color=discord.Color.gold()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"오류: {e}", ephemeral=True)

        @self.tree.command(
            name="card_give",
            description="Admin: Manually give a card to a user."
        )
        async def card_give_command(interaction: discord.Interaction, target: discord.Member, character: str, card_id: str):
            if not self.settings.is_admin(interaction.user):
                await interaction.response.send_message("Only admins can use this command.", ephemeral=True)
                return
            success = self.db.add_user_card(target.id, character, card_id)
            if success:
                embed = discord.Embed(
                        title="Card given",
                        description=f"{target.display_name} has been given the {character} {card_id} card.",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="Card giving failed",
                    description=f"The card {card_id} has already been given or the giving failed.",
                    color=discord.Color.red()
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @self.tree.command(
            name="message_add_total",
            description="Admin: Manually set a user's total message count."
        )
        async def message_add_total_command(interaction: discord.Interaction, target: discord.Member, total: int):
            if not self.settings.is_admin(interaction.user):
                await interaction.response.send_message("Only admins can use this command.", ephemeral=True)
                return
            if total < 0:
                await interaction.response.send_message("The message count must be 0 or more.", ephemeral=True)
                return
            # 유저의 현재 총 메시지 수 확인
            current_count = await self.db.get_user_message_count(target.id)
            to_add = total - current_count
            if to_add > 0:
                for _ in range(to_add):
                    await self.db.add_message(
                        channel_id=0,  # 시스템 메시지이므로 0
                        user_id=target.id,
                        character_name="system",  # 또는 None/공백 등
                        role="user",
                        content="[관리자 메시지 추가]",
                        language="en"
                    )
                await interaction.response.send_message(f"{target.display_name}'s total message count is set to {total}.", ephemeral=True)
            elif to_add == 0:
                await interaction.response.send_message(f"{target.display_name}'s total message count is already {total}.", ephemeral=True)
            else:
                await interaction.response.send_message(f"{target.display_name}'s total message count ({current_count} times) exceeds {total}. (Decrease is not supported)", ephemeral=True)

        @self.tree.command(
            name="help",
            description="How to use the chatbot, affinity, card, story, ranking, FAQ guide"
        )
        async def help_command(interaction: discord.Interaction):
            help_topics = [
                ("🤖 How to Use the Chatbot", "how_to_use"),
                ("❤️ Affinity & Level System", "affinity"),
                ("🎴 Card & Reward System", "card"),
                ("🎭 Story Mode", "story"),
                ("🏆 Ranking System", "ranking"),
                ("❓ FAQ", "faq"),
            ]
            options = [
                discord.SelectOption(label=title, value=key)
                for title, key in help_topics
            ]
            class HelpSelect(discord.ui.Select):
                def __init__(self):
                    super().__init__(placeholder="Select a help topic", min_values=1, max_values=1, options=options)
                async def callback(self, interaction2: discord.Interaction):
                    topic = self.values[0]
                    embed = discord.Embed(color=discord.Color.blurple())
                    if topic == "how_to_use":
                        embed.title = "🤖 How to Use the Chatbot"
                        embed.add_field(name="How to Talk with Characters", value="- Use /bot to create a private chat channel with a character like Kagari or Eros.\n- Supports multilingual input (EN/JP/ZH), responses are always in English.\n- Characters react to your emotions, tone, and depth of conversation.\n🧠 Pro Tip: The more emotionally engaging your dialogue, the faster you grow your bond!", inline=False)
                    elif topic == "affinity":
                        embed.title = "❤️ Affinity & Level System"
                        embed.add_field(name="Level Up with Conversations", value="- Rookie (1–10 msgs): Basic chat only.\n- Iron (11–30): Unlock C-rank cards & light emotion.\n- Silver (31–60): A/B/C cards & story mood options.\n- Gold (61+): S-tier chance & story unlock.\n- Gold+ (100+): Higher A-rank chance + special tone.\nCommand: /affinity to check your current level, progress, and daily message stats.", inline=False)
                    elif topic == "card":
                        embed.title = "🎴 Card & Reward System"
                        embed.add_field(name="How to Earn & Collect Cards", value="You earn cards through:\n- 🗣️ Emotional chat: score-based triggers (10/20/30)\n- 🎮 Story Mode completions\n- ❤️ Affinity milestone bonuses\nCard Tier Example (Gold user):\n- A (20%) / B (40%) / C (40%)\n- Gold+ user: A (35%) / B (35%) / C (30%)\n📜 Use /mycard to view your collection.", inline=False)
                    elif topic == "story":
                        embed.title = "🎭 Story Mode"
                        embed.add_field(name="Play Story Chapters with Your Favorite Characters", value="Start with /story start [character]\nStory Mode is only open to users with Gold status or higher. Story Mode allows you to earn Tier Cards.\n\nScenarios:\n- Kagari: 🌸 Spring date under the cherry blossoms\n- Eros: 🕵️ Track down the mysterious gift thief\n🎯 30+ dialogue turns → score-based endings (positive/neutral/negative)\n🃏 Ending gives you a card (based on performance)", inline=False)
                    elif topic == "ranking":
                        embed.title = "🏆 Ranking System"
                        embed.add_field(name="Want to know who's building the strongest bond with each character?", value="Our Crush Rankings track the top players based on weekly interaction scores!\n\nHow it works:\n- Rankings are based on your weekly Crush Score from chats and stories\n- Updated every Monday 00:00 UTC (Sunday reset)\n- Rank = sum of crush points with that character\nCommands:\n- /ranking — View current top players", inline=False)
                    elif topic == "faq":
                        embed.title = "❓ FAQ"
                        embed.add_field(name="Q1: How can I get Q cards or grade cards?", value="A: You can get A–C grade cards through 1:1 general chat with characters.\nHowever, your Crush level determines the probability and tier of the card you receive.\nCheck /help affinity & level system to see what tier unlocks which card grades.", inline=False)
                        embed.add_field(name="Q2: How are rewards calculated in Story Mode?", value="A: There are two score systems in Story Mode:\n- Mission Clear Logic: Each story has a mission goal. If you clear it, you're guaranteed an S-tier card.\n- Affinity Score Logic: Your outcome is affected by how close you are with the character.\nIf your crush score is too low, you may not receive a card at all. Higher crush = higher card tier and more beautiful card art!", inline=False)
                        embed.add_field(name="Q3: What changes based on my Crush with the character?", value="A: Character tone, reaction, and card chances all change based on your Affinity level.\n- Higher Affinity = More natural or intimate dialogue\n- Higher Affinity = Better chance at A-tier or S-tier cards\n- Lower Affinity = Dull responses, chance of being rejected\nUse /affinity to track your current level with each character.", inline=False)
                    await interaction2.response.send_message(embed=embed, ephemeral=True)
            class HelpView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=180)
                    self.add_item(HelpSelect())
            embed = discord.Embed(
                title="Help Menu",
                description="Select a topic below to learn more!",
                color=discord.Color.blurple()
            )
            await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)

        @self.tree.command(
            name="feedback",
            description="Leave your feedback"
        )
        async def feedback_command(interaction: discord.Interaction):
            embed = discord.Embed(
                title="Thank you for playing Zerolink!",
                description="The program is currently in the testing phase, so there may be some bugs and incomplete features. Please leave your feedback through the link below (in English)",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📧 Feedback Form",
                value="[Click here to leave feedback](https://docs.google.com/forms/u/1/d/e/1FAIpQLSf4Y2QMiPvFPoYv5kzq_r1iqUmOKTo4RUjPi3xopOEQU6_qXw/viewform)",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def setup_hook(self):
        print("봇 초기화 중...")
        try:
            await self.tree.sync()
            print("Commands synced!")
        except Exception as e:
            print(f"Error syncing commands: {e}")

    def detect_language(self, text: str) -> str:
        try:
            text_without_brackets = re.sub(r'\([^)]*\)', '', text)
            text_clean = re.sub(r'[^a-zA-Z\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\s]', '', text_without_brackets)
            text_clean = text_clean.strip()
            if not text_clean:
                return 'en'
            detected = langdetect.detect(text_clean)
            lang_map = {
                'zh-cn': 'zh', 'zh-tw': 'zh', 'zh': 'zh',
                'ja': 'ja',
                'ko': 'en',
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
                'ko': 'en',
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
        'ko': 'en',
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
        language_instructions = [
            {"role": "system", "content": f"CRITICAL: You MUST respond ONLY in {channel_language.upper()}. If you respond in any other language, reply with: (system error) Only {channel_language.upper()} is allowed."},
            {"role": "system", "content": f"IMPORTANT: Even if previous messages are in another language, you MUST reply ONLY in {channel_language.upper()}."}
        ]
        # ... 캐릭터 프롬프트 등 추가 ...

        # 응답 생성 및 언어 검증
        for attempt in range(3):
            response = await self.get_ai_response(language_instructions + filtered_recent + [{"role": "user", "content": user_message}])
            response_language = self.detect_language(response)
            if response_language == channel_language:
                return response
        # 3번 모두 실패하면 강제 오류 메시지
        return f"(system error) Only {channel_language.upper()} is allowed."

    async def process_message(self, message):
        try:
            if message.author.bot or not message.guild:
                return

            if message.content.startswith('/'):
                await super().on_message(message)
                return

            if message.channel.id not in self.active_channels:
                return

            # 메시지 저장
            await self.db.add_message(
                message.channel.id,
                message.author.id,
                self.character_name,
                "user",
                message.content
            )

            # 친밀도 업데이트 및 새로운 친밀도 점수 받기
            affinity_info = self.db.get_affinity(message.author.id, self.character_name)
            current_affinity = affinity_info['emotion_score']
            new_affinity, _ = self.db.update_affinity(message.author.id, self.character_name, message.content)

            # 레벨업 체크 및 임베드 출력
            print(f"[DEBUG] current_affinity: {current_affinity}, new_affinity: {new_affinity}")
            current_grade = get_affinity_grade(current_affinity)
            new_grade = get_affinity_grade(new_affinity)
            print(f"[DEBUG] current_grade: {current_grade}, new_grade: {new_grade}")

            if new_affinity > current_affinity:
                print("[DEBUG] Affinity increased!")
                if current_grade != new_grade:
                    print("[DEBUG] Level up detected!")
                    embed = get_levelup_embed(new_grade)
                    await message.channel.send(embed=embed)
                else:
                    print("[DEBUG] No level up (grade unchanged)")
            else:
                print("[DEBUG] Affinity did not increase")

            # 마일스톤 카드 지급 로직
            milestone = None
            if new_affinity == 10:
                milestone = 10
            elif new_affinity > 10 and (new_affinity - 10) % 10 == 0:
                milestone = new_affinity
            if milestone:
                if not self.db.has_user_card(message.author.id, self.character_name, milestone):
                    embed = discord.Embed(
                        title="🎉 Milestone Reached!",
                        description=f"You reached {milestone} affinity! Claim your card!",
                        color=discord.Color.gold()
                    )
                    view = CardClaimView(message.author.id, milestone, self.character_name, self.db)
                    await message.channel.send(embed=embed, view=view)

            # AI 응답 생성
            async with message.channel.typing():
                # 최근 메시지 가져오기
                recent_messages = [m["content"] for m in self.db.get_recent_messages(message.channel.id, self.character_name, limit=5)]
                for _ in range(3):  # 최대 3번 재시도
                    response = await self.get_ai_response([{"role": "user", "content": message.content}])
                    if not is_duplicate_message(response, recent_messages):
                        break
                else:
                    response = "(system) Sorry, I couldn't generate a new response."
                await message.channel.send(response)

                # AI 응답 저장
                await self.db.add_message(
                    message.channel.id,
                    message.author.id,
                    self.character_name,
                    "assistant",
                    response
                )

        except Exception as e:
            print(f"Error in message processing: {e}")
            import traceback
            print(traceback.format_exc())
            await message.channel.send("I'm sorry. An error has occurred.")

    def get_random_card(self, character_name: str, user_id: int, is_story_mode=False) -> tuple:
        try:
            user_cards = self.db.get_user_cards(user_id, character_name)
            available_cards = {
                'C': [],
                'B': [],
                'A': [],
                'S': [],
                'Special': []
            }
            for tier in available_cards.keys():
                if tier == 'S' and not is_story_mode:
                    continue  # 일반 대화에서는 S카드 제외
                for i in range(1, self.tier_card_counts[tier] + 1):
                    card_id = f"{tier}{i}"
                    if card_id not in user_cards:
                        available_cards[tier].append(card_id)
            available_tiers = {
                tier: cards for tier, cards in available_cards.items() 
                if cards and tier in self.card_probabilities
            }
            if not available_tiers:
                return None, None
            tier = random.choices(
                list(available_tiers.keys()),
                weights=[self.card_probabilities[t] for t in available_tiers.keys()],
                k=1
            )[0]
            selected_card = random.choice(available_tiers[tier])
            return tier, selected_card
        except Exception as e:
            print(f"Error in get_random_card: {e}")
            return None, None

    def milestone_to_card_id(self, milestone: int) -> str:
        milestone_map = {
            10: "C1",
            15: "C2",
            20: "C3",
            # 필요시 추가
        }
        return milestone_map.get(milestone)

class CardClaimView(discord.ui.View):
    def __init__(self, user_id, card_id, character_name, db_manager, is_story_mode=False):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.card_id = card_id
        self.character_name = character_name
        self.db_manager = db_manager
        self.animation_task = None
        self.message = None
        self.animation_running = True
        self.confirmed = False
        self.add_item(CardClaimButton(user_id, card_id, character_name, db_manager, self, is_story_mode=is_story_mode))

    async def start_animation(self, message, tier, character_name):
        from config import CHARACTER_CARD_INFO
        import random
        self.message = message
        self.animation_running = True

        # 카드 ID 형식 변환 (숫자만 있는 경우 티어+숫자 형식으로 변환)
        if self.card_id.isdigit():
            self.card_id = f"{tier}{self.card_id}"

        all_card_ids = [cid for cid in CHARACTER_CARD_INFO[character_name] if cid.startswith(tier)]
        for _ in range(7):  # 7회 애니메이션
            if not self.animation_running:
                break
            show_card = random.choice(all_card_ids)
            card_info = CHARACTER_CARD_INFO[character_name][show_card]
            embed = discord.Embed(
                title="🎲 Rolling...",
                description="Which card will you get?",
                color=discord.Color.blurple()
            )
            if os.path.exists(card_info["image_path"]):
                file = discord.File(card_info["image_path"], filename=f"card_{show_card}.png")
                embed.set_image(url=f"attachment://card_{show_card}.png")
                await message.edit(embed=embed, attachments=[file], view=self)
            else:
                print(f"Card image not found: {card_info['image_path']}")
                await message.edit(embed=embed, view=self)
            await asyncio.sleep(1)
        # 마지막엔 확정 카드가 아닌, Claim 버튼이 활성화된 상태로 대기
        self.animation_running = False

class CardClaimButton(discord.ui.Button):
    def __init__(self, user_id: int, card_id: str, character_name: str, db, view, is_story_mode=False):
        super().__init__(
            label="Claim",
            style=discord.ButtonStyle.green,
            custom_id=f"claim_card_{user_id}_{card_id}"
        )
        self.user_id = user_id
        self.card_id = card_id
        self.character_name = character_name
        self.db = db
        self.parent_view = view
        self.is_story_mode = is_story_mode

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("지정된 유저만 클릭할 수 있습니다.", ephemeral=True)
            return
        try:
            self.parent_view.animation_running = False
            from config import CHARACTER_CARD_INFO
            # 스토리 모드 S카드 지급 정책
            if self.is_story_mode:
                has_card = self.db.has_user_card(self.user_id, self.character_name, self.card_id)
                if has_card:
                    embed = discord.Embed(
                        title="Duplicate cards, cannot be acquired",
                        description=f"You cannot obtain this because you already have the card [{self.card_id}].",
                        color=discord.Color.red()
                    )
                    await interaction.response.edit_message(embed=embed, view=None)
                    await interaction.channel.send("Story mode has ended, please enter /close to close the channel.")
                    self.disabled = True
                    return
                success = self.db.add_user_card(self.user_id, self.character_name, self.card_id)
                card_info = CHARACTER_CARD_INFO.get(self.character_name, {}).get(self.card_id, {})
                if success:
                    embed = discord.Embed(
                        title="🎉 S Card Claimed!",
                        description=f"Congratulations! You have obtained the {self.character_name} {self.card_id} card!",
                        color=discord.Color.gold()
                    )
                    image_path = card_info.get("image_path")
                    if image_path and os.path.exists(image_path):
                        file = discord.File(image_path, filename=f"card_{self.card_id}.png")
                        embed.set_image(url=f"attachment://card_{self.card_id}.png")
                        await interaction.response.edit_message(embed=embed, attachments=[file], view=None)
                    else:
                        await interaction.response.edit_message(embed=embed, view=None)
                    await interaction.channel.send("Story mode has ended, please enter /close to close the channel.")
                    self.disabled = True
                else:
                    await interaction.response.send_message("Card payout failed, please contact your manager.", ephemeral=True)
                return
            # ... 이하 기존 일반 카드 지급 로직 ...
            # 기존 일반 카드 수령 로직 (랜덤 카드, 중복 시 안내)
            # 카드 ID 형식 변환 (숫자만 있는 경우 티어+숫자 형식으로 변환)
            if self.card_id.isdigit():
                tier = self.card_id[0] if len(self.card_id) > 1 else 'C'  # 기본값으로 C 티어 사용
                self.card_id = f"{tier}{self.card_id}"

            from config import CHARACTER_CARD_INFO
            # 카드 지급
            print("수령 시도:", self.user_id, self.character_name, self.card_id)
            has_card = self.db.has_user_card(self.user_id, self.character_name, self.card_id)
            print("이미 보유 여부:", has_card)
            # 중복일 경우 같은 티어의 미보유 카드 지급
            if has_card:
                # 중복 안내 및 소각 처리
                embed = discord.Embed(
                    title="Sorry, duplicate card burned!!",
                    description=f"You have obtained a duplicate card [{self.card_id}]Try drawing a card again next time!",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=None)
                self.disabled = True
                return
            success = self.db.add_user_card(self.user_id, self.character_name, self.card_id)
            print("DB 저장 성공:", success)
            card_info = CHARACTER_CARD_INFO.get(self.character_name, {}).get(self.card_id, {})
            print("카드 정보:", card_info)
            if has_card:
                await interaction.response.send_message("You have already claimed this card.", ephemeral=True)
                # 스토리 종료 안내 메시지 추가
                await interaction.channel.send("This story has ended. Please close the chat with /close!")
                return
            if success:
                embed = discord.Embed(
                    title="🎉 Card Claimed!",
                    description=f"Congratulations! You have claimed the {self.character_name} {self.card_id} card! Use `/mycard` to check your cards!",
                    color=discord.Color.green()
                )
                image_path = card_info.get("image_path")
                if image_path and os.path.exists(image_path):
                    file = discord.File(image_path, filename=f"card_{self.card_id}.png")
                    embed.set_image(url=f"attachment://card_{self.card_id}.png")
                    view = CardClaimView(f"{self.character_name} {self.card_id}", card_info.get("description", ""), image_path)
                    await interaction.response.edit_message(embed=embed, attachments=[file], view=view)
                else:
                    print(f"Card image not found: {image_path}")
                    view = CardClaimView(f"{self.character_name} {self.card_id}", card_info.get("description", ""), "")
                    await interaction.response.edit_message(embed=embed, view=view)
                self.disabled = True
                # 스토리 종료 안내 메시지 추가
                await interaction.channel.send("This story has ended. Please close the chat with /close!")
            else:
                await interaction.response.send_message("Failed to claim the card. Please try again.", ephemeral=True)
        except Exception as e:
            print(f"Error while claiming card: {e}")
            await interaction.response.send_message("An error occurred while claiming the card.", ephemeral=True)

class DiscordShareButton(discord.ui.Button):
    def __init__(self, card_name, card_desc, image_path, channel_id=None):
        super().__init__(label="Share to Discord", style=discord.ButtonStyle.primary, emoji="💬")
        self.card_name = card_name
        self.card_desc = card_desc
        self.image_path = image_path
        # 공유 채널 ID를 새 값으로 고정
        self.channel_id = 1376830716855189575

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(self.channel_id)
        if channel:
            embed = discord.Embed(title=self.card_name, description=self.card_desc, color=discord.Color.gold())
            embed.set_footer(text=f"Shared by: {interaction.user.display_name} ({interaction.user.id})", icon_url=interaction.user.display_avatar.url)
            if self.image_path and os.path.exists(self.image_path):
                file = discord.File(self.image_path, filename=os.path.basename(self.image_path))
                embed.set_image(url=f"attachment://{os.path.basename(self.image_path)}")
                await channel.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed)
            channel_mention = channel.mention if hasattr(channel, 'mention') else f"<# {channel.id}>"
            await interaction.response.send_message(f"Card has been shared to {channel_mention}!", ephemeral=True)
        else:
            await interaction.response.send_message("Failed to find the share channel.", ephemeral=True)

class CardShareView(discord.ui.View):
    def __init__(self, card_name, card_desc, image_path):
        super().__init__()
        self.add_item(DiscordShareButton(card_name, card_desc, image_path, 1376830716855189575))

class RankingSelect(discord.ui.Select):
    def __init__(self, db):
        self.db = db
        options = [
            discord.SelectOption(
                label="Total Ranking",
                description="View total chat ranking across all characters",
                value="total",
                emoji="👑"
            )
        ]
        for char_name, char_info in CHARACTER_INFO.items():
            options.append(
                discord.SelectOption(
                    label=f"{char_name} Ranking",
                    description=f"View {char_name} chat ranking",
                    value=char_name,
                    emoji=char_info['emoji']
                )
            )
        super().__init__(
            placeholder="Select ranking type",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        print("[DEBUG] RankingSelect callback called")
        try:
            await interaction.response.defer()
            character_name = self.values[0]
            user_id = interaction.user.id

            if character_name == "total":
                rankings = self.db.get_total_ranking()
                user_rank = self.db.get_user_total_rank(user_id)
                stats = self.db.get_user_stats(user_id)
                affinity = stats.get('total_affinity', 0) if stats else 0
                title = "👑 Total Chat Ranking TOP 10"
                color = discord.Color.gold()
            else:
                rankings = self.db.get_character_ranking(character_name)
                user_rank = self.db.get_user_character_rank(user_id, character_name)
                stats = self.db.get_user_stats(user_id, character_name)
                affinity = stats.get('affinity', 0) if stats else 0
                char_info = CHARACTER_INFO[character_name]
                title = f"{char_info['emoji']} {character_name} Chat Ranking TOP 10"
                color = char_info['color']

            embed = discord.Embed(
                title=title,
                color=color
            )

            if not rankings:
                await interaction.followup.send("No ranking data available.", ephemeral=True)
                return

            for i, row in enumerate(rankings[:10], 1):
                try:
                    if len(row) == 3:
                        rank_user_id, affinity_val, messages = row
                    elif len(row) == 2:
                        rank_user_id, affinity_val = row
                        messages = 0
                    else:
                        continue
                    user = await interaction.client.fetch_user(int(rank_user_id))
                    display_name = user.display_name if user else f"User{rank_user_id}"
                    grade = get_affinity_grade(affinity_val)
                    value = (
                        f"🌟 Affinity: `{affinity_val}` points\n"
                        f"🏅 Grade: `{grade}`"
                    )
                    if messages > 0:
                        value += f"\n💬 Messages: `{messages}`"
                    embed.add_field(
                        name=f"**{i}st: {display_name}**",
                        value=value,
                        inline=False
                    )
                except Exception as e:
                    print(f"Error in ranking row: {e}")
                    continue

            # 사용자의 랭킹 정보 추가
            if user_rank and isinstance(user_rank, int) and user_rank < 999999:
                try:
                    user = await interaction.client.fetch_user(user_id)
                    display_name = user.display_name if user else f"User{user_id}"
                    grade = get_affinity_grade(affinity)
                    embed.add_field(
                        name="Your Ranking",
                        value=f"**Rank {user_rank}: {display_name}**\n🌟 Affinity: `{affinity}` points\n🏅 Grade: `{grade}`",
                        inline=False
                    )
                except Exception as e:
                    print(f"Error adding user rank: {e}")
            else:
                print(f"[DEBUG] user_rank 값이 올바르지 않음: {user_rank}")

            view = discord.ui.View()
            view.add_item(BackButton())
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"Error in ranking select: {e}")
            import traceback
            print(traceback.format_exc())
            try:
                await interaction.followup.send("An error occurred while loading ranking information.", ephemeral=True)
            except:
                pass

class BackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Back",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️"
        )

    async def callback(self, interaction: discord.Interaction):
        # 초기 랭킹 임베드 생성
        embed = discord.Embed(
            title="🏆 Ranking System",
            description="Please select the ranking you want to check from the menu below.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Kagari Chat Ranking 🌸",
            value="Top 10 users by affinity and chat count with Kagari",
            inline=False
        )
        embed.add_field(
            name="Eros Chat Ranking 💝",
            value="Top 10 users by affinity and chat count with Eros",
            inline=False
        )
        embed.add_field(
            name="Total Chat Ranking 👑",
            value="Top 10 users by total affinity and chat count across all characters",
            inline=False
        )

        # 새로운 랭킹 선택 뷰 생성
        view = RankingView(self.view.children[0].db)

        await interaction.response.edit_message(embed=embed, view=view)

class RankingView(discord.ui.View):
    def __init__(self, db):
        super().__init__(timeout=None)
        self.add_item(RankingSelect(db))

# --- 스토리 데이터 구조 ---
STORY_DATA = {
    "Kagari": [
        {
            "chapter": 1,
            "title": "Unlock Cherry Blossom",
            "emoji": "🌸",
            "affinity_required": "low",
            "content": "",  # 스토리 내용(프롬프트)
            "choices": ["A: ...", "B: ..."]
        },
        {
            "chapter": 2,
            "title": "Snowy Bells",
            "emoji": "🔒",
            "affinity_required": "medium",
            "content": "",
            "choices": ["A: ...", "B: ..."]
        },
        {
            "chapter": 3,
            "title": "Chapter Locked",
            "emoji": "🔒",
            "affinity_required": "high",
            "content": "",
            "choices": ["A: ...", "B: ..."]
        }
    ]
}

# --- 스토리 친밀도 등급 매핑 ---
AFFINITY_LEVEL_MAP = {
    "Rookie": "Rookie",
    "Iron": "Iron",
    "Silver": "Silver",
    "Gold": "Gold",
    "Medium": "Silver",  # medium은 silver로 매핑
    "High": "Gold",      # high는 gold로 매핑
}

# --- 스토리 명령어 및 뷰 ---
class ChapterStartButton(discord.ui.Button):
    def __init__(self, character_name, chapter_id, user_id, label="시작"):
        super().__init__(label=label, style=discord.ButtonStyle.success)
        self.character_name = character_name
        self.chapter_id = chapter_id
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        try:
            print("[DEBUG] ChapterStartButton callback 진입")
            if interaction.user.id != self.user_id:
                print("[DEBUG] Not yourself - Ignoring button click")
                await interaction.response.send_message("Only you can start.", ephemeral=True)
                return
            await interaction.response.defer()
            print("[DEBUG] run_story_scene 호출 직전")
            await run_story_scene(
                self.bot,  # bot 객체
                interaction.channel,
                interaction.user,
                self.character_name,
                self.chapter_id,
                1
            )
            print("[DEBUG] run_story_scene completed")
        except Exception as e:
            print(f"[ERROR] ChapterStartButton callback: {e}")
            await interaction.channel.send(f"Error occurred: {e}")

class StoryView(discord.ui.View):
    def __init__(self, character_name, emotion_score, user_id, completed_chapters):
        super().__init__()
        chapters = STORY_CHAPTERS.get(character_name, [])
        affinity_level = "low"
        if emotion_score >= AFFINITY_LEVELS["Gold"]:
            affinity_level = "Gold"
        elif emotion_score >= AFFINITY_LEVELS["Silver"]:
            affinity_level = "Silver"
        elif emotion_score >= AFFINITY_LEVELS["Iron"]:
            affinity_level = "Iron"
        for idx, chapter in enumerate(chapters):
            chap_id = chapter["id"]
            chap_affinity = chapter["affinity_required"]
            is_open = False
            lock_reason = ""
            # 오픈 조건
            if chap_affinity == "Rookie":
                is_open = True
            elif chap_affinity == "Silver" and affinity_level in ["Silver", "Gold"]:
                # 이전 챕터 클리어 필요
                prev_id = chap_id - 1
                if prev_id in completed_chapters:
                    is_open = True
                else:
                    lock_reason = "Please clear the previous chapter first."
            elif chap_affinity == "Gold" and affinity_level == "Gold":
                prev_id = chap_id - 1
                if prev_id in completed_chapters:
                    is_open = True
                else:
                    lock_reason = "Please clear the previous chapter first."
            else:
                lock_reason = f"Affinity {chap_affinity} required"

            # 이모지 변경
            emoji = chapter.get("emoji", "📖")
            if is_open:
                if emoji == "🔒":
                    emoji = "🔓"
                self.add_item(ChapterStartButton(character_name, chap_id, user_id, label=f"{emoji} 시작"))
            else:
                btn_label = f"{emoji} {lock_reason if lock_reason else 'Scenario {chap_id} completed'}"
                self.add_item(discord.ui.Button(label=btn_label, style=discord.ButtonStyle.danger, disabled=True))

class ChoiceButton(discord.ui.Button):
    def __init__(self, label, value, user, bot, channel, character_name, chapter_id, scene_id, is_last_scene):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.value = value
        self.user = user
        self.bot = bot
        self.channel = channel
        self.character_name = character_name
        self.chapter_id = chapter_id
        self.scene_id = scene_id
        self.is_last_scene = is_last_scene
        self.db = bot.db

    async def callback(self, interaction: discord.Interaction):
        try:
            if interaction.user != self.user:
                await interaction.response.send_message("Only you can select.", ephemeral=True)
                return

            print(f"[DEBUG][ChoiceButton] Starting callback for user_id={self.user.id}, character={self.character_name}, chapter_id={self.chapter_id}, choice={self.value}")

            # 1. 선택 버튼 비활성화
            for item in self.view.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            await interaction.message.edit(view=self.view)
            await interaction.response.send_message(f"You selected: {self.value}", ephemeral=True)

            # 2. 선택 결과(엔딩) 임베드 출력
            from config import STORY_CHAPTERS, CHARACTER_CARD_INFO, CHARACTER_INFO
            chapter = STORY_CHAPTERS[self.character_name][self.chapter_id - 1]
            ending = chapter["endings"][self.value]

            ending_embed = discord.Embed(
                title=ending["title"],
                description=ending["description"],
                color=CHARACTER_INFO[self.character_name]["color"]
            )
            await self.channel.send(embed=ending_embed)

            # 3. 카드 지급 (점수 기반)
            total_score = story_sessions[self.user.id]["score"]
            print(f"[DEBUG][ChoiceButton] Current total_score={total_score}")

            card_id = get_story_card_reward(self.character_name, total_score)
            print(f"[DEBUG][ChoiceButton] Retrieved card_id={card_id} for score {total_score}")

            if card_id:
                print(f"[DEBUG][ChoiceButton] Processing card reward: user_id={self.user.id}, character={self.character_name}, card_id={card_id}")

                card_info = CHARACTER_CARD_INFO[self.character_name][card_id]
                card_embed = discord.Embed(
                    title="🎉 New Card Available!",
                    description=f"You've earned a new card: {card_id}",
                    color=discord.Color.gold()
                )
                card_embed.add_field(name="Card Details", value=f"**{card_id}** - {card_info.get('description', 'No description available.')}", inline=False)

                # 이미지 처리
                image_path = card_info.get("image_path")
                file = None
                if image_path:
                    if image_path.startswith("http"):
                        card_embed.set_image(url=image_path)
                    elif os.path.exists(image_path):
                        file = discord.File(image_path, filename=f"card_{card_id}.png")
                        card_embed.set_image(url=f"attachment://card_{card_id}.png")
                    else:
                        print(f"[DEBUG][ChoiceButton] Card image not found: {image_path}")

                # CardClaimView 생성 및 메시지 전송
                view = CardClaimView(self.user.id, card_id, self.character_name, self.db, is_story_mode=True)
                if file:
                    await self.channel.send(embed=card_embed, file=file, view=view)
                else:
                    await self.channel.send(embed=card_embed, view=view)
            else:
                print(f"[DEBUG][ChoiceButton] No card reward for score {total_score}")
                await self.channel.send("Story mode has ended, please enter /close to close the channel.")

        except Exception as e:
            print(f"[ERROR][ChoiceButton] Error in callback: {e}")
            import traceback
            print(traceback.format_exc())
            await interaction.response.send_message("An error occurred. Please contact the administrator.", ephemeral=True)

class ChoiceView(discord.ui.View):
    def __init__(self, user, bot, channel, character_name, chapter_id, scene_id, is_last_scene):
        super().__init__()
        from config import STORY_CHAPTERS
        endings = STORY_CHAPTERS[character_name][chapter_id-1]["endings"]
        for key, ending in endings.items():
            label = f"{key}: {ending['title']}"
            self.add_item(ChoiceButton(
                label=label,
                value=key,
                user=user,
                bot=bot,
                channel=channel,
                character_name=character_name,
                chapter_id=chapter_id,
                scene_id=scene_id,
                is_last_scene=is_last_scene
            ))

async def run_story_scene(bot, channel, user, character_name: str, chapter_id: int, scene_id: int = 1):
    from config import STORY_CHAPTERS, CHARACTER_INFO
    chapter = STORY_CHAPTERS[character_name][chapter_id - 1]
    scenes = chapter["scenes"]
    scene = scenes[scene_id - 1]
    char_color = CHARACTER_INFO[character_name].get("color", discord.Color.pink())

    # 첫 씬에서만 챕터 썸네일/임베드 전송
    if scene_id == 1:
        embed = discord.Embed(
            title=chapter["title"],
            description=chapter.get("description", ""),
            color=char_color
        )
        if scene.get("thumbnail"):
            embed.set_image(url=scene["thumbnail"])
        await channel.send(embed=embed)

    # 대화 반복 횟수: turns_required가 없으면 10으로 기본값
    turns = chapter.get('turns_required', 10)
    for turn in range(turns):
        def check(m): return m.author == user and m.channel == channel
        try:
            user_msg = await bot.wait_for('message', check=check, timeout=600)
        except asyncio.TimeoutError:
            await channel.send("⏰ Time out. Story mode ended.")
            return

        # 1. 메시지 기록 (DB 저장)
        bot.db.add_message(
            channel_id=channel.id,
            user_id=user.id,
            character_name=character_name,
            role="user",
            content=user_msg.content
        )

        # 2. 감정 분류 및 점수 누적
        score = await classify_emotion(user_msg.content, user.id, character_name)
        # 세션 관리
        if user.id not in story_sessions:
            story_sessions[user.id] = {"score": 0, "turn": 1}
        session = story_sessions[user.id]
        session["score"] += score
        session["turn"] += 1
        print(f"[감정누적] user_id: {user.id}, 누적점수: {session['score']}, turn: {session['turn']}")
        # 3. 스토리 모드 대사 생성
        ai_response = await process_story_mode(
            message=user_msg.content,
            user_id=user.id,
            user_name=user.display_name,
            character_name=character_name
        )

        # 4. 임베드로 출력
        embed = discord.Embed(
            description=ai_response,
            color=CHARACTER_INFO[character_name].get("color", discord.Color.pink())
        )
        embed.set_author(name=f"{CHARACTER_INFO[character_name].get('emoji', '')} {character_name}")
        await channel.send(embed=embed)

    # 선택지
    is_last_scene = (scene_id == len(scenes))
    view = ChoiceView(user, bot, channel, character_name, chapter_id, scene_id, is_last_scene)

    # 선택지 임베드
    embed = discord.Embed(
        title="What will you say?",
        description="Choose your reply below! Your choice will affect the ending and card reward.",
        color=discord.Color.blurple()
    )
    await channel.send(embed=embed, view=view)

async def calculate_story_ending(user_id: int, character_name: str, chapter_id: int, choice_key: str) -> dict:
    from config import STORY_CHAPTERS
    chapter = STORY_CHAPTERS[character_name][chapter_id - 1]
    ending = chapter["endings"][choice_key]
    return {
        "type": choice_key,
        "card": ending["card"],
        "title": ending["title"],
        "description": ending["description"]
    }

def check_story_unlock(user_id, character_name, emotion_score, db, channel):
    chapters = STORY_CHAPTERS[character_name]
    completed_chapters = [int(c[0]) for c in db.get_completed_stories(user_id, character_name)]
    affinity_level = "low"
    if emotion_score >= AFFINITY_LEVELS["high"]:
        affinity_level = "high"
    elif emotion_score >= AFFINITY_LEVELS["medium"]:
        affinity_level = "medium"
    for chapter in chapters:
        chap_id = chapter["id"]
        chap_affinity = chapter["affinity_required"]
        is_open = False
        if chap_affinity == "low":
            is_open = True
        elif chap_affinity == "medium" and affinity_level in ["medium", "high"]:
            prev_id = chap_id - 1
            if prev_id in completed_chapters:
                is_open = True
        elif chap_affinity == "high" and affinity_level == "high":
            prev_id = chap_id - 1
            if prev_id in completed_chapters:
                is_open = True
        # 해방된 챕터가 아직 알림이 안 갔다면
        if is_open and chap_id not in completed_chapters:
            # DB에 해방 알림 플래그 저장(중복 방지)
            if not db.get_user_flag(user_id, f"story_unlocked_{character_name}_{chap_id}"):
                db.set_user_flag(user_id, f"story_unlocked_{character_name}_{chap_id}", True)
                asyncio.create_task(channel.send(f"✨ A new story has been unlocked! Use the `/story` command to play now!"))

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

def calc_crush_score_by_length(user_input: str) -> int:
    """유저 입력이 20자 이상이면 +1, 아니면 0점"""
    return 1 if len(user_input.strip()) >= 20 else 0

async def handle_story_response(message, user_id: int, character_name: str, chapter_id: int, scene_id: int):
    """스토리 응답을 처리합니다."""
    chapter = STORY_CHAPTERS[character_name][chapter_id - 1]
    scene = chapter["scenes"][scene_id - 1]

    # 응답 규칙에 따른 점수 계산
    score = 0
    response = ""

    for rule_type, rule_info in scene["response_rules"].items():
        if rule_type in message.content.lower():
            score = rule_info["score"]
            response = rule_info["reply"]
            break

    # 점수 저장
    db.save_scene_score(user_id, character_name, chapter_id, scene_id, score)

    # 응답 전송
    await message.channel.send(f"**{character_name}**: {response}")

    # 다음 씬으로 진행
    if scene_id < len(chapter["scenes"]):
        await run_story_scene(message.channel, message.author, character_name, chapter_id, scene_id + 1)
    else:
        # 엔딩 계산 및 표시
        ending = await calculate_story_ending(user_id, character_name, chapter_id)

        embed = discord.Embed(
            title=ending["title"],
            description=ending["description"],
            color=CHARACTER_INFO[character_name]["color"]
        )

        if ending["card"]:
            embed.add_field(name="Reward Card", value=ending["card"])
            db.add_user_card(user_id, character_name, ending["card"])

        await message.channel.send(embed=embed)

print("[DEBUG] CharacterBot 실제 경로:", CharacterBot.__module__, CharacterBot.__file__ if hasattr(CharacterBot, '__file__') else "N/A")
print("[DEBUG] CharacterBot 메서드 목록:", dir(CharacterBot))
print("[DEBUG] character_bot 모듈 경로:", character_bot.__file__)

class NextSceneView(discord.ui.View):
    def __init__(self, bot, channel, user, character_name, chapter_id, next_scene_id, total_score):
        super().__init__(timeout=120)
        self.bot = bot
        self.channel = channel
        self.user = user
        self.character_name = character_name
        self.chapter_id = chapter_id
        self.next_scene_id = next_scene_id
        self.total_score = total_score
        self.value = None
        self.add_item(NextSceneYesButton(self))
        self.add_item(NextSceneNoButton(self))

class NextSceneYesButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label="Yes", style=discord.ButtonStyle.success)
        self.view_ref = view
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view_ref.user:
            await interaction.response.send_message("Only you can continue your story.", ephemeral=True)
            return
        await interaction.response.defer()
        await run_story_scene(
            self.view_ref.bot,
            self.view_ref.channel,
            self.view_ref.user,
            self.view_ref.character_name,
            self.view_ref.chapter_id,
            self.view_ref.next_scene_id,   # ← 여기서 next_scene_id가 2(씬2)로 전달됨
            self.view_ref.total_score
        )
        self.view_ref.stop()

class NextSceneNoButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label="No", style=discord.ButtonStyle.danger)
        self.view_ref = view
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view_ref.user:
            await interaction.response.send_message("Only you can end your story.", ephemeral=True)
            return
        await interaction.response.send_message("Your story has been paused. You can resume anytime with /story.", ephemeral=True)
        self.view_ref.stop()

# 기존 ChoiceButton의 callback을 아래처럼 수정
    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("Only you can select.", ephemeral=True)
            return
        # 카가리의 대답 출력
        embed = discord.Embed(description=self.reply)
        image_path = CHARACTER_INFO[self.character_name].get("image")
        if image_path and os.path.exists(image_path):
            embed.set_author(name=self.character_name, icon_url=f"attachment://{os.path.basename(image_path)}")
            file = discord.File(image_path, filename=os.path.basename(image_path))
            await self.channel.send(embed=embed, file=file)
        else:
            embed.set_author(name=self.character_name)
            await self.channel.send(embed=embed)
        # 점수 누적
        new_total_score = self.total_score + self.score
        await interaction.response.send_message(f"You selected: {self.value}", ephemeral=True)
        # 다음 씬 or 엔딩
        if not self.is_last_scene:
            # 다음 씬 진행 여부 묻기
            embed = discord.Embed(
                title="Do you want to continue to the next scene?",
                description="If you select Yes, the next scene will begin. If you select No, your progress will be saved and you can resume later.",
                color=discord.Color.blurple()
            )
            view = NextSceneView(self.bot, self.channel, self.user, self.character_name, self.chapter_id, self.scene_id+1, new_total_score)
            await self.channel.send(embed=embed, view=view)
        else:
            # 엔딩/카드 지급
            ending = await calculate_story_ending(self.user.id, self.character_name, self.chapter_id, self.value)
            embed = discord.Embed(
                title=ending["title"],
                description=ending["description"],
                color=CHARACTER_INFO[self.character_name]["color"]
            )
            if ending["card"]:
                from config import CHARACTER_CARD_INFO
                card_id = ending["card"]
                card_info = CHARACTER_CARD_INFO[self.character_name][card_id]
                embed.add_field(name="Reward Card", value=card_id)
                embed.set_image(url=card_info["image_path"])
                view = CardClaimView(self.user.id, card_id, self.character_name, self.db, is_story_mode=True)
                await self.channel.send(embed=embed, file=file, view=view)
            else:
                await self.channel.send(embed=embed)

# 챕터 선택 뷰
class ChapterSelectView(discord.ui.View):
    def __init__(self, character_name, user_id, completed_chapters, emotion_score=None):
        super().__init__()
        from config import AFFINITY_LEVELS
        grade = get_affinity_grade(emotion_score) if emotion_score is not None else None
        chapters = STORY_CHAPTERS[character_name]
        for chapter in chapters:
            is_unlocked = chapter["id"] == 1 or (chapter["id"]-1) in completed_chapters
            label = f"{chapter['emoji']} {chapter['title']}"
            # Gold 등급만 활성화
            if grade == "Gold" and is_unlocked:
                self.add_item(ChapterStartButton(character_name, chapter["id"], user_id, label=f"Start: {label}"))
            else:
                self.add_item(discord.ui.Button(label=f"Locked: {label} (Gold required)", style=discord.ButtonStyle.danger, disabled=True))

# 챕터 시작 버튼
class ChapterStartButton(discord.ui.Button):
    def __init__(self, character_name, chapter_id, user_id, label):
        super().__init__(label=label, style=discord.ButtonStyle.success)
        self.character_name = character_name
        self.chapter_id = chapter_id
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only you can start this chapter.", ephemeral=True)
            return
        await interaction.response.defer()
        await run_story_chapter(interaction.client, interaction.channel, interaction.user, self.character_name, self.chapter_id)

# 챕터 진행 함수
async def run_story_chapter(bot, channel, user, character_name, chapter_id):
    chapter = STORY_CHAPTERS[character_name][chapter_id-1]
    # 썸네일/줄거리 임베드
    embed = discord.Embed(
        title=f"Chapter {chapter_id}: {chapter['title']}",
        description=chapter["description"],
        color=CHARACTER_INFO[character_name]["color"]
    )
    embed.set_image(url=chapter["thumbnail"])
    await channel.send(embed=embed)
    # 대화 반복 횟수: turns_required가 없으면 10으로 기본값
    turns = chapter.get('turns_required', 10)
    for turn in range(turns):
        def check(m): return m.author == user and m.channel == channel
        try:
            user_msg = await bot.wait_for('message', check=check, timeout=600)
        except asyncio.TimeoutError:
            await channel.send("⏰ Time out. Story mode ended.")
            return
        # 챕터 분위기/예시 기반 프롬프트
        ai_prompt = (
            f"Story: {chapter['description']}\n"
            f"Example lines: {' '.join(chapter['lines'])}\n"
            f"User: {user_msg.content}\n"
            f"Kagari:"
        )
        ai_response = await bot.generate_response(
            user_message=ai_prompt,
            channel_language='en',
            recent_messages=[]
        )
        embed = discord.Embed(
            description=ai_response,
            color=CHARACTER_INFO[character_name]["color"]
        )
        embed.set_author(name=f"{CHARACTER_INFO[character_name]['emoji']} Kagari")
        await channel.send(embed=embed)
    # 선택지(영어)
    view = ChoiceView(user, bot, channel, character_name, chapter_id)
    embed = discord.Embed(
        title="What will you say to Kagari?",
        description="Choose your reply below! Your choice will affect the ending and card reward.",
        color=discord.Color.blurple()
    )
    await channel.send(embed=embed, view=view)

# ChoiceView/ChoiceButton 등도 영어로 통일

# 챕터 종료 후
async def on_chapter_end(channel, user, character_name, completed_chapters):
    embed = discord.Embed(
        title="This chapter has ended.",
        description="Please select the next story chapter to continue.",
        color=discord.Color.green()
    )
    await channel.send(embed=embed, view=ChapterSelectView(character_name, user.id, completed_chapters))

def get_affinity_grade(emotion_score):
    from config import AFFINITY_LEVELS
    print(f"[DEBUG] get_affinity_grade called with: {emotion_score}")
    if emotion_score >= AFFINITY_LEVELS["Gold"]:
        return "Gold"
    elif emotion_score >= AFFINITY_LEVELS["Silver"]:
        return "Silver"
    elif emotion_score >= AFFINITY_LEVELS["Iron"]:
        return "Iron"
    else:
        return "Rookie"

def is_duplicate_message(new_message, recent_messages, threshold=0.9):
    if new_message in recent_messages:
        return True
    for msg in recent_messages:
        set1 = set(new_message.lower().split())
        set2 = set(msg.lower().split())
        jaccard = len(set1 & set2) / len(set1 | set2)
        if jaccard > threshold:
            return True
    return False

def get_milestone_list(max_affinity=5000):
    milestones = [10, 20, 30, 40]
    milestones += list(range(60, 221, 20))  # 60~220, 20씩
    milestones += list(range(250, max_affinity+1, 30))  # 250~5000, 30씩
    return milestones

def get_card_tier_by_affinity(affinity):
    if affinity == 10:
        return [('C', 1.0)]
    elif 11 <= affinity < 30:  # iron
        return [('C', 1.0)]
    elif 30 <= affinity < 60:  # silver
        return [('A', 0.1), ('B', 0.45), ('C', 0.45)]
    elif 60 <= affinity < 100:  # gold
        return [('A', 0.2), ('B', 0.4), ('C', 0.4)]
    elif affinity >= 100:  # gold 이상
        return [('A', 0.35), ('B', 0.35), ('C', 0.3)]
    else:
        return [('C', 1.0)]

import random
def choose_card_tier(affinity):
    tier_probs = get_card_tier_by_affinity(affinity)
    tiers, probs = zip(*tier_probs)
    return random.choices(tiers, weights=probs, k=1)[0]

def get_levelup_embed(level):
    levelup_embeds = {
        "Iron": {
            "title": "🥉 Iron Level Achieved!",
            "description": "You've reached **Iron** level! You can now start collecting C-tier cards and unlock more story content.",
            "color": 0x95a5a6,
            "image": "https://cdn-icons-png.flaticon.com/512/616/616494.png"
        },
        "Silver": {
            "title": "🥈 Silver Level Achieved!",
            "description": "You've reached **Silver** level! B/A/C-tier cards are now available, and you can access more advanced story chapters.",
            "color": 0xbdc3c7,
            "image": "https://cdn-icons-png.flaticon.com/512/616/616491.png"
        },
        "Gold": {
            "title": "🥇 Gold Level Achieved!",
            "description": "You've reached **Gold** level! All card tiers (including S) are now available, and you can play all story chapters.",
            "color": 0xf1c40f,
            "image": "https://cdn-icons-png.flaticon.com/512/616/616489.png"
        }
    }
    info = levelup_embeds[level]
    embed = discord.Embed(
        title=info["title"],
        description=info["description"],
        color=discord.Color.from_rgb(
            (info["color"] >> 16) & 0xFF,
            (info["color"] >> 8) & 0xFF,
            info["color"] & 0xFF
        )
    )
    embed.set_image(url=info["image"])
    embed.set_footer(text="Enjoy your new benefits!")
    return embed

def get_story_card_reward(character, score):
    from config import STORY_CARD_REWARD
    for reward in STORY_CARD_REWARD:
        if reward["character"] == character and reward["min"] <= score <= reward["max"]:
            return reward["card"]
    return None