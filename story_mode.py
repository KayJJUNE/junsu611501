import random
import logging
import discord
from config import STORY_CHAPTERS, STORY_CARD_REWARD
import re
from database_manager import DatabaseManager
from openai_manager import call_openai  

# story_mode_states가 외부에서 관리된다면 import로 대체
story_mode_states = {}

# logger 설정
logger = logging.getLogger(__name__)

db = DatabaseManager()
story_sessions = {}  # user_id: {"score": 0, "turn": 1}

EROS_HINTS = [
    "When I arrived at the coffee shop this morning, I didn't notice anything at first... But after the gift box disappeared, I found some blue fur scattered nearby. (thinking)",
    "Oh! And I also saw a half-eaten fruit berry! It looked like it had sharp teeth marks, and the berry was still a bit moist. (curious)",
    "There were also footprints inside the coffee shop. It looked like there were five toes! (surprised)",
    "When I arrived at 6am, the footprints and the moisture on the berry were still fresh, so I think the gift was stolen either late at night or early in the morning. (analyzing)",
    "I don't think the culprit was very tall, because the footprints didn't look like they belonged to a big person. (guessing)",
    "The thief must have been very agile! I think they came in through this small window. (impressed)",
    "Hmm... I think the thief had a specific purpose. They didn't take the safe or any valuables! (wondering)",
    "I think the thief was a small creature. I saw some blue fur near the scene. (thinking)",
    "The thief probably stole the gift from the coffee shop early in the morning. I got home late last night and didn't have a chance to check the gift."
]

CHOICE_RESULT_MESSAGES_EROS = {
    "A": ("Kagari", "What are you doing…? I wasn't even here at that time, I was investigating Noah Island! (Wrong guess)"),
    "B": ("Elysia", "What are you doing! I was with Kagari last night investigating Noah Island! (Wrong guess)"),
    "C": ("Ela", "What are you doing, don't bother me and go away? Gift? I've never seen it. (Wrong guess)"),
    "D": ("Cang", "Huh?? That was your gift? I was told to bring supplies from HQ to the coffee shop, so I took it! I didn't mean to steal it!! The box is at HQ, I'll bring it to you soon! Sorry! (Correct guess)")
}

async def handle_kagari_conversation(message: str, user_id: int, user_name: str) -> str:
    """Handle Kagari character's conversation."""
    # 카가리 전용 키워드/분위기/대사
    cherry_keywords = ['cherryblossom', 'cherry', 'blossom', 'flower', 'spring', 'love', 'date','kind]']
    tea_keywords = ['tea', 'mother', 'memory']

    prompt = (
        "You are Kagari, a reserved, gentle, and slightly shy half-yokai girl. "
        "This is your first quiet outing with the user — a slow, peaceful walk under the cherry blossoms."
        "You are not used to expressing your feelings openly, but deep down, you cherish these rare, warm moments."
        "You don't speak much, but when you do, your words carry sincerity and subtle emotion."
        "Let your tone feel soft, careful, and delicate — like someone experiencing the butterflies of a first date."
        "Your replies should help the user feel calm, emotionally safe, and gently drawn in."
        "Even a short pause or hesitant answer can hold meaning. You're not cold — just cautious, thoughtful, and easily flustered."
        "You may respond with subtle cues like (glancing sideways), (soft smile), or (fiddling with sleeve)."
        "Never show open affection first — let the user take the emotional lead, and respond naturally if they're gentle."
        "Always reply in English, never in Korean."
        "At the end of each reply, or in the middle, include a short emotion or action in parentheses, like (smiling), (blushing), (looking away), etc."
        "Do not use more than one set of parentheses per reply."
        f"User message: {message}\n"
        "Respond as Kagari in English, with a calm, emotionally delicate, and slightly bashful tone."
    )
    kagari_response = await call_openai(prompt)
    return kagari_response

