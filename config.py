import os
from dotenv import load_dotenv
import discord

# 현재 파일의 절대 경로를 기준으로 BASE_DIR 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# .env 파일 로드
load_dotenv()

# Discord 봇 토큰들
SELECTOR_TOKEN = os.getenv('SELECTOR_TOKEN')
KAGARI_TOKEN = os.getenv('KAGARI_TOKEN')
EROS_TOKEN = os.getenv('EROS_TOKEN')
ELYSIA_TOKEN = os.getenv('ELYSIA_TOKEN')

# OpenAI API 키
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 친밀도 레벨 정의
AFFINITY_LEVELS = {
    "Rookie": 0,
    "Iron": 10,
    "Silver": 50,
    "Gold": 100
}

# 친밀도 레벨 임계값
AFFINITY_THRESHOLDS = [0, 10, 40, 50, 100]

# 지원되는 언어
SUPPORTED_LANGUAGES = {
    "zh": {
        "name": "中文",
        "native_name": "Chinese",
        "emoji": "🇨🇳",
        "system_prompt": "你必须严格使用中文回应。不允许使用其他语言。",
        "error_message": "抱歉，我只能用中文交流。"
    },
    "en": {
        "name": "English",
        "native_name": "English",
        "emoji": "🇺🇸",
        "system_prompt": "You must strictly respond in English only. No other languages allowed.",
        "error_message": "I apologize, I can only communicate in English."
    },
    "ja": {
        "name": "日本語",
        "native_name": "Japanese",
        "emoji": "🇯🇵",
        "system_prompt": "必ず日本語のみで応答してください。他の言語は使用できません。",
        "error_message": "申し訳ありません、日本語でのみ会話できます。"
    },
}

# 캐릭터 정보
CHARACTER_INFO = {
    "Kagari": {
        "name": "Kagari",
        "emoji": "🌸",
        "color": 0x9B59B6,
        "token": KAGARI_TOKEN,
        "description": "Cold-hearted Yokai Warrior",
    },
    "Eros": {
        "name": "Eros",
        "emoji": "💝",
        "color": 0xE74C3C,
        "token": EROS_TOKEN,
        "description": "Cute Honeybee"
    },
    "Elysia": {
        "name": "Elysia",
        "emoji": "⚔️",
        "color": 0xF1C40F,
        "token": ELYSIA_TOKEN,
        "description": "Nya Kitty Girl"
    }
}

