import discord
from discord.ext import commands
import os
from typing import Optional, Dict
import asyncio
import random
import psycopg2
from datetime import datetime

from bot_selector import LanguageSelectView
from database_manager import DATABASE_URL, DatabaseManager

class CharacterBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        
        # Character images
        self.character_images = {
            "kagari": os.path.join("assets", "kagari.png"),
            "eros": os.path.join("assets", "eros.png"),
            "elysia": os.path.join("assets", "elysia.png")
        }
        
        self.db = DatabaseManager()  # 인스턴스 준비
        
    async def setup_hook(self):
        """Initial setup after the bot is ready"""
        await self.tree.sync()
        
    @commands.command()
    async def character(self, ctx, name: str):
        """Show character information with image"""
        name = name.lower()
        if name in self.character_images:
            file = discord.File(self.character_images[name])
            embed = discord.Embed(title=f"{name.capitalize()} 캐릭터", color=discord.Color.blue())
            embed.set_image(url=f"attachment://{os.path.basename(self.character_images[name])}")
            await ctx.send(file=file, embed=embed)
        else:
            await ctx.send("해당 캐릭터를 찾을 수 없습니다.")

    def set_user_language(self, user_id: int, character_name: str, language: str) -> bool:
        """사용자의 특정 캐릭터와의 대화 언어를 설정합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE conversations
                    SET language = %s
                    WHERE user_id = %s AND character_name = %s
                ''', (language, user_id, character_name))
                cursor.execute('''
                    INSERT INTO user_context (user_id, character_name, last_language, last_interaction)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id, character_name) DO UPDATE SET last_language = EXCLUDED.last_language, last_interaction = EXCLUDED.last_interaction
                ''', (user_id, character_name, language))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error setting user language: {e}")
            return False 

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_char = self.values[0]

            # 새로운 채널 생성
            category = discord.utils.get(interaction.guild.categories, name="chatbot")
            if not category:
                try:
                    category = await interaction.guild.create_category("chatbot")
                except Exception as e:
                    print(f"Category creation error: {e}")
                    await interaction.response.send_message(
                        "Please check the bot's permissions..",
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
                channel = await interaction.guild.create_text_channel(
                    name=channel_name,
                    category=category,
                    overwrites=overwrites
                )

                # 채널 생성 성공 메시지 전송
                await interaction.response.send_message(
                    f"{channel.mention}에서 {selected_char}와(과) 대화를 시작하세요!",
                    ephemeral=True
                )

                # 언어 선택 임베드 생성
                embed = discord.Embed(
                    title="🌍 언어 선택 / Language Selection",
                    description="Spot zero 캐릭터와 어떤 언어로 대화하시겠습니까?\nWhich language would you like to chat in?",
                    color=discord.Color.blue()
                )

                embed.add_field(
                    name="사용 가능한 언어 / Available Languages",
                    value="🇰🇷 한국어 (Korean)\n🇺🇸 English\n🇯🇵 日本語 (Japanese)\n🇨🇳 中文 (Chinese)",
                    inline=False
                )

                embed.set_footer(text="원하시는 언어를 선택해주세요 / Please select your preferred language")

                # 선택된 캐릭터 봇에 채널 추가
                selected_bot = self.bot_selector.character_bots.get(selected_char)
                if selected_bot:
                    try:
                        success, message = await selected_bot.add_channel(channel.id, interaction.user.id)

                        if success:
                            await interaction.response.send_message(
                                f"{channel.mention}에서 {selected_char}와(과) 대화를 시작하세요!",
                                ephemeral=True
                            )

                            # 언어 선택 임베드 생성 및 전송
                            embed = discord.Embed(
                                title="🌍 언어 선택 / Language Selection",
                                description="Spot zero 캐릭터와 어떤 언어로 대화하시겠습니까?\nWhich language would you like to chat in?",
                                color=discord.Color.blue()
                            )

                            embed.add_field(
                                name="사용 가능한 언어 / Available Languages",
                                value="🇰🇷 한국어 (Korean)\n🇺🇸 English\n🇯🇵 日本語 (Japanese)\n🇨🇳 中文 (Chinese)",
                                inline=False
                            )

                            embed.set_footer(text="원하시는 언어를 선택해주세요 / Please select your preferred language")

                            # DatabaseManager 인스턴스 확인
                            if not hasattr(selected_bot, 'db'):
                                selected_bot.db = DatabaseManager()  # DatabaseManager 인스턴스 생성

                            # 언어 선택 뷰 생성 및 전송
                            view = LanguageSelectView(selected_bot.db, interaction.user.id, selected_char, timeout=None)
                            await channel.send(embed=embed, view=view)

                    except Exception as e:
                        print(f"Error in channel creation: {e}")
                        await interaction.followup.send(
                            "채널 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
                            ephemeral=True
                        )

            except Exception as e:
                print(f"Error in channel creation: {e}")
                await interaction.followup.send(
                    "채널 생성 중 오류가 발생했습니다. 다시 시도해주세요.",
                    ephemeral=True
                )

        except Exception as e:
            print(f"CharacterSelect error: {e}")
            await interaction.response.send_message(
                "오류가 발생했습니다. 다시 시도해주세요.",
                ephemeral=True
            ) 

    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = message.author.id
        channel_id = message.channel.id
        character_name = "kagari"  # 실제 캐릭터명 추출 로직 필요
        language = "ko"  # 실제 언어 추출 로직 필요

        # 1. 대화(conversations) 기록
        self.db.add_message(channel_id, user_id, character_name, "user", message.content, language)

        # 2. 감정 분석 (예시)
        score_change = 1  # 실제 감정 분석 함수로 대체
        await self.db.update_affinity(user_id, character_name, message.content, str(datetime.now()), score_change)

        # 3. 감정 로그 기록
        self.db.log_emotion_score(user_id, character_name, score_change, message.content)

        # 4. 대화 카운트/마일스톤 업데이트 (선택)
        milestone = 10  # 예시, 실제 마일스톤 로직 필요
        await self.db.update_last_milestone(user_id, milestone)

        # ... 나머지 응답 처리 ... 