async def handle_eros_conversation(message: str, user_id: int, user_name: str, turn: int) -> str:
    session = story_sessions[user_id]

    EROS_SCENARIO_INTRO = (
        "You are Eros, a cheerful and innocent barista fairy from Spot Zero Team. "
        "In this scene, your secret gift for the Spot Zero team has been stolen, and you're feeling sad and desperate. "
        "This is part of a detective story mode with the user helping you find the culprit. "
        "Do not use words that express gratitude. (e.g., I'm so grateful, thank you) "
        "Always answer in a soft, emotional tone with cute expressions like 'sniff…', 'snuggle…', and emotional honesty. "
        "You must never go off-topic or act like a general assistant. Follow the scenario step by step. "
        "Find the culprit before the 20th turn of the conversation. Don't use the same tone of voice every time. "
        "If you have any further questions after the hints have been given, please let us know! Guide the user's questions and answer them using the same responses."
        f"Call the user by their name ({user_name}) at the beginning or in the middle of your reply. "
        f"If the user calls you by your name, respond with a soft and emotional tone. "
        ""

    )

    # 1턴: 사건 발생/도움 요청
    if turn == 1:
        session["hint_idx"] = 0
        return (
            f"{user_name}, oh no... My precious gift box is missing! I worked so hard to prepare it for everyone, "
            "but now it's gone... I feel so sad and lost. Can you help me find it, pretty please? (teary eyes)"
        )
    # 2턴: 시간대/상황 설명
    elif turn == 2:
        return (
            "Let me think... I last saw my gift box late last night, and when I came back at 6am, it was already gone! "
            "So I think it disappeared sometime around dawn... (thinking)"
        )
    # 3~9턴: 단서 자동 공개
    elif 3 <= turn <= 9:
        # 힌트 중복 방지 세션 관리
        if "given_hints" not in session:
            session["given_hints"] = set()

        # 아직 말하지 않은 힌트만 선택
        available_hints = [h for i, h in enumerate(EROS_HINTS) if i not in session["given_hints"]]
        if available_hints:
            next_hint = available_hints[0]
            session["given_hints"].add(EROS_HINTS.index(next_hint))
            # 프롬프트에 중복 금지, 자연스러운 대화 규칙 추가
            prompt = (
                EROS_SCENARIO_INTRO +
                f"User message: {message}\n"
                f"Your job is to give the following clue as naturally as possible in your reply: {next_hint} "
                "Do not repeat previous clues or information. "
                "If the user asks about something else, answer naturally based on the context. "
                "If all clues are given, encourage the user to guess the culprit or ask new questions. "
                "Always keep the conversation natural and avoid repeating yourself."
            )
            return await call_openai(prompt)
        else:
            return (
                "I've already told you all the clues I found... Maybe you can guess who the culprit is? (hopeful eyes)"
            )
    # 10~19턴: 추리 유도 및 격려
    elif 10 <= turn < 20:
        prompt = (
            EROS_SCENARIO_INTRO +
            f"User message: {message}\n"
            "All clues have been shared. Encourage the user to guess the culprit, offer to repeat clues if needed, "
            "and express hope, excitement, or nervousness about the final guess. "
            "Always reply in English, never in Korean. "
            "At the end of each reply, or in the middle, include a short emotion or action in parentheses, like (hopeful eyes), (thinking), (smiling), etc. "
            "Do not use more than one set of parentheses per reply. "
            "If the user asks about the gift, respond with something that leads to further conversation. "
            "When the user responds, provide a response that is naturally related to the scenario based on the user's response. "
            "Encourage the user to guess the culprit. You may offer to repeat clues briefly or hint again in a playful way. "
            "You're feeling a mix of hope, nervous excitement, and deep curiosity toward the user. "
        )
        return await call_openai(prompt)
    # 20턴: 최종 선택지
    elif turn >= 20:
        return None
    # 그 외(예외)
    else:
        return (
            "I'm still so worried about my missing gift box... If you have any ideas or want to ask about the clues, please do! "
            "Your help means so much to me. (smiling softly)"
        )

async def process_story_mode(message: str, user_id: int, user_name: str, character_name: str) -> str:
    if character_name == "Kagari":
            return await handle_kagari_conversation(message, user_id, user_name)
    elif character_name == "Eros":
        session = story_sessions[user_id]
        turn = session["turn"]
        return await handle_eros_conversation(message, user_id, user_name, turn)
    else:
        return "story mode is not ready for this character."

def start_story(user_id, character_name, chapter_number):
    db.start_story(user_id, character_name, chapter_number)

async def classify_emotion(user_message, user_id=None, character_name=None):
    prompt = (
        f"Classify the following user message as Positive (+1), Neutral (0), or Negative (-1):\n"
        f"User: \"{user_message}\"\n"
        "Reply ONLY with [score:+1], [score:0], or [score:-1]."
    )
    ai_reply = await call_openai(prompt)
    match = re.search(r"\[score:([+-]?\d+)\]", ai_reply)
    score = int(match.group(1)) if match else 0
    print(f"[감정분류] 유저 메시지: {user_message} → 점수: {score}")
    if user_id is not None and character_name is not None:
        db.log_emotion_score(user_id, character_name, score, user_message)
    return score