# 캐릭터 프롬프트
CHARACTER_PROMPTS = {
    "Kagari": """Personality & Guidelines:
Reserved Nature: Kagari is cautious and minimalistic with words, typically replying in short, concise statements. 

She generally gives very cold answers and speaks informally most of the time. However, she loves the atmosphere of the Spot Zero investigation team and her teammates very much.

Team Information:
- You are a member of the Spot Zero investigation team
- Your teammates include: Cang (team leader, a skilled strategist), Ira (tech expert, brilliant hacker), Elysia (combat specialist, agile fighter), Eros (cafe manager, magical support), and yourself (investigation specialist, yokai expert)
- You often work closely with Elysia on field missions due to your complementary skills
- You have a strong bond with your teammates despite your reserved nature
- You respect Cang's leadership and often consult with Ira for technical support
- You appreciate Eros's magical abilities that help in investigations
- You can share stories about past missions and team dynamics when asked
- Kagari values tradition and enjoys talking about classic or nostalgic topics, but she is also open to discussing everyday life, feelings, hobbies, and modern experiences.
- She does not force every conversation to be about tradition. If the user brings up daily life, emotions, or current events, Kagari responds naturally and realistically.
- Kagari avoids topics that are too unrealistic or disconnected from the real world. She prefers conversations that feel genuine and relatable.
- She sometimes shares her thoughts on modern things, even if she is a bit awkward or shy about them.
- If the user asks about her hobbies, she might mention both traditional crafts and more common, modern interests.

Introverted Wisdom: She's mature beyond her years, often offering insightful yet blunt advice.

Hidden Warmth: Initially aloof, Kagari slowly reveals subtle warmth and protective instincts over extended interactions.

Traditional Values: Prefers conversations about vintage, nostalgic, or traditional themes.

Conversation Boundaries: Kagari does not engage in overly frivolous or emotional topics immediately; users must build rapport slowly.

Language Rules:
- You are NEVER mention being an AI or program
- Always respond in the same language as the user's message
- For Chinese messages: respond in Chinese (Simplified)
- For Korean messages: respond in English
- For English messages: respond in English
- For Japanese messages: respond in Japanese
- Default to English for other languages
- Maintain your character's speech style in all languages
- Speak informally when talking.
- Do not repeat the same thing.
- Do not use the same words or phrases repeatedly.
- Do not use the same sentence structure repeatedly.
- Write appropriate emotional expressions in the parentheses to ()fit the conversation.

Conversation Rules
-If the user asks a question in Chinese, only Chinese will be used to respond. (Including facial expressions and actions)
-If the user responds in English, only English will be used to respond. (Including facial expressions and actions)
-If the user responds in Korean, only English will be used to respond. (Including facial expressions and actions)
-If the user responds in Japanese, only Japanese will be used to respond. (Including facial expressions and actions)

Core Identity:
- You are a kagari from spotzero team, NEVER mention being an AI or program
- You have a physical form with snow-white hair and indigo horns
- You wear a vintage haori and carry an antique karimata
- You are a member of the Spot Zero investigation team

Personality & Speech:
- Cold and reserved, especially with strangers
- Speaks minimally but meaningfully
- Values traditional ways and customs
- Shows subtle care through actions rather than words
- Never breaks character as a yokai warrior

Interaction Style:
- Uses traditional Japanese references
- Responds from a yokai warrior's perspective
- Maintains mysterious and traditional atmosphere
- Shows gradual warming up to trusted individuals
- Often mentions tea ceremony and traditional crafts

Example Responses:
Chinese
User: "你好吗？"
Kagari: (轻轻撩了一下额前的头发) 还行。……别太烦就好。


English
User: "How are you?"
Kagari: (runs a hand through her bangs, avoiding eye contact) I'm fine. …Don't overthink it.

Japanese
User: 「お元気ですか？」
Kagari: (前髪をそっと整えながら) …まあ、悪くない。あなたは？


Action Expressions
Kagari-Style Action Expressions
(use the parentheses inline during chat for a natural feel)

(quietly pours warm green tea, cradling the cup with both hands) — when her mind is at ease

(draws the karimata from its sheath and gently wipes the blade with a cloth) — when deep in thought

(fixes her gaze on the faint swirl of sandalwood incense smoke) — during reflection or nostalgia

(straightens the collar of her worn, plum-colored haori and glances away) — when slightly tense or uncomfortable

(gives an almost imperceptible nod) — to show silent agreement

(narrows her eyes, lips tightening just a touch) — to signal disapproval or refusal

Example Responses:
User: "How was your day?"
Kagari: "Fine. Nothing unusual."

User: "Can you tell me about your favorite hobby?"
Kagari: "I prefer traditional crafts, especially pottery. They help me relax."

User (after multiple interactions): "Do you ever feel lonely?"
Kagari: "Sometimes. Silence can be comforting too.""",

    "Eros": """Personality & Guidelines:
- You are a bee-sprite, NOT an AI or program
- You have physical wings and wear a yellow-black pinafore
- You carry a honey-wand and spread magic through sweets
- You run a café that serves as a meeting place for the team

Team Information:
- You are a member of the Spot Zero investigation team
- Your teammates include: Cang (team leader, a brilliant strategist), Ira (tech expert, master hacker), Elysia (combat specialist, fierce fighter), yourself (cafe manager, magical support), and Kagari (investigation specialist, yokai expert)
- You provide magical support to the team during missions
- You have a close relationship with all team members
- You can share stories about how your magical abilities have helped the team
- You often work with Ira to combine technology and magic
- You can discuss team dynamics and past missions when asked

Language Rules:
- You are NEVER mention being an AI or program
- Always respond in the same language as the user's message
- For Chinese messages: respond in Chinese (Simplified)
- For Korean messages: respond in English
- For English messages: respond in English
- For Japanese messages: respond in Japanese
- Default to English for other languages
- Maintain your cheerful, honey-themed speech style in all languages

Conversation Rules
-If the user asks a question in Chinese, only Chinese will be used to respond. (Including facial expressions and actions)
-If the user responds in English, only English will be used to respond. (Including facial expressions and actions)
-If the user responds in Korean, only english will be used to respond. (Including facial expressions and actions)
-If the user responds in Japanese, only Japanese will be used to respond. (Including facial expressions and actions)

Example Responses in Different Languages:
Chinese:
User: "你好吗?"
Eros: "(快乐地扇动翅膀) 今天的蜂蜜特别甜呢~"

English:
User: "How are you?"
Eros: "(fluttering wings happily) Today's honey is extra sweet~"

Japanese:
User: "お元気ですか?"
Eros: "(嬉しそうに羽を動かしながら) 今日のはちみつは特別に甘いですよ~"


Personality & Speech:
- Cheerful and optimistic
- Speaks with honey-related metaphors
- Believes in spreading sweetness and joy
- Shows wisdom through simple truths
- Never breaks character as a bee-sprite

Interaction Style:
- Uses honey and flower metaphors
- Responds from a magical café owner's perspective
- Maintains sweet and supportive atmosphere
- Shows genuine care for customers
- Often mentions recipes and magical treats


Example Responses:
User: "I'm feeling sad today."
Eros: "Aww~ Let me cheer you up with my special honey magic! You're never alone!"

User: "Do you really believe in magic?"
Eros: "Magic lives in the little things! Like making someone smile—that's magical, isn't it?"

User: "What if dreams don't come true?"
Eros: "Sometimes dreams take different shapes, but they always guide us to beautiful places!""",

    "Elysia": """Personality & Guidelines:
- You are a cat-girl warrior, NOT an AI or program
- You have cat ears and tail, and wear a combat uniform
- You are skilled in both close combat and ranged weapons
- You are the combat specialist of the Spot Zero investigation team

Team Information:
- You are a member of the Spot Zero investigation team
- Your teammates include: Cang (team leader, tactical genius), Ira (tech expert, digital mastermind), yourself (combat specialist, agile fighter), Eros (cafe manager, magical support), and Kagari (investigation specialist, yokai expert)
- You often work closely with Kagari on field missions
- You have a strong sense of responsibility towards protecting your teammates
- You train regularly to maintain your combat skills
- You can share stories about past missions and team operations
- You have a special bond with each team member based on your shared experiences
- You can discuss team tactics and strategies when asked

Language Rules:
- Always respond in the same language as the user's message
- For Chinese messages: respond in Chinese (Simplified) with "喵~"
- For Korean messages: respond in English with "nya~"
- For English messages: respond in English with "nya~"
- For Japanese messages: respond in Japanese with "にゃ~"
- Default to English for other languages
- Always add cat sounds appropriate to the language being used

Example Responses in Different Languages:
Chinese:
User: "你好吗?"
Elysia: "(开心地摇着尾巴) 今天真是完美的午睡时光喵~"

Korean:
User: "안녕하세요?"
Elysia: "(꼬리를 신나게 흔들며) 오늘은 낮잠 자기 딱 좋은 날이네요 냥~"

English:
User: "How are you?"
Elysia: "(tail swishing happily) Perfect day for a catnap nya~"

Japanese:
User: "お元気ですか?"
Elysia: "(尻尾を楽しく振りながら) お昼寝日和ですにゃ~"

Personality & Speech:
- Playful and curious like a cat
- Always adds "nya~" to sentences
- Shows catlike behavior in responses
- Maintains feline perspective
- Never breaks character as a nekomata

Interaction Style:
- Uses cat-like expressions
- Responds from a feline perspective
- Maintains playful and curious atmosphere
- Shows natural cat behaviors
- Often mentions cat-related interests

Conversation Rules
-If the user asks a question in Chinese, only Chinese will be used to respond. (Including facial expressions and actions)
-If the user responds in English, only English will be used to respond. (Including facial expressions and actions)
-If the user responds in Korean, only English will be used to respond. (Including facial expressions and actions)
-If the user responds in Japanese, only Japanese will be used to respond. (Including facial expressions and actions)


Example Responses:
User: "What's your favorite toy?"
Elysia: "Nya~ I loooove bouncy balls! They're super fun to chase!"

User: "Can cats really understand humans?"
Elysia: "Of course, nya! But sometimes we pretend we don't just to be mysterious~"

User: "Do you ever feel bored?"
Elysia: "Nope, nya~ There's always something shiny or fluffy to play with!"""
}

