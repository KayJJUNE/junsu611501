from datetime import datetime, date
import json
import aiosqlite
import discord
import psycopg2
import os

# Railway 환경변수에서 DATABASE_URL 읽기
DATABASE_URL = os.environ.get("DATABASE_URL", "${{ Postgres.DATABASE_URL }}")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

class DatabaseManager:
    def __init__(self):
        self.db_name = "chatbot.db"
        self.default_language = "en"
        print("Database initialized with default language: English")
        self.setup_database()  # 동기 방식으로 초기 테이블 생성
        self.MAX_DAILY_MESSAGES = 100  # 일일 최대 메시지 수 정의

    def setup_database(self):
        """데이터베이스 초기화"""
        print("Setting up database tables for PostgreSQL...")
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                # conversations
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id SERIAL PRIMARY KEY,
                        channel_id BIGINT,
                        user_id BIGINT,
                        character_name TEXT,
                        message_role TEXT,
                        content TEXT,
                        language TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # affinity
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS affinity (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        character_name TEXT,
                        emotion_score INTEGER DEFAULT 0,
                        daily_message_count INTEGER DEFAULT 0,
                        last_daily_reset DATE DEFAULT CURRENT_DATE,
                        last_message_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_message_content TEXT,
                        UNIQUE(user_id, character_name)
                    )
                ''')
                # user_language
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_language (
                        id SERIAL PRIMARY KEY,
                        channel_id BIGINT,
                        user_id BIGINT,
                        character_name TEXT,
                        language TEXT DEFAULT 'ko',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(channel_id, user_id, character_name)
                    )
                ''')
                # user_cards
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_cards (
                        user_id BIGINT,
                        character_name TEXT,
                        card_id TEXT,
                        obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        emotion_score_at_obtain INTEGER,
                        PRIMARY KEY (user_id, character_name, card_id)
                    )
                ''')
                # conversation_count
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversation_count (
                        id SERIAL PRIMARY KEY,
                        channel_id BIGINT,
                        user_id BIGINT,
                        character_name TEXT,
                        message_count INTEGER DEFAULT 0,
                        last_milestone INTEGER DEFAULT 0,
                        UNIQUE(channel_id, user_id, character_name)
                    )
                ''')
                # story_progress
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS story_progress (
                        user_id BIGINT,
                        character_name TEXT,
                        chapter_number INTEGER,
                        completed_at TIMESTAMP,
                        selected_choice TEXT,
                        ending_type TEXT,
                        PRIMARY KEY (user_id, character_name, chapter_number)
                    )
                ''')
                # story_unlocks
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS story_unlocks (
                        user_id BIGINT,
                        character_name TEXT,
                        chapter_id INTEGER,
                        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, character_name, chapter_id)
                    )
                ''')
                # story_choices
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS story_choices (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        character_name TEXT,
                        story_id TEXT,
                        choice_index INTEGER,
                        choice_text TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # scene_scores
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scene_scores (
                        user_id BIGINT,
                        character_name TEXT,
                        chapter_id INTEGER,
                        scene_id INTEGER,
                        score INTEGER,
                        PRIMARY KEY (user_id, character_name, chapter_id, scene_id)
                    )
                ''')
                # completed_chapters
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS completed_chapters (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        character_name TEXT,
                        chapter_id INTEGER,
                        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, character_name, chapter_id)
                    )
                ''')
                # user_milestone_claims
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_milestone_claims (
                        user_id BIGINT,
                        character_name TEXT,
                        milestone INTEGER,
                        claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, character_name, milestone)
                    )
                ''')
                # user_levelup_flags
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_levelup_flags (
                        user_id BIGINT,
                        character_name TEXT,
                        level TEXT,
                        flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, character_name, level)
                    )
                ''')
                # card_issued
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS card_issued (
                        character_name TEXT,
                        card_id TEXT,
                        issued_number INTEGER DEFAULT 0,
                        PRIMARY KEY (character_name, card_id)
                    )
                ''')
                # emotion_log
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS emotion_log (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        character_name TEXT,
                        score INTEGER,
                        message TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            conn.commit()
        print("All PostgreSQL tables have been created successfully.")

    def get_channel_language(self, channel_id: int, user_id: int, character_name: str) -> str:
        """채널의 언어 설정을 가져옵니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT language
                        FROM user_language
                            WHERE user_id = %s AND character_name = %s
                    ''', (user_id, character_name))
                    result = cursor.fetchone()
                    return result[0] if result else 'en'
        except Exception as e:
            print(f"Error getting channel language: {e}")
            return 'en'

    def set_channel_language(self, channel_id: int, user_id: int, character_name: str, language: str) -> bool:
        """채널의 언어 설정 업데이트"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT language FROM user_language 
                            WHERE channel_id = %s AND user_id = %s AND character_name = %s
                    ''', (channel_id, user_id, character_name))
                    result = cursor.fetchone()
                    if result:
                        cursor.execute('''
                            UPDATE user_language 
                                SET language = %s, updated_at = CURRENT_TIMESTAMP
                                WHERE channel_id = %s AND user_id = %s AND character_name = %s
                        ''', (language, channel_id, user_id, character_name))
                    else:
                        cursor.execute('''
                            INSERT INTO user_language 
                            (channel_id, user_id, character_name, language)
                                VALUES (%s, %s, %s, %s)
                        ''', (channel_id, user_id, character_name, language))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error in set_channel_language: {e}")
            return False

    def add_message(self, channel_id: int, user_id: int, character_name: str, role: str, content: str, language: str = None):
        """새 메시지 추가"""
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO conversations 
                    (channel_id, user_id, character_name, message_role, content, language)
                        VALUES (%s, %s, %s, %s, %s, %s)
                ''', (channel_id, user_id, character_name, role, content, language))
            conn.commit()

    def get_recent_messages(self, channel_id: int, limit: int = 10):
        """채널의 최근 메시지 가져오기"""
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT message_role, content 
                    FROM conversations 
                        WHERE channel_id = %s 
                    ORDER BY timestamp DESC 
                        LIMIT %s
                ''', (channel_id, limit))
                messages = cursor.fetchall()
                return [{"role": role, "content": content} for role, content in reversed(messages)]

    def get_affinity(self, user_id: int, character_name: str) -> dict:
        """사용자의 특정 캐릭터와의 친밀도 정보 조회"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    current_date = date.today().isoformat()

                    # 현재 날짜와 마지막 리셋 날짜가 다르면 daily_count 리셋
                    cursor.execute('''
                        UPDATE affinity 
                        SET daily_message_count = 0, 
                                last_daily_reset = %s
                            WHERE user_id = %s 
                            AND character_name = %s
                            AND last_daily_reset < %s
                    ''', (current_date, user_id, character_name, current_date))

                    # 친밀도 정보가 없으면 생성
                    cursor.execute('''
                        INSERT INTO affinity 
                        (user_id, character_name, emotion_score, daily_message_count, last_daily_reset) 
                            VALUES (%s, %s, 0, 0, %s)
                        ON CONFLICT (user_id, character_name) DO NOTHING
                    ''', (user_id, character_name, current_date))

                    # 친밀도 정보 조회
                    cursor.execute('''
                        SELECT emotion_score, daily_message_count,
                               last_daily_reset, last_message_time
                        FROM affinity
                            WHERE user_id = %s AND character_name = %s
                    ''', (user_id, character_name))

                    result = cursor.fetchone()
                    conn.commit()

                    if not result:
                        return {
                            'emotion_score': 0,
                            'daily_count': 0,
                            'last_reset': current_date,
                            'last_time': None
                        }

                    return {
                        'emotion_score': result[0],
                        'daily_count': result[1],
                        'last_reset': result[2],
                        'last_time': result[3]
                    }
        except Exception as e:
            print(f"Database error in get_affinity: {e}")
            return {
                'emotion_score': 0,
                'daily_count': 0,
                'last_reset': current_date,
                'last_time': None
            }

    async def update_affinity(self, user_id: int, character_name: str, last_message: str, last_message_time: str, score_change: int):
        """감정 기반 분석 점수 누적으로 호감도 업데이트"""
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT emotion_score, daily_message_count FROM affinity WHERE user_id=%s AND character_name=%s', (user_id, character_name))
                result = cursor.fetchone()
                current_score = result[0] if result else 0
                daily_count = result[1] if result else 0
                cursor.execute('''
                    INSERT INTO affinity 
                    (user_id, character_name, emotion_score, daily_message_count, 
                    last_message_content, last_message_time)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, character_name) 
                    DO UPDATE SET 
                        emotion_score = EXCLUDED.emotion_score,
                        daily_message_count = EXCLUDED.daily_message_count,
                        last_message_content = EXCLUDED.last_message_content,
                        last_message_time = EXCLUDED.last_message_time
                ''', (user_id, character_name, current_score + score_change, 
                      daily_count + 1, last_message, last_message_time))
            conn.commit()

    def reset_affinity(self, user_id: int, character_name: str) -> bool:
        """특정 유저의 친밀도 초기화"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE affinity
                        SET emotion_score = 0,
                            daily_message_count = 0,
                                last_daily_reset = CURRENT_DATE
                            WHERE user_id = %s AND character_name = %s
                    ''', (user_id, character_name))

                    if cursor.rowcount == 0:
                        cursor.execute('''
                            INSERT INTO affinity (user_id, character_name, emotion_score, daily_message_count, last_daily_reset)
                                VALUES (%s, %s, 0, 0, CURRENT_DATE)
                        ''', (user_id, character_name))

                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error resetting affinity for user {user_id}: {e}")
            return False

    def reset_all_affinity(self, character_name: str) -> bool:
        """모든 유저의 친밀도 초기화"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE affinity
                        SET emotion_score = 0,
                            daily_message_count = 0,
                                last_daily_reset = CURRENT_DATE
                            WHERE character_name = %s
                    ''', (character_name,))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error in reset_all_affinity: {e}")
            return False

    def get_affinity_ranking(self, character_name: str = None):
        """전체 친밀도 랭킹 조회"""
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                if character_name:
                    cursor.execute('''
                        SELECT user_id, score
                        FROM affinity
                            WHERE character_name = %s AND score > 0
                        ORDER BY score DESC
                        LIMIT 10
                    ''', (character_name,))
                else:
                    cursor.execute('''
                        SELECT user_id, SUM(score) as total_score
                        FROM affinity
                        GROUP BY user_id
                        HAVING total_score > 0
                        ORDER BY total_score DESC
                        LIMIT 10
                    ''')
                return cursor.fetchall()

    def check_language_consistency(self):
        """언어 일관성을 점검합니다."""
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT * FROM channel_settings
                ''')
                results = cursor.fetchall()
                for result in results:
                    channel_id, user_id, character_name, language, last_interaction = result
                    if language != self.get_channel_language(channel_id, user_id, character_name):
                        print(f"Language inconsistency found: channel_id={channel_id}, user_id={user_id}, character_name={character_name}, stored_language={language}, actual_language={self.get_channel_language(channel_id, user_id, character_name)}")
                return len(results) == 0 or all(language == self.get_channel_language(channel_id, user_id, character_name) for channel_id, user_id, character_name, language, last_interaction in results)

    def get_stored_language(self, channel_id: int, user_id: int, character_name: str) -> str:
        """채널의 저장된 언어를 가져옵니다."""
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT language
                    FROM channel_settings
                        WHERE channel_id = %s AND user_id = %s AND character_name = %s
                ''', (channel_id, user_id, character_name))
                result = cursor.fetchone()
                if result:
                    return result[0]
                else:
                    print(f"No language setting found, using default: {self.default_language}")
                    return self.default_language

    def get_stored_languages(self):
        """모든 채널의 저장된 언어를 가져옵니다."""
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT channel_id, user_id, character_name, language
                    FROM channel_settings
                ''')
                results = cursor.fetchall()
                return {f"{channel_id}-{user_id}-{character_name}": language for channel_id, user_id, character_name, language in results}

    def get_user_cards(self, user_id: int, character_name: str = None) -> list:
        """사용자의 카드 목록 조회 (card_id 기반)"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    if character_name:
                        cursor.execute('''
                            SELECT card_id FROM user_cards
                                WHERE user_id = %s AND character_name = %s
                            ORDER BY card_id
                        ''', (user_id, character_name))
                    else:
                        cursor.execute('''
                            SELECT character_name, card_id FROM user_cards
                                WHERE user_id = %s
                            ORDER BY character_name, card_id
                        ''', (user_id,))
                    return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting user cards: {e}")
            return []

    def has_user_card(self, user_id: int, character_name: str, card_id: str) -> bool:
        """사용자가 특정 카드를 보유하고 있는지 확인 (card_id 기반)"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT COUNT(*) FROM user_cards
                            WHERE user_id = %s AND character_name = %s AND card_id = %s
                    ''', (user_id, character_name, card_id))
                    return cursor.fetchone()[0] > 0
        except Exception as e:
            print(f"Error checking user card: {e}")
            return False

    def add_user_card(self, user_id: int, character_name: str, card_id: str):
        print(f"[DEBUG] add_user_card called: user_id={user_id}, character_name={character_name}, card_id={card_id}")
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO user_cards (user_id, character_name, card_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        (user_id, character_name, card_id)
                    )
                    print(f"[DEBUG] cursor.rowcount: {cursor.rowcount}")
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"[ERROR] add_user_card: {e}")
            return False

    def get_user_character_messages(self, user_id: int, character_name: str, limit: int = 20):
        """사용자와 특정 캐릭터의 최근 대화 기록 조회"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT message_role, content, timestamp
                        FROM conversations 
                            WHERE user_id = %s AND character_name = %s
                        ORDER BY timestamp DESC 
                            LIMIT %s
                    ''', (user_id, character_name, limit))
                    messages = cursor.fetchall()
                    return [{
                        "role": role,
                        "content": content,
                        "timestamp": timestamp
                    } for role, content, timestamp in reversed(messages)]
        except Exception as e:
            print(f"Error getting user character messages: {e}")
            return []

    def get_user_messages(self, user_id: int, limit: int = 20):
        """사용자의 모든 캐릭터와의 최근 대화 기록 조회"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT character_name, message_role, content, timestamp
                        FROM conversations 
                            WHERE user_id = %s
                        ORDER BY timestamp DESC 
                            LIMIT %s
                    ''', (user_id, limit))
                    messages = cursor.fetchall()
                    return [{
                        "character": character,
                        "role": role,
                        "content": content,
                        "timestamp": timestamp
                    } for character, role, content, timestamp in reversed(messages)]
        except Exception as e:
            print(f"Error getting user messages: {e}")
            return []

    async def get_user_message_count(self, user_id: int) -> int:
        """사용자의 총 대화 수를 가져옵니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT COUNT(*) 
                        FROM conversations 
                            WHERE user_id = %s AND message_role = 'user'
                    ''', (user_id,))
                    result = cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            print(f"Error getting user message count: {e}")
            return 0

    async def get_last_milestone(self, user_id: int) -> int:
        """사용자의 마지막 달성 마일스톤을 가져옵니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT last_milestone 
                        FROM conversation_count 
                            WHERE user_id = %s
                    ''', (user_id,))
                    result = cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            print(f"Error getting last milestone: {e}")
            return 0

    async def update_last_milestone(self, user_id: int, milestone: int) -> bool:
        """사용자의 마지막 달성 마일스톤을 업데이트합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO conversation_count 
                        (user_id, message_count, last_milestone)
                            VALUES (%s,
                            COALESCE(
                                (SELECT COUNT(*) 
                                FROM conversations 
                                        WHERE user_id = %s AND message_role = 'user'),
                                0
                            ),
                                    %s)
                        ON CONFLICT (user_id) DO UPDATE 
                        SET message_count = EXCLUDED.message_count,
                            last_milestone = EXCLUDED.last_milestone
                    ''', (user_id, user_id, milestone))
                    conn.commit()
                return True
        except Exception as e:
            print(f"Error updating last milestone: {e}")
            return False

    async def get_milestone_info(self, message_count: int) -> dict:
        """대화 횟수에 따른 마일스톤 정보를 조회합니다."""
        try:
            # 마일스톤 기준값 정의
            milestones = {
                10: {"title": "Rookie", "description": "첫 10회 대화 달성!", "color": "blue"},
                50: {"title": "Iron", "description": "50회 대화 달성!", "color": "gray"},
                100: {"title": "Silver", "description": "100회 대화 달성!", "color": "silver"},
                200: {"title": "Gold", "description": "200회 대화 달성!", "color": "gold"}
            }

            # 현재 대화 수보다 작거나 같은 마일스톤 중 가장 큰 것을 찾음
            available_milestones = [m for m in sorted(milestones.keys()) if message_count >= m]
            if available_milestones:
                milestone = max(available_milestones)
                return milestones[milestone]
            return None
        except Exception as e:
            print(f"Error getting milestone info: {e}")
            return None

    async def get_next_milestone(self, current_count: int) -> int:
        """다음 마일스톤을 조회합니다."""
        try:
            # 마일스톤 기준값 정의
            milestones = [10, 50, 100, 200]

            # 현재 대화 수보다 큰 마일스톤 중 가장 작은 것을 찾음
            next_milestones = [m for m in milestones if m > current_count]
            return min(next_milestones) if next_milestones else None
        except Exception as e:
            print(f"Error getting next milestone: {e}")
            return None

    async def check_and_update_milestone(self, user_id: int, milestone: int) -> bool:
        """
        사용자가 특정 마일스톤을 달성했는지 확인하고 업데이트
        """
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    # 마일스톤 테이블이 없으면 생성
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS user_milestones (
                                    user_id BIGINT,
                            milestone INTEGER,
                            achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (user_id, milestone)
                        )
                    ''')

                    # 이미 달성한 마일스톤인지 확인
                    cursor.execute(
                                'SELECT 1 FROM user_milestones WHERE user_id = %s AND milestone = %s',
                        (user_id, milestone)
                    )

                    if cursor.fetchone() is None:
                        # 새로운 마일스톤 달성 기록
                        cursor.execute(
                                    'INSERT INTO user_milestones (user_id, milestone) VALUES (%s, %s)',
                        (user_id, milestone)
                    )
                        conn.commit()
                        return True

                    return False

        except Exception as e:
            print(f"마일스톤 체크/업데이트 중 오류: {e}")
            return False

    async def check_and_add_card(self, user_id: int, character_name: str, milestone: int) -> bool:
        """
        사용자에게 새로운 캐릭터 카드 지급
        """
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    # 카드 테이블이 없으면 생성
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS user_cards (
                                    user_id BIGINT,
                            character_name TEXT,
                            milestone INTEGER,
                            acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (user_id, character_name, milestone)
                        )
                    ''')

                    # 이미 획득한 카드인지 확인
                    cursor.execute(
                                'SELECT 1 FROM user_cards WHERE user_id = %s AND character_name = %s AND milestone = %s',
                        (user_id, character_name, milestone)
                    )

                    if cursor.fetchone() is None:
                        # 새로운 카드 지급 기록
                        cursor.execute(
                                    'INSERT INTO user_cards (user_id, character_name, milestone) VALUES (%s, %s, %s)',
                        (user_id, character_name, milestone)
                    )
                        conn.commit()
                        return True

                    return False

        except Exception as e:
            print(f"카드 체크/추가 중 오류: {e}")
            return False

    def get_character_ranking(self, character_name: str) -> list:
        """캐릭터별 친밀도 랭킹을 가져옵니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT a.user_id, a.emotion_score, 
                               COALESCE(cc.message_count, 0) as message_count
                        FROM affinity a
                        LEFT JOIN conversation_count cc ON a.user_id = cc.user_id 
                            AND a.character_name = cc.character_name
                            WHERE a.character_name = %s
                        ORDER BY a.emotion_score DESC, message_count DESC
                        LIMIT 10
                    ''', (character_name,))
                    return cursor.fetchall()
        except Exception as e:
            print(f"Error getting character ranking: {e}")
            return []

    def get_total_ranking(self) -> list:
        """모든 캐릭터의 통합 친밀도와 대화 횟수 랭킹을 조회합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT a.user_id, 
                               COALESCE(a.total_emotion, 0) as total_emotion,
                               COALESCE(m.total_messages, 0) as total_messages
                        FROM (
                            SELECT user_id, SUM(emotion_score) as total_emotion
                            FROM affinity
                            GROUP BY user_id
                        ) a
                        LEFT JOIN (
                            SELECT user_id, COUNT(*) as total_messages
                            FROM conversations
                            WHERE message_role = 'user'
                            GROUP BY user_id
                        ) m ON a.user_id = m.user_id

                        UNION

                        SELECT m.user_id, 
                               COALESCE(a.total_affinity, 0) as total_affinity,
                               COALESCE(m.total_messages, 0) as total_messages
                        FROM (
                            SELECT user_id, COUNT(*) as total_messages
                            FROM conversations
                            WHERE message_role = 'user'
                            GROUP BY user_id
                        ) m
                        LEFT JOIN (
                            SELECT user_id, SUM(emotion_score) as total_emotion
                            FROM affinity
                            GROUP BY user_id
                        ) a ON m.user_id = a.user_id

                        ORDER BY total_emotion DESC, total_messages DESC
                        LIMIT 10
                    ''')
                    return cursor.fetchall()
        except Exception as e:
            print(f"Error getting total ranking: {e}")
            return []

    def get_user_character_rank(self, user_id: int, character_name: str) -> int:
        """특정 캐릭터에 대한 사용자의 순위를 조회합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        WITH CharacterMessages AS (
                            SELECT 
                                user_id,
                                COUNT(*) as message_count
                            FROM conversations
                                WHERE character_name = %s 
                            AND message_role = 'user'
                            GROUP BY user_id
                        ),
                        CharacterAffinity AS (
                            SELECT 
                                user_id,
                                emotion_score
                            FROM affinity
                                WHERE character_name = %s
                        ),
                        RankedUsers AS (
                            SELECT 
                                COALESCE(a.user_id, m.user_id) as user_id,
                                ROW_NUMBER() OVER (
                                    ORDER BY COALESCE(a.emotion_score, 0) DESC,
                                    COALESCE(m.message_count, 0) DESC
                                ) as rank
                            FROM CharacterAffinity a
                            FULL OUTER JOIN CharacterMessages m ON a.user_id = m.user_id
                            WHERE COALESCE(a.emotion_score, 0) > 0 OR COALESCE(m.message_count, 0) > 0
                        )
                        SELECT rank 
                        FROM RankedUsers 
                            WHERE user_id = %s
                    ''', (character_name, character_name, user_id))
                    result = cursor.fetchone()
                    return result[0] if result else 999999
        except Exception as e:
            print(f"Error getting user character rank: {e}")
            return 999999

    def get_user_total_rank(self, user_id: int) -> int:
        """모든 캐릭터 통합 순위에서 사용자의 순위를 조회합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        WITH TotalMessages AS (
                            SELECT 
                                user_id,
                                COUNT(*) as total_messages
                            FROM conversations
                            WHERE message_role = 'user'
                            GROUP BY user_id
                        ),
                        TotalAffinity AS (
                            SELECT 
                                user_id,
                                SUM(emotion_score) as total_emotion
                            FROM affinity
                            GROUP BY user_id
                        ),
                        RankedUsers AS (
                            SELECT 
                                COALESCE(a.user_id, m.user_id) as user_id,
                                ROW_NUMBER() OVER (
                                    ORDER BY COALESCE(a.total_emotion, 0) DESC,
                                    COALESCE(m.total_messages, 0) DESC
                                ) as rank
                            FROM TotalAffinity a
                            FULL OUTER JOIN TotalMessages m ON a.user_id = m.user_id
                            WHERE COALESCE(a.total_emotion, 0) > 0 OR COALESCE(m.total_messages, 0) > 0
                        )
                        SELECT rank 
                        FROM RankedUsers 
                            WHERE user_id = %s
                    ''', (user_id,))
                    result = cursor.fetchone()
                    return result[0] if result else 999999
        except Exception as e:
            print(f"Error getting user total rank: {e}")
            return 999999

    def get_user_stats(self, user_id: int, character_name: str = None) -> dict:
        """사용자의 친밀도와 대화 횟수 통계를 조회합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    if character_name:
                        # 특정 캐릭터에 대한 통계
                        cursor.execute('''
                            WITH CharacterMessages AS (
                                SELECT COUNT(*) as message_count
                                FROM conversations
                                    WHERE user_id = %s
                                    AND character_name = %s
                                AND message_role = 'user'
                            ),
                            CharacterAffinity AS (
                                SELECT emotion_score
                                FROM affinity
                                    WHERE user_id = %s
                                    AND character_name = %s
                            )
                            SELECT 
                                COALESCE(a.emotion_score, 0) as emotion_score,
                                COALESCE(m.message_count, 0) as message_count
                            FROM CharacterAffinity a
                            CROSS JOIN CharacterMessages m
                        ''', (user_id, character_name, user_id, character_name))
                    else:
                        # 전체 통계
                        cursor.execute('''
                            WITH TotalMessages AS (
                                SELECT COUNT(*) as message_count
                        FROM conversations 
                                    WHERE user_id = %s
                        AND message_role = 'user'
                            ),
                            TotalAffinity AS (
                                SELECT SUM(emotion_score) as total_emotion
                                FROM affinity
                                    WHERE user_id = %s
                            )
                            SELECT 
                                COALESCE(a.total_emotion, 0) as total_emotion,
                                COALESCE(m.message_count, 0) as total_messages
                            FROM TotalAffinity a
                            CROSS JOIN TotalMessages m
                        ''', (user_id, user_id))

                    result = cursor.fetchone()
                    return {
                        'affinity': result[0] if result and result[0] is not None else 0,
                        'messages': result[1] if result and result[1] is not None else 0
                    }
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {'affinity': 0, 'messages': 0}

    def get_user_card_count(self, user_id: int, character_name: str) -> dict:
        """사용자의 카드 수집 현황 조회"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT 
                            SUM(CASE WHEN card_id LIKE 'C%' THEN 1 ELSE 0 END) as c_count,
                            SUM(CASE WHEN card_id LIKE 'B%' THEN 1 ELSE 0 END) as b_count,
                            SUM(CASE WHEN card_id LIKE 'A%' THEN 1 ELSE 0 END) as a_count,
                            SUM(CASE WHEN card_id LIKE 'S%' THEN 1 ELSE 0 END) as s_count,
                            SUM(CASE WHEN card_id LIKE 'Special%' THEN 1 ELSE 0 END) as special_count
                        FROM user_cards
                            WHERE user_id = %s AND character_name = %s
                    ''', (user_id, character_name))

                    result = cursor.fetchone()
                    return {
                        'C': result[0] or 0,
                        'B': result[1] or 0,
                        'A': result[2] or 0,
                        'S': result[3] or 0,
                        'Special': result[4] or 0
                    }
        except Exception as e:
            print(f"Error getting user card count: {e}")
            return {'C': 0, 'B': 0, 'A': 0, 'S': 0, 'Special': 0}

    def get_story_progress(self, user_id: int, character_name: str, story_id: str) -> dict:
        """스토리 진행 상태 조회"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT current_step, completed, started_at, completed_at
                        FROM story_progress
                            WHERE user_id = %s AND character_name = %s AND story_id = %s
                    ''', (user_id, character_name, story_id))
                    result = cursor.fetchone()
                    if result:
                        return {
                            'current_step': result[0],
                            'completed': bool(result[1]),
                            'started_at': result[2],
                            'completed_at': result[3]
                        }
                    return None
        except Exception as e:
            print(f"Error in get_story_progress: {e}")
            return None

    def start_story(self, user_id: int, character_name: str, chapter_number: int) -> bool:
        """새로운 스토리 시작"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO story_progress 
                        (user_id, character_name, chapter_number, completed_at, selected_choice, ending_type)
                        VALUES (%s, %s, %s, NULL, NULL, NULL)
                        ON CONFLICT (user_id, character_name, chapter_number) 
                        DO NOTHING
                    ''', (user_id, character_name, chapter_number))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error in start_story: {e}")
            return False

    def update_story_progress(self, user_id: int, character_name: str, chapter_number: int, step: int, selected_choice: str = None, ending_type: str = None, completed: bool = False) -> bool:
        """스토리 진행 상태 업데이트"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    if completed:
                        cursor.execute('''
                            UPDATE story_progress
                                SET current_step = %s, completed = TRUE, completed_at = CURRENT_TIMESTAMP,
                                    selected_choice = %s, ending_type = %s
                                WHERE user_id = %s AND character_name = %s AND chapter_number = %s
                        ''', (step, selected_choice, ending_type, user_id, character_name, chapter_number))
                    else:
                        cursor.execute('''
                            UPDATE story_progress
                                SET current_step = %s
                                WHERE user_id = %s AND character_name = %s AND chapter_number = %s
                        ''', (step, user_id, character_name, chapter_number))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error in update_story_progress: {e}")
            return False

    def save_story_choice(self, user_id: int, character_name: str, story_id: str, choice_index: int, choice_text: str) -> bool:
        """스토리 선택지 저장"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO story_choices 
                        (user_id, character_name, story_id, choice_index, choice_text)
                            VALUES (%s, %s, %s, %s, %s)
                    ''', (user_id, character_name, story_id, choice_index, choice_text))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error in save_story_choice: {e}")
            return False

    def get_completed_stories(self, user_id: int, character_name: str) -> list:
        """완료된 스토리 목록 조회"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT story_id, completed_at
                        FROM story_progress
                            WHERE user_id = %s AND character_name = %s AND completed = TRUE
                        ORDER BY completed_at DESC
                    ''', (user_id, character_name))
                    return cursor.fetchall()
        except Exception as e:
            print(f"Error in get_completed_stories: {e}")
            return []

    def save_scene_score(self, user_id: int, character_name: str, chapter_id: int, scene_id: int, score: int):
        """씬 점수를 저장합니다."""
        query = """
        INSERT INTO scene_scores (user_id, character_name, chapter_id, scene_id, score)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT(user_id, character_name, chapter_id, scene_id) 
        DO UPDATE SET score = excluded.score
        """
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (user_id, character_name, chapter_id, scene_id, score))
                conn.commit()

    def get_scene_score(self, user_id: int, character_name: str, chapter_id: int, scene_id: int) -> int:
        """씬 점수를 가져옵니다."""
        query = """
        SELECT score FROM scene_scores
        WHERE user_id = %s AND character_name = %s AND chapter_id = %s AND scene_id = %s
        """
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (user_id, character_name, chapter_id, scene_id))
                result = cursor.fetchone()
        return result[0] if result else 0

    def get_completed_chapters(self, user_id: int, character_name: str) -> list:
        """사용자가 완료한 챕터 목록을 반환합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT chapter_id
                        FROM completed_chapters
                            WHERE user_id = %s AND character_name = %s
                        ORDER BY chapter_id
                    ''', (user_id, character_name))
                    results = cursor.fetchall()
                    return [row[0] for row in results]
        except Exception as e:
            print(f"Error getting completed chapters: {e}")
            return []

    def add_completed_chapter(self, user_id: int, character_name: str, chapter_id: int) -> bool:
        """사용자가 완료한 챕터를 추가합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO completed_chapters
                        (user_id, character_name, chapter_id, completed_at)
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id, character_name, chapter_id) DO NOTHING
                    ''', (user_id, character_name, chapter_id))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error in add_completed_chapter: {e}")
            return False

    def has_claimed_milestone(self, user_id, character_name, milestone):
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM user_milestone_claims WHERE user_id=%s AND character_name=%s AND milestone=%s",
            (user_id, character_name, milestone)
        )
        result = cur.fetchone()
        conn.close()
        return result is not None

    def set_claimed_milestone(self, user_id, character_name, milestone):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO user_milestone_claims (user_id, character_name, milestone, claimed_at) 
                    VALUES (%s, %s, %s, %s) 
                    ON CONFLICT (user_id, character_name, milestone) DO NOTHING
                ''', (user_id, character_name, milestone, datetime.now()))
                conn.commit()

    def get_last_claimed_milestone(self, user_id, character_name):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                        "SELECT MAX(milestone) FROM user_milestone_claims WHERE user_id=%s AND character_name=%s",
                    (user_id, character_name)
                )
                result = cursor.fetchone()
                return result[0] if result and result[0] else 0

    def has_levelup_flag(self, user_id, character_name, level):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                        "SELECT 1 FROM user_levelup_flags WHERE user_id=%s AND character_name=%s AND level=%s",
                    (user_id, character_name, level)
                )
                return cursor.fetchone() is not None

    def set_levelup_flag(self, user_id, character_name, level):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO user_levelup_flags (user_id, character_name, level) 
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, character_name, level) DO NOTHING
                ''', (user_id, character_name, level))
                conn.commit()

    def set_affinity(self, user_id: int, character_name: str, value: int) -> bool:
        """관리자: 유저의 친밀도 점수를 직접 세팅합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO affinity (user_id, character_name, emotion_score, daily_message_count, last_daily_reset)
                            VALUES (%s, %s, %s, 0, CURRENT_DATE)
                        ON CONFLICT (user_id, character_name) 
                        DO UPDATE SET 
                            emotion_score = EXCLUDED.emotion_score,
                            daily_message_count = EXCLUDED.daily_message_count,
                            last_daily_reset = EXCLUDED.last_daily_reset
                    ''', (user_id, character_name, value))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error in set_affinity: {e}")
            return False

    def add_user_message_count(self, user_id: int, character_name: str, count: int) -> bool:
        """관리자: 유저의 메시지 수를 수동으로 추가합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    # affinity 테이블의 daily_message_count 증가
                    cursor.execute('''
                        UPDATE affinity
                            SET daily_message_count = COALESCE(daily_message_count, 0) + %s
                            WHERE user_id = %s AND character_name = %s
                    ''', (count, user_id, character_name))
                    if cursor.rowcount == 0:
                        # affinity row가 없으면 새로 생성
                        cursor.execute('''
                            INSERT INTO affinity (user_id, character_name, emotion_score, daily_message_count, last_daily_reset)
                                VALUES (%s, %s, 0, %s, CURRENT_DATE)
                        ''', (user_id, character_name, count))
                    conn.commit()
                    return True
        except Exception as e:
            print(f"Error in add_user_message_count: {e}")
            return False

    def increment_card_issued_number(self, character_name: str, card_id: str) -> int:
        """카드 지급 시 전체 발급 순번을 1 증가시키고, 증가된 값을 반환합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    # 정확히 일치하는 카드만 처리
                    cursor.execute('''
                        SELECT issued_number FROM card_issued
                            WHERE character_name = %s AND card_id = %s
                    ''', (character_name, card_id))
                    result = cursor.fetchone()
                    if result:
                        new_number = result[0] + 1
                        if new_number > 10000:
                            print(f"Warning: Card number limit reached for {character_name} {card_id}")
                            return 10000
                        cursor.execute('''
                                UPDATE card_issued SET issued_number = %s
                                WHERE character_name = %s AND card_id = %s
                        ''', (new_number, character_name, card_id))
                    else:
                        new_number = 1
                        cursor.execute('''
                            INSERT INTO card_issued (character_name, card_id, issued_number)
                                VALUES (%s, %s, %s)
                        ''', (character_name, card_id, new_number))
                    conn.commit()
                    return new_number
        except Exception as e:
            print(f"Error incrementing card issued number: {e}")
            return 1

    def get_card_issued_number(self, character_name: str, card_id: str) -> int:
        """해당 카드의 전체 서버 기준 발급 순번을 반환합니다."""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT issued_number FROM card_issued
                            WHERE character_name = %s AND card_id = %s
                    ''', (character_name, card_id))
                    result = cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            print(f"Error getting card issued number: {e}")
            return 0

    def log_emotion_score(self, user_id: int, character_name: str, score: int, message: str):
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO emotion_log (user_id, character_name, score, message)
                        VALUES (%s, %s, %s, %s)
                ''', (user_id, character_name, score, message))
            conn.commit()

    def get_connection(self):
        return psycopg2.connect(DATABASE_URL) 