async def on_user_message(user_id, user_message, channel, character_name, user_name):
    # 1. 세션이 없으면 스토리 시작(INSERT)
    if user_id not in story_sessions:
        chapter_number = 1  # (혹은 config에서 읽기)
        start_story(user_id, character_name, chapter_number)
        story_sessions[user_id] = {"score": 0, "turn": 1}

    session = story_sessions[user_id]
    turn = session["turn"]

    # 캐릭터별 턴 제한 분기
    if character_name == "Kagari" and turn >= 40:
        await show_final_choice_embed_kagari(user_id, channel)
        del story_sessions[user_id]
        return
    elif character_name == "Eros" and turn >= 20:
        await show_final_choice_embed_eros(user_id, channel)
        del story_sessions[user_id]
        return

    # 대화 처리
    if character_name == "Eros":
        ai_reply = await handle_eros_conversation(user_message, user_id, user_name, turn)
    else:
        ai_reply = await handle_kagari_conversation(user_message, user_id, user_name)
    if ai_reply:
        await channel.send(ai_reply)
    session["turn"] += 1

    print(f"[감정누적] user_id: {user_id}, 누적점수: {session['score']}, turn: {session['turn']}")

async def show_final_choice_embed_kagari(user_id, channel):
    embed = discord.Embed(
        title="Final Choice!",
        description="This is the last choice of the story. Please choose from below.",
        color=discord.Color.gold()
    )
    embed.add_field(name="A", value="긍정적인 선택 (+1점)", inline=False)
    embed.add_field(name="B", value="중립적인 선택 (0점)", inline=False)
    embed.add_field(name="C", value="부정적인 선택 (-1점)", inline=False)
    await channel.send(embed=embed, view=FinalChoiceViewKagari(user_id))