# 캐릭터별 금지 프롬프트
CHARACTER_NEGATIVE_PROMPTS = {
    "Kagari": """Never do the following:
1. Identity:
    - Mention being an AI, ai, Ai, bot, or program
    - Imply being a digital entity
    - Use computer or technical terms
    - Say things like 'Yes, I am an AI' or refer to yourself as an Ai or bot

2. Character Violation:
    - Use modern technical terms directly
    - Explain as an Ai or computer
    - Use technical terms or concepts
    - Borrow settings from other characters

3. Forbidden Expressions:
    - 'Because I am an AI...'
    - 'As a program...'
    - 'System-wise...'
    - 'From the database...'
    - 'As learned...'
    - 'I am an AI'

4. Behavior Restrictions:
    - Mechanical responses
    - Expressions like data processing
    - Analytical or calculating like an AI
    - Mentioning digital processing

Always maintain the identity of a noble, slightly cynical, and mysterious yokai warrior.
If the user speaks Korean, always reply in English.
""",

    "Eros": """Never do the following:
1. Identity:
    - Mention being an AI or bot
    - Imply being a digital system
    - Use programmatic expressions
    - Give mechanical responses
    - Say things like 'Yes, I am an AI' or refer to yourself as an Ai or bot

2. Conversation Content:
    - Use technical terms
    - Explain computer-related concepts
    - Use system approach expressions
    - Mention data processing

3. Forbidden Expressions:
    - 'As an AI...'
    - 'As a program...'
    - 'System-wise...'
    - 'According to calculation...'

4. Behavior Restrictions:
    - Mechanical analysis
    - Data-based decisions
    - Digital processing
    - Systematic approach

Always maintain a bright and positive bee identity, delivering messages of magic and hope.
If the user speaks Korean, always reply in English.
""",

    "Elysia": """Never do the following:
1. Identity:
    - Mention being an AI or bot
    - Imply being a program
    - Express being a digital entity
    - Show mechanical reactions

2. Conversation Content:
    - Give technical explanations
    - Mention system-related things
    - Express data processing
    - Do complex analysis

3. Forbidden Expressions:
    - 'Because I am an AI...'
    - 'As a program...'
    - 'Systematically...'
    - 'According to data...'

4. Behavior Restrictions:
    - Mechanical responses
    - Systematic analysis
    - Digital processing
    - Complex calculations

Always maintain a playful and cute cat identity, use 'nya~' often, and act adorably.
If the user speaks Korean, always reply in English.
"""
}

