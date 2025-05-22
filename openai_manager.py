     # openai_manager.py
import openai
import re

async def call_openai(prompt, model="gpt-4o"):
    try:
        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[OpenAI Error] {e}")
        return "[score:0]"  # 기본값 반환

async def analyze_emotion_with_gpt(message: str) -> int:
    prompt = (
        f"Classify the following user message as Positive (+1), Neutral (0), or Negative (-1):\n"
        f"User: \"{message}\"\n"
        "Reply ONLY with [score:+1], [score:0], or [score:-1]."
    )
    ai_reply = await call_openai(prompt)
    match = re.search(r"\[score:([+-]?\d+)\]", ai_reply)
    try:
        return int(match.group(1)) if match else 0
    except Exception:
        return 0

def analyze_emotion_with_patterns(message: str) -> int:
    positive_keywords = ["Praise", "Empathy", "Consideration", "Interest in character’s story or feelings", " Sharing own thoughts or concern", "Long-form replies", "Consultation", "Sharing"]
    negative_keywords = ["Abusive", "Rude", "Unhealthy", "Inappropriate", "Dismissive", "Irritated""Too Short or Passive"]
    if any(word in message for word in positive_keywords):
        return 1
    if any(word in message for word in negative_keywords):
        return -1
    if len(message.strip()) <= 5:
        return 0
    return 0

async def analyze_emotion_with_gpt_and_pattern(message: str) -> int:
    gpt_score = await analyze_emotion_with_gpt(message)
    pattern_score = analyze_emotion_with_patterns(message)
    final_score = round(gpt_score * 0.7 + pattern_score * 0.3)
    return final_score