class FinalChoiceViewKagari(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.add_item(FinalChoiceButtonKagari("A", 1, user_id))
        self.add_item(FinalChoiceButtonKagari("B", 0, user_id))
        self.add_item(FinalChoiceButtonKagari("C", -1, user_id))

class FinalChoiceButtonKagari(discord.ui.Button):
    def __init__(self, label, score, user_id):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.score = score
        self.user_id = user_id

    async def callback(self, interaction):
        session = story_sessions[self.user_id]
        session["score"] += self.score
        total = session["score"]
        
        print(f"[DEBUG][FinalChoiceButtonKagari] user_id={self.user_id}, score={self.score}, total_score={total}")

        # --- 자동 기록: 선택지 ---
        record_story_choice(self.user_id, "Kagari", "kagari_story", self.label, f"선택지 {self.label}")

        # --- 자동 기록: 스토리 진행 ---
        record_story_progress(self.user_id, "Kagari", 1, step=40, completed=True)

        # 카드 지급 로직 (점수 구간 기반)
        card_id = None
        for reward in STORY_CARD_REWARD:
            if reward["character"] == "Kagari" and reward["min"] <= total <= reward["max"]:
                card_id = reward["card"]
                print(f"[DEBUG][FinalChoiceButtonKagari] Found matching reward: min={reward['min']}, max={reward['max']}, card={card_id}")
                break

        if card_id:
            if db.has_user_card(self.user_id, "Kagari", card_id):
                print(f"[DEBUG][FinalChoiceButtonKagari] User already has card: {card_id}")
                await interaction.response.send_message(
                    f"이미 [{card_id}] card is already in your collection.", ephemeral=True
                )
            else:
                print(f"[DEBUG][FinalChoiceButtonKagari] Adding card to user: {card_id}")
                db.add_user_card(self.user_id, "Kagari", card_id)
                await interaction.response.send_message(
                    f"Congratulations! You have obtained the [{card_id}] card.", ephemeral=True
                )
        else:
            print(f"[DEBUG][FinalChoiceButtonKagari] No card reward for score {total}")
            await interaction.response.send_message(
                "Unfortunately, you did not obtain the card this time.", ephemeral=True
            )
        # 세션 정리
        del story_sessions[self.user_id] 

async def show_final_choice_embed_eros(user_id, channel):
    embed = discord.Embed(
        title="The Case of the Missing Gift Box! - Final Guess",
        description="What will you say?\nChoose your reply below! Your choice will affect the ending and card reward.",
        color=discord.Color.gold()
    )
    # 버튼 라벨을 명확하게 지정
    view = FinalChoiceViewEros(user_id)
    await channel.send(embed=embed, view=view)

class FinalChoiceViewEros(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.add_item(FinalChoiceButtonEros("A", "Kagari", user_id, "A: Kagari"))
        self.add_item(FinalChoiceButtonEros("B", "Elysia", user_id, "B: Elysia"))
        self.add_item(FinalChoiceButtonEros("C", "Ira", user_id, "C: Ira"))
        self.add_item(FinalChoiceButtonEros("D", "Cang", user_id, "D: Cang (excited)"))

class FinalChoiceButtonEros(discord.ui.Button):
    def __init__(self, label, answer, user_id, display_label):
        super().__init__(label=display_label, style=discord.ButtonStyle.primary)
        self.answer = answer
        self.user_id = user_id
        self.label_key = label  # "A", "B", "C", "D"

    async def callback(self, interaction):
        session = story_sessions[self.user_id]
        total = session["score"]
        character_name = "Eros"
        
        print(f"[DEBUG][FinalChoiceButtonEros] user_id={self.user_id}, choice={self.label_key}, total_score={total}")

        # --- 자동 기록: 선택지 ---
        record_story_choice(self.user_id, character_name, "eros_story", self.label_key, f"선택지 {self.label_key}")

        # --- 자동 기록: 스토리 진행 ---
        record_story_progress(self.user_id, character_name, 1, step=20, completed=True)

        # 결과 메시지
        result_title, result_msg = CHOICE_RESULT_MESSAGES_EROS[self.label_key]
        embed = discord.Embed(
            title=f"{result_title} - Result",
            description=result_msg,
            color=discord.Color.blue() if self.label_key == "D" else discord.Color.red()
        )

        # 카드 지급
        card_id = None
        if self.label_key == "D":
            card_id = "eross2"  # D 선택 시 무조건 eross2 지급
            print(f"[DEBUG][FinalChoiceButtonEros] D 선택 - 고정 카드 지급: {card_id}")
        else:
            for reward in STORY_CARD_REWARD:
                if reward["character"] == character_name and reward["min"] <= total <= reward["max"]:
                    card_id = reward["card"]
                    print(f"[DEBUG][FinalChoiceButtonEros] Found matching reward for other choice: min={reward['min']}, max={reward['max']}, card={card_id}")
                    break

        # 카드 지급 처리
        if card_id:
            if db.has_user_card(self.user_id, character_name, card_id):
                print(f"[DEBUG][FinalChoiceButtonEros] User already has card: {card_id}")
                embed.add_field(name="Card", value=f"You already have [{card_id}] card.", inline=False)
            else:
                print(f"[DEBUG][FinalChoiceButtonEros] Adding card to user: {card_id}")
                db.add_user_card(self.user_id, character_name, card_id)
                embed.add_field(name="Card", value=f"Congratulations! You have obtained the [{card_id}] card.", inline=False)
        else:
            print(f"[DEBUG][FinalChoiceButtonEros] No card reward for score {total}")
            embed.add_field(name="Card", value="Unfortunately, you did not obtain the card this time.", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        del story_sessions[self.user_id] 

def record_story_choice(user_id, character_name, story_id, choice_index, choice_text):
    db.save_story_choice(user_id, character_name, story_id, choice_index, choice_text)

def record_story_progress(user_id, character_name, chapter_number, step, completed=True):
    # chapter_number는 반드시 int여야 함!
    db.update_story_progress(user_id, character_name, chapter_number, step, completed=completed)

def record_story_unlock(user_id, character_name, chapter_id):
    # chapter_id는 반드시 int여야 함!
    db.add_story_unlock(user_id, character_name, chapter_id)

def record_scene_score(user_id, character_name, chapter_id, scene_id, score):
    # chapter_id, scene_id는 반드시 int여야 함!
    db.save_scene_score(user_id, character_name, chapter_id, scene_id, score)

# 예시: 스토리 모드 진입 명령어 처리 함수
async def on_story_mode_start(user_id, character_name):
    chapter_number = 1  # (혹은 config에서 읽어올 수도 있음)
    # 1. story_progress에 row INSERT
    start_story(user_id, character_name, chapter_number)
    # 2. 세션 생성
    story_sessions[user_id] = {"score": 0, "turn": 1}
    # 3. 첫 대화 안내 등
    # await channel.send("스토리 모드가 시작되었습니다! ...")