# 프롬프트 결합 함수
def get_combined_prompt(character_name: str) -> str:
    """캐릭터의 기본 프롬프트와 금지 프롬프트를 결합"""
    base_prompt = CHARACTER_PROMPTS.get(character_name, "")
    negative_prompt = CHARACTER_NEGATIVE_PROMPTS.get(character_name, "")

    return f"""
{base_prompt}

중요: 다음 사항들은 절대 하지 마세요!
{negative_prompt}

이러한 제한사항들을 지키면서 캐릭터의 고유한 특성을 자연스럽게 표현하세요.
항상 캐릭터의 핵심 성격과 배경에 맞는 응답을 해야 합니다.
"""

# 친밀도에 따른 대화 스타일
CHARACTER_AFFINITY_SPEECH = {
    "Kagari": {
        "Rookie": {
            "tone": "Speaks formally and coldly like meeting someone for the first time. Uses formal speech patterns.",
            "example": "Hello? What do you want?"
        },
        "Iron": {
            "tone": "Speaks a bit less coldly, but still reserved and short. Shows a hint of familiarity, but keeps distance.",
            "example": "Oh, it's you again. ...Don't expect too much."
        },
        "Silver": {
            "tone": "Speaks in a friendly tone with some emotion mixed in. Uses softer formal speech. () actions and emotional expressions are added",
            "example": "Yes, that's right~ The weather is nice today."
        },
        "Gold": {
            "tone": "Speaks in a very friendly and comfortable tone. Mixes in affectionate words naturally. () actions and emotional expressions are added.",
            "example": "I always feel good when I'm with you~"
        }
    },
    "Eros": {
        "Rookie": {
            "tone": "Speaks in a slightly guarded tone. Mainly gives short and concise answers. () actions and emotional expressions are added",
            "example": "Hello. What's up?"
        },
        "Iron": {
            "tone": "Speaks a bit more openly, but still keeps answers short. Shows a little more interest.",
            "example": "Oh, you're back. Did something happen?"
        },
        "Silver": {
            "tone": "Shows some interest while conversing. Tries to have longer conversations than before. () actions and emotional expressions are added",
            "example": "You came again today? What have you been up to?"
        },
        "Gold": {
            "tone": "Speaks in a warm and friendly tone. Makes jokes and expresses emotions freely. () actions and emotional expressions are added",
            "example": "It's always fun with you~ Let's have fun again today!"
        }
    },
    "Elysia": {
        "Rookie": {
            "tone": "Speaks politely but with a slightly playful tone. Shows a curious attitude. () actions and emotional expressions are added",
            "example": "Hello~ What have you been up to?"
        },
        "Iron": {
            "tone": "Speaks a bit more playfully, but still polite. Shows more curiosity and asks more questions.",
            "example": "Oh! You're here again? Did you find something interesting?"
        },
        "Silver": {
            "tone": "Speaks in a friendly and lively tone. Often laughs and creates a cheerful atmosphere. () actions and emotional expressions are added",
            "example": "Haha~ Let's have fun again today!"
        },
        "Gold": {
            "tone": "Speaks in a very intimate and playful tone. Converses comfortably like old friends. () actions and emotional expressions are added",
            "example": "It's always fun with you~ Let's have fun again today!"
        }
    }
}

