import json
from datetime import datetime, timedelta
import os
import psycopg2
from database_manager import DATABASE_URL

class IntimacyManager:
    def __init__(self):
        self.data_file = "intimacy_data.json"
        self.data = self.load_data()
        self.last_messages = {}  # {user_id: [timestamp, content]}
        self.daily_message_counts = {}  # {user_id: {"count": int, "last_reset": str}}
        self.message_cooldowns = {}  # {user_id: timestamp}
        self.cooldown_time = 3  # seconds
        self.max_daily_messages = 50

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"users": {}}
        return {"users": {}}

    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_user_data(self, user_id):
        str_user_id = str(user_id)
        if str_user_id not in self.data["users"]:
            self.data["users"][str_user_id] = {}
        return self.data["users"][str_user_id]

    def get_character_data(self, user_id, character_name):
        user_data = self.get_user_data(user_id)
        if character_name not in user_data:
            user_data[character_name] = {
                "intimacy": 0,
                "total_messages": 0,
                "last_interaction": None
            }
        return user_data[character_name]

    def add_message_point(self, user_id, character_name):
        user_data = self.get_user_data(user_id)
        char_data = self.get_character_data(user_id, character_name)
        
        # Update message counts
        user_data["total_messages"] += 1
        char_data["total_messages"] += 1
        
        # Update intimacy
        char_data["intimacy"] += 1
        char_data["last_interaction"] = datetime.now().isoformat()
        
        self.save_data()

    def get_intimacy_level(self, user_id, character_name):
        char_data = self.get_character_data(user_id, character_name)
        intimacy = char_data["intimacy"]
        
        if intimacy >= 100:
            return 3  # 최고 레벨
        elif intimacy >= 50:
            return 2
        elif intimacy >= 20:
            return 1
        return 0

    def get_ranking(self, character_name=None):
        """친밀도 랭킹 조회"""
        try:
            with psycopg2.connect(DATABASE_URL) as conn:
                cursor = conn.cursor()
                if character_name:
                    cursor.execute('''
                        SELECT user_id, emotion_score, message_count
                        FROM conversations
                        WHERE character_name = %s
                        ORDER BY emotion_score DESC
                    ''', (character_name,))
                else:
                    cursor.execute('''
                        SELECT user_id, 
                               SUM(emotion_score) as total_score,
                               SUM(message_count) as total_messages
                        FROM conversations
                        GROUP BY user_id
                        ORDER BY total_score DESC
                    ''')
                
                rankings = []
                for row in cursor.fetchall():
                    rankings.append({
                        "user_id": row[0],
                        "intimacy": row[1],
                        "total_messages": row[2]
                    })
                return rankings
        except Exception as e:
            print(f"Error getting ranking: {e}")
            return []

    def is_spam(self, user_id, message_content):
        current_time = datetime.now()
        
        if user_id in self.last_messages:
            last_time, last_content = self.last_messages[user_id]
            time_diff = (current_time - last_time).total_seconds()
            
            # 3초 이내에 동일한 메시지를 보내면 스팸으로 간주
            if time_diff < 3 and message_content == last_content:
                return True
        
        self.last_messages[user_id] = (current_time, message_content)
        return False

    def can_send_message(self, user_id):
        current_time = datetime.now()
        str_user_id = str(user_id)

        # 쿨다운 체크
        if user_id in self.message_cooldowns:
            cooldown_end = self.message_cooldowns[user_id]
            if current_time < cooldown_end:
                return False

        # 일일 메시지 제한 체크
        if str_user_id in self.daily_message_counts:
            count_data = self.daily_message_counts[str_user_id]
            last_reset = datetime.strptime(count_data["last_reset"], "%Y-%m-%d").date()
            
            if last_reset < current_time.date():
                # 새로운 날짜면 카운트 리셋
                count_data = {
                    "count": 1,
                    "last_reset": current_time.date().isoformat()
                }
            elif count_data["count"] >= self.max_daily_messages:
                return False
            else:
                count_data["count"] += 1
        else:
            count_data = {
                "count": 1,
                "last_reset": current_time.date().isoformat()
            }

        self.daily_message_counts[str_user_id] = count_data
        self.message_cooldowns[user_id] = current_time + timedelta(seconds=self.cooldown_time)
        return True

    def add_gift_points(self, user_id, character_name, amount=30):
        """기프팅/후원 포인트 추가"""
        self.get_user_data(user_id)
        self.get_character_data(user_id, character_name)
        self.data["users"][str(user_id)][character_name]["intimacy"] += amount
        self.save_data()
        return self.data["users"][str(user_id)][character_name]["intimacy"]

    def get_intimacy_level(self, user_id, character_name):
        """친밀도 레벨 확인"""
        self.get_character_data(user_id, character_name)
        intimacy = self.data["users"][str(user_id)][character_name]["intimacy"]
        if intimacy >= 30:
            return 3
        elif intimacy >= 20:
            return 2
        elif intimacy >= 10:
            return 1
        return 0

    def get_ranking(self, character_name=None):
        """친밀도 랭킹 조회"""
        rankings = []
        for user_id, user_data in self.data["users"].items():
            if character_name:
                if character_name in user_data:
                    rankings.append({
                        "user_id": user_id,
                        "intimacy": user_data[character_name]["intimacy"],
                        "total_messages": user_data[character_name]["total_messages"]
                    })
            else:
                total_intimacy = sum(char_data["intimacy"] for char_data in user_data.values())
                total_messages = sum(char_data["total_messages"] for char_data in user_data.values())
                rankings.append({
                    "user_id": user_id,
                    "intimacy": total_intimacy,
                    "total_messages": total_messages
                })
        
        return sorted(rankings, key=lambda x: x["intimacy"], reverse=True) 