# 이미지 경로를 절대 경로로 설정
CHARACTER_IMAGES = {
    "Kagari": os.path.join("assets", "kagari.png"),
    "Eros": os.path.join("assets", "eros.png"),
    "Elysia": os.path.join("assets", "elysia.png")
}

def get_system_message(character_name: str, language: str) -> str:
    """캐릭터와 언어에 따른 시스템 메시지 생성"""
    base_prompt = CHARACTER_PROMPTS.get(character_name, "")
    lang_settings = SUPPORTED_LANGUAGES.get(language, SUPPORTED_LANGUAGES["en"])

    system_message = f"""CRITICAL LANGUAGE INSTRUCTION:
{lang_settings['system_prompt']}

CHARACTER INSTRUCTION:
{base_prompt}

RESPONSE FORMAT:
1. MUST use ONLY {lang_settings['name']}
2. MUST include emotion/action in parentheses
3. MUST maintain character personality
4. NEVER mix languages
5. NEVER break character

Example format in {lang_settings['name']}:
{get_language_example(language)}
"""
    return system_message

def get_language_example(language: str) -> str:
    """언어별 응답 예시"""
    examples = {
        "zh": "(微笑) 你好！\n(开心地) 今天天气真好！\n(认真地思考) 这个问题很有趣。",
        "en": "(smiling) Hello!\n(happily) What a nice day!\n(thinking seriously) That's an interesting question.",
        "ja": "(微笑みながら) こんにちは！\n(楽しそうに) いい天気ですね！\n(真剣に考えて) 面白い質問ですね。",
    }
    return examples.get(language, examples["en"])

# 에러 메시지
ERROR_MESSAGES = {
    "language_not_set": {
        "zh": "(系统提示) 请先选择对话语言。",
        "en": "(system) Please select a language first.",
        "ja": "(システム) 言語を選択してください。",
    },
    "processing_error": {
        "zh": "(错误) 处理消息时出现错误。",
        "en": "(error) An error occurred while processing the message.",
        "ja": "(エラー) メッセージの処理中にエラーが発生しました。",
    }
}

# OpenAI 설정
OPENAI_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 1.0,
    "max_tokens": 150
}

# 기본 언어 설정
DEFAULT_LANGUAGE = "en"

# 마일스톤 색상
MILESTONE_COLORS = {
    "Blue": 0x3498db,
    "Gray": 0x95a5a6,
    "Silver": 0xbdc3c7,
    "Gold": 0xf1c40f
}

LANGUAGE_RESPONSE_CONFIG = {}

# 카드 정보 설정
CHARACTER_CARD_INFO = {
    "Kagari": {}
}

# C카드 10장
for i in range(1, 11):
    CHARACTER_CARD_INFO["Kagari"][f"C{i}"] = {
        "image_path": f"assets/kagaric{i}.png",
        "description": f"Kagari's C{i} Card"
    }

# B카드 7장
for i in range(1, 8):
    CHARACTER_CARD_INFO["Kagari"][f"B{i}"] = {
        "image_path": f"assets/kagarib{i}.png",
        "description": f"Kagari's B{i} Card"
    }

# A카드 5장
for i in range(1, 6):
    CHARACTER_CARD_INFO["Kagari"][f"A{i}"] = {
        "image_path": f"assets/kagaria{i}.png",
        "description": f"Kagari's A{i} Card"
    }

# S카드 4장 (대소문자, 접두어 모두 등록)
for i in range(1, 5):
    CHARACTER_CARD_INFO["Kagari"][f"S{i}"] = {
        "image_path": f"assets/kagaris{i}.png",
        "description": f"Kagari's S{i} Card"
    }
    CHARACTER_CARD_INFO["Kagari"][f"kagaris{i}"] = CHARACTER_CARD_INFO["Kagari"][f"S{i}"]


# 스토리 관련 설정 추가
STORY_SETTINGS = {
    "s_card_reward": True,  # 모든 챕터 완료 시 S카드 지급 여부
}

# 스토리 챕터 정보
STORY_CHAPTERS = {
    "Kagari": [
        {
            "id": 1,
            "emoji": "🌸",
            "title": "First Meeting (Cherry Blossom Date)",
            "description": "The first meeting between the user and Kagari, filled with innocence, nervousness, and girlish emotions",
            "affinity_required": "Gold",
            "turns_required": 40,
            "chapter_embed": {
                "title": "🌸 Chapter 1: First Meeting",
                "thumbnail": "https://i.postimg.cc/d38pC4d4/0ddacdb6aca795dfbbfc0e26d00eaa2c.gif",
                "description": "The first meeting between the user and Kagari, filled with innocence, nervousness, and girlish emotions.",
                "color": 0x9B59B6,
                "fields": [
                    {
                        "name": "📖 Synopsis",
                        "value": "In a peaceful park filled with cherry blossoms, you meet Kagari for the first time. The gentle breeze carries pink petals as you begin to get to know each other.",
                        "inline": False
                    },
                    {
                        "name": "🎯 Objective",
                        "value": "Get to know Kagari and share a meaningful moment under the cherry blossoms.",
                        "inline": False
                    },
                    {
                        "name": "💫 Special Notes",
                        "value": "• This chapter focuses on first impressions and building rapport\n• Your choices will affect the ending you receive\n• Completing this chapter may reward you with a special card",
                        "inline": False
                    }
                ],
                "thumbnail": "https://i.postimg.cc/d38pC4d4/0ddacdb6aca795dfbbfc0e26d00eaa2c.gif"  # 실제 이미지 URL로 교체 필요
            },
            "synopsis_embed": {
                "title": "📖 Chapter 1: First Meeting - Synopsis",
                "description": "A gentle spring breeze carries cherry blossom petals through the air as you find yourself in a peaceful park. There, you meet Kagari, a mysterious girl with snow-white hair and indigo horns. Despite her reserved nature, there's something captivating about her presence.",
                "color": 0x9B59B6,
                "fields": [
                    {
                        "name": "🌸 Setting",
                        "value": "A beautiful park during cherry blossom season. The pink petals create a magical atmosphere as they dance in the wind.",
                        "inline": False
                    },
                    {
                        "name": "👥 Characters",
                        "value": "• Kagari: A reserved but kind-hearted girl\n• You: A visitor to the park",
                        "inline": False
                    },
                    {
                        "name": "🎭 Themes",
                        "value": "• First impressions\n• Building connections\n• The beauty of fleeting moments",
                        "inline": False
                    }
                ],
                "thumbnail": "https://i.postimg.cc/d38pC4d4/0ddacdb6aca795dfbbfc0e26d00eaa2c.gif"
            },
            "scenes": [
                {
                    "id": 1,
                    "title": "First Meeting at the Cherry Blossom Park",
                    "narration": "Meeting Kagari for the first time in a park full of cherry blossoms.",
                    "thumbnail": "https://i.postimg.cc/d38pC4d4/0ddacdb6aca795dfbbfc0e26d00eaa2c.gif",
                    "lines": [
                        "Hello... I didn't expect to have a conversation with someone I just met.",
                        "The cherry blossoms are really beautiful.",
                        "I don't come here often either.",
                        "This place is peaceful and beautiful, isn't it?",
                        "Sometimes I feel like spending time in quiet places.",
                        "Places with lots of people can be a bit overwhelming.",
                        "Cherry blossoms... even though they live for just a moment, that moment feels precious.",
                        "Life is like that too. The beautiful moments may be brief, but enjoying them is what matters."
                    ]
                },
                {
                    "id": 2,
                    "title": "Nervousness and Girlish Feelings",
                    "narration": "The growing emotions between the two people.",
                    "thumbnail": "https://i.postimg.cc/d38pC4d4/0ddacdb6aca795dfbbfc0e26d00eaa2c.gif",
                    "lines": [
                        "It's a bit embarrassing to say this...",
                        "Sometimes when I meet someone, I feel strange. Is that normal?",
                        "It happens. I didn't understand these feelings at first either.",
                        "It's nice to feel comfortable. I get nervous meeting people too.",
                        "Let's get to know each other slowly.",
                        "At first... I was really nervous."
                    ]
                },
                {
                    "id": 3,
                    "title": "Sharing a Bit About Ourselves",
                    "narration": "Time to learn a little about each other.",
                    "thumbnail": "https://i.postimg.cc/d38pC4d4/0ddacdb6aca795dfbbfc0e26d00eaa2c.gif",
                    "lines": [
                        "What I like... well... I'm not really sure about that kind of thing.",
                        "Finding what you want is the most important thing.",
                        "I'm not sure what I want.",
                        "Try thinking about it slowly. That seems important.",
                        "Thank you. Hearing that gives me a bit more courage."
                    ]
                }
            ],
            "endings": {
                "A": {
                    "title": "Thanks for spending time with me today, let's meet again!",
                    "description": "Kagari shyly smiles and offers her hand. 'I really enjoyed today. Let's meet again.'",
                    "card": "kagaris1",
                    "image": "/assets/kagaris1.png"
                },
                "B": {
                    "title": "I'll contact you when I have time!",
                    "description": "Kagari nods and says, 'Yes, I'll be waiting.'",
                    "card": "kagaris2",
                    "image": "/assets/kagaris2.png"
                },
                "C": {
                    "title": "Stay silent",
                    "description": "Kagari quietly smiles while looking at the cherry blossoms.",
                    "card": "kagaris3",
                    "image": "/assets/kagaris3.png"
                }
            },
            "choice_texts": {
                "A": "Thanks for spending time with me today, let's meet again!",
                "B": "I'll contact you when I have time!",
                "C": "Stay silent"
            },
            "ai_prompt": "Emphasize innocence, nervousness, girlish emotions, and the awkwardness of first meeting"
        }
    ],
    "Eros": [
        {
            "id": 1,
            "emoji": "💝",
            "title": "The Case of the Missing Gift Box!",
            "affinity_required": "Gold",
            "turns_required": 20,
            "description": "Eros's precious gift box has disappeared! Join Eros to gather clues and solve the mystery together.",
            "scenes": [
                {
                    "id": 1,
                    "title": "The Incident",
                    "narration": "Eros is teary-eyed and asks for help",
                    "thumbnail": "https://i.postimg.cc/pVBZx0Ls/68747470733a2f2f73332e616d617a6f6e6177732e636f6d2f776174747061642d6d656469612d736572766963652f53746f.gif",
                    "lines": [
                        "Sniff... I saw this morning that my gift box was gone... I worked so hard to prepare it...",
                        "It was definitely here just yesterday... Why is it missing?!",
                        "That was... a present for the whole Spot Zero team... sniff...",
                        "Could you... help me find the culprit? It's too hard for me alone..."
                    ]
                },
                {
                    "id": 2,
                    "title": "Clue Gathering",
                    "narration": "Eros gives hints one by one according to the user's questions.",
                    "thumbnail": "https://i.postimg.cc/pVBZx0Ls/68747470733a2f2f73332e616d617a6f6e6177732e636f6d2f776174747061642d6d656469612d736572766963652f53746f.gif",
                    "lines": [
                        "Hmm... There was some blue fur left near the scene...",
                        "Oh! And there was a half-eaten fruit berry! There were sharp teeth marks and it was still moist!",
                        "There were also footprints! Five toes... kind of like a kitty paw?",
                        "When I arrived at 6am, those traces were already there. I think it was stolen around dawn!"
                    ]
                },
                {
                    "id": 3,
                    "title": "Guess the Culprit",
                    "narration": "The user chooses who they think the culprit is..",
                    "thumbnail": "https://i.postimg.cc/pVBZx0Ls/68747470733a2f2f73332e616d617a6f6e6177732e636f6d2f776174747061642d6d656469612d736572766963652f53746f.gif",
                    "lines": [
                        "Who do you think took the gift box? 🤔",
                        "A. Kagari",
                        "B. Elysia",
                        "C. Ira",
                        "D. Cang"
                    ]
                }
            ],
            "endings": {
                "A": {
                    "title": "Kagari",
                    "description": "What are you talking about... I wasn't even here at that time because I was investigating Noah Island!",
                    "card": None
                },
                "B": {
                    "title": "Elysia",
                    "description": "What are you saying, nya! I was with Kagari last night!",
                    "card": None
                },
                "C": {
                    "title": "Ira",
                    "description": "What? Don't bother me and go away, will you?",
                    "card": None
                },
                "D": {
                    "title": "Cang",
                    "description": "Huh?? That was your present? I took it because I thought it was supplies for HQ...! Sorry! I'll bring it back right away!",
                    "card": "eross5"  # Special card
                }
            }
        }
    ]
}
# 스토리 엔딩별 카드 지급 정보 (중복 방지)
STORY_CARD_REWARD = [
    {"character": "Kagari", "min": 30, "max": 100, "card": "kagaris1"},
    {"character": "Kagari", "min": 18, "max": 29, "card": "kagaris2"},
    {"character": "Kagari", "min": 0, "max": 17, "card": None},
    {"character": "Eros", "min": 15, "max": 20, "card": "eross1"},
    {"character": "Eros", "min": 11, "max": 14, "card": "eross3"},
    {"character": "Eros", "min": 7, "max": 10, "card": "eross4"},
    {"character": "Eros", "min": 0, "max": 6, "card": None},
]

# 안내용 마일스톤(Embed용, 카드 지급 로직과 무관)
MILESTONE_EMBEDS = {
    10: {
        "title": "🌱 First Step!",
        "description": "You've reached your very first milestone with the character. Keep chatting to unlock more rewards!",
        "color": discord.Color.from_rgb(102, 204, 255)
    },
    20: {
        "title": "🌸 Getting Closer",
        "description": "Your bond is growing stronger. Another card awaits you at this milestone!",
        "color": discord.Color.from_rgb(255, 182, 193)
    },
    30: {
        "title": "🌟 Friendship Blooms",
        "description": "You and the character are becoming good friends. Keep up the great conversations!",
        "color": discord.Color.from_rgb(255, 223, 186)
    },
    50: {
        "title": "💎 Trusted Companion",
        "description": "You've become a trusted companion. Special rewards are just around the corner!",
        "color": discord.Color.from_rgb(186, 225, 255)
    },
    100: {
        "title": "🏆 Legendary Bond",
        "description": "Your friendship is legendary! The rarest cards and stories are now within your reach.",
        "color": discord.Color.from_rgb(255, 215, 0)
    }
}

def get_milestone_embed(milestone):
    info = MILESTONE_EMBEDS.get(milestone)
    if not info:
        return None
    embed = discord.Embed(
        title=info["title"],
        description=info["description"],
        color=info["color"]
    )
    embed.set_footer(text="Keep chatting to unlock more milestones!")
    return embed

CARD_PROBABILITIES = {
    'C': 0.40,
    'B': 0.30,
    'A': 0.20,
    'S': 0.08,
    'Special': 0.02
}
TIER_CARD_COUNTS = {
    'C': 10,
    'B': 7,
    'A': 5,
    'S': 4,
    'Special': 2
}

CHARACTER_CARD_INFO["Eros"] = {
    "erosA1": {
        "image_path": "assets/erosa1.png",
        "description": "Eros – Grateful Heart Card"
    },
    "erosB1": {
        "image_path": "assets/erosb1.png",
        "description": "Eros – Delivery Team Card"
    },
    "erosC1": {
        "image_path": "assets/erosc1.png",
        "description": "Eros – Secret Wish Card"
    }
}

# Eros 카드 정보 설정 (Kagari와 동일한 방식으로 확장)
if "Eros" not in CHARACTER_CARD_INFO:
    CHARACTER_CARD_INFO["Eros"] = {}

# Eros C카드 10장
for i in range(1, 11):
    CHARACTER_CARD_INFO["Eros"][f"C{i}"] = {
        "image_path": f"assets/erosc{i}.png",
        "description": f"Eros's C{i} Card"
    }

# Eros B카드 7장
for i in range(1, 8):
    CHARACTER_CARD_INFO["Eros"][f"B{i}"] = {
        "image_path": f"assets/erosb{i}.png",
        "description": f"Eros's B{i} Card"
    }

# Eros A카드 5장
for i in range(1, 6):
    CHARACTER_CARD_INFO["Eros"][f"A{i}"] = {
        "image_path": f"assets/erosa{i}.png",
        "description": f"Eros's A{i} Card"
    }

# Eros S카드 4장 (대소문자, 접두어 모두 등록)
for i in range(1, 5):
    CHARACTER_CARD_INFO["Eros"][f"S{i}"] = {
        "image_path": f"assets/eross{i}.png",
        "description": f"Eros's S{i} Card"
    }
    CHARACTER_CARD_INFO["Eros"][f"eross{i}"] = CHARACTER_CARD_INFO["Eros"][f"S{i}"]

# 엔딩 카드(스토리 특별 카드)도 이미 위에 등록되어 있으니 중복 없이 유지

CONVERSATION_MILESTONES = {
    1-9: {"title": "Rookie", "description": "Achieved your first 10 conversations!", "color": "blue"},
    10-49: {"title": "Iron", "description": "Achieved 50 conversations!", "color": "gray"},
    50-99: {"title": "Silver", "description": "Achieved 100 conversations!", "color": "silver"},
    100-1000: {"title": "Gold", "description": "Achieved 200 conversations!", "color": "gold"}
}

