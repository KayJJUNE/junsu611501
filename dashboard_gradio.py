import gradio as gr
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
from sqlalchemy import create_engine
import os

# PostgreSQL 연결 문자열
DATABASE_URL = "postgresql://postgres:HOOcjansZSDZvFtGcNfNCQUjtpBPbZck@switchback.proxy.rlwy.net:44316/railway"
engine = create_engine(DATABASE_URL)

def create_tables():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # conversations 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                character_name VARCHAR(64) NOT NULL,
                message_role VARCHAR(16) NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                token_count INTEGER
            )
        """)
        
        # affinity 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS affinity (
                user_id VARCHAR(64) NOT NULL,
                character_name VARCHAR(64) NOT NULL,
                emotion_score INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, character_name)
            )
        """)
        
        # user_cards 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_cards (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                character_name VARCHAR(64) NOT NULL,
                card_id VARCHAR(16) NOT NULL,
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, card_id)
            )
        """)
        
        # story_progress 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS story_progress (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                character_name VARCHAR(64) NOT NULL,
                chapter_number INTEGER NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                selected_choice TEXT,
                ending_type VARCHAR(16),
                UNIQUE(user_id, character_name, chapter_number)
            )
        """)
        
        # emotion_log 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emotion_log (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                character_name VARCHAR(64) NOT NULL,
                message TEXT NOT NULL,
                score INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # conversation_count 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_count (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                character_name VARCHAR(64) NOT NULL,
                message_count INTEGER DEFAULT 0,
                UNIQUE(user_id, character_name)
            )
        """)
        
        conn.commit()
        print("테이블이 성공적으로 생성되었습니다.")
    except Exception as e:
        print(f"테이블 생성 중 오류 발생: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 프로그램 시작 시 테이블 생성
create_tables()

def get_user_cards():
    df = pd.read_sql_query("""
        SELECT user_id, character_name, card_id, obtained_at
        FROM user_cards
        ORDER BY obtained_at DESC
    """, engine)
    return df

def get_user_info():
    df = pd.read_sql_query("""
        SELECT a.user_id, a.character_name, a.emotion_score, c.message_count
        FROM affinity a
        LEFT JOIN (
            SELECT user_id, character_name, SUM(message_count) as message_count
            FROM conversation_count
            GROUP BY user_id, character_name
        ) c ON a.user_id = c.user_id AND a.character_name = c.character_name
    """, engine)
    return df

def get_user_summary(user_id):
    conn = psycopg2.connect(DATABASE_URL)
    # 유저 기본 정보
    total_msgs = pd.read_sql_query("""
        SELECT COUNT(*) as total_messages
        FROM conversations
        WHERE user_id = %s AND message_role = 'user'
    """, conn, params=(user_id,))
    user_info = pd.read_sql_query("""
        SELECT
            %s as user_id,
            MIN(timestamp) as joined_at,
            MAX(timestamp) as last_message_time,
            (SELECT content FROM conversations WHERE user_id = %s ORDER BY timestamp ASC LIMIT 1) as first_message_content,
            (SELECT content FROM conversations WHERE user_id = %s ORDER BY timestamp DESC LIMIT 1) as last_message_content,
            SUM(CASE WHEN message_role='user' THEN 1 ELSE 0 END) as total_messages
        FROM conversations
        WHERE user_id = %s
    """, conn, params=(user_id, user_id, user_id, user_id))
    # 친밀도 등급
    affinity = pd.read_sql_query("""
        SELECT character_name, emotion_score
        FROM affinity
        WHERE user_id = %s
    """, conn, params=(user_id,))
    # 카드 정보
    cards = pd.read_sql_query("""
        SELECT card_id, character_name, obtained_at
        FROM user_cards
        WHERE user_id = %s
        ORDER BY obtained_at DESC
    """, conn, params=(user_id,))
    # 카드 등급 비율
    card_tiers = pd.read_sql_query("""
        SELECT
            SUBSTRING(card_id, 1, 1) as tier,
            COUNT(*) as count
        FROM user_cards
        WHERE user_id = %s
        GROUP BY tier
    """, conn, params=(user_id,))
    # 캐릭터별 카드 분류
    char_cards = pd.read_sql_query("""
        SELECT character_name, COUNT(*) as count
        FROM user_cards
        WHERE user_id = %s
        GROUP BY character_name
    """, conn, params=(user_id,))
    # 최근 획득 카드
    recent_card = cards.head(1)
    # 주간 활동량
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    week_msgs = pd.read_sql_query("""
        SELECT COUNT(*) as week_messages
        FROM conversations
        WHERE user_id = %s AND timestamp >= %s AND message_role = 'user'
    """, conn, params=(user_id, week_ago))
    week_cards = pd.read_sql_query("""
        SELECT COUNT(*) as week_cards
        FROM user_cards
        WHERE user_id = %s AND obtained_at >= %s
    """, conn, params=(user_id, week_ago))
    # 스토리 진행 현황
    story_progress = get_user_story_progress(user_id)
    conn.close()
    # 결과 딕셔너리로 반환
    return {
        "기본 정보": user_info,
        "친밀도": affinity,
        "카드 목록": cards,
        "카드 등급 비율": card_tiers,
        "캐릭터별 카드 분류": char_cards,
        "최근 획득 카드": recent_card,
        "주간 대화 수": week_msgs,
        "주간 카드 획득": week_cards,
        "스토리 진행 현황": story_progress
    }

def user_dashboard(user_id):
    info = get_user_summary(user_id)
    emotion_summary = get_emotion_score_summary(user_id)
    return (
        info["기본 정보"],
        info["친밀도"],
        info["카드 목록"],
        info["카드 등급 비율"],
        info["캐릭터별 카드 분류"],
        info["최근 획득 카드"],
        info["주간 대화 수"],
        info["주간 카드 획득"],
        info["스토리 진행 현황"],
        emotion_summary
    )

def get_dashboard_stats():
    conn = psycopg2.connect(DATABASE_URL)
    # 1. 총 유저 메시지 수
    total_user_messages = pd.read_sql_query(
        "SELECT COUNT(*) as total_user_messages FROM conversations WHERE LOWER(message_role)='user';", conn
    )["total_user_messages"][0]
    # 2. 챗봇 총 친밀도 점수
    total_affinity = pd.read_sql_query(
        "SELECT SUM(emotion_score) as total_affinity FROM affinity;", conn
    )["total_affinity"][0]
    # 3. 총 대화한 유저 수
    total_users = pd.read_sql_query(
        "SELECT COUNT(DISTINCT user_id) as total_users FROM conversations WHERE message_role = 'user';", conn
    )["total_users"][0]
    # 4. 오늘 대화한 유저 수
    today_users = pd.read_sql_query(
        "SELECT COUNT(DISTINCT user_id) as today_users FROM conversations WHERE message_role = 'user' AND DATE(timestamp) = CURRENT_DATE;", conn
    )["today_users"][0]
    # 5. OpenAI 토큰 소비량
    try:
        total_tokens = pd.read_sql_query(
            "SELECT SUM(token_count) as total_tokens FROM conversations WHERE message_role='assistant';", conn
        )["total_tokens"][0]
        if total_tokens is None:
            total_tokens = 0
    except Exception:
        total_tokens = 0
    # 6. 카드 등급별 출하량 및 백분율
    card_tiers = pd.read_sql_query(
        "SELECT SUBSTRING(card_id, 1, 1) as tier, COUNT(*) as count FROM user_cards GROUP BY tier;", conn
    )
    total_cards = card_tiers["count"].sum()
    card_tiers["percent"] = (card_tiers["count"] / total_cards * 100).round(2).astype(str) + "%"
    # 7. 레벨 통계 추가
    level_stats = get_level_statistics()
    conn.close()
    return {
        "총 유저 메시지 수": total_user_messages,
        "총 친밀도 점수": total_affinity,
        "총 대화한 유저 수": total_users,
        "오늘 대화한 유저 수": today_users,
        "OpenAI 토큰 소비량": f"{total_tokens:,} 토큰",
        "카드 등급별 출하량": card_tiers,
        "레벨별 현황": level_stats
    }

def show_dashboard_stats():
    stats = get_dashboard_stats()
    return (
        f"총 유저 메시지 수: {stats['총 유저 메시지 수']}",
        f"총 친밀도 점수: {stats['총 친밀도 점수']}",
        f"총 대화한 유저 수: {stats['총 대화한 유저 수']}",
        f"오늘 대화한 유저 수: {stats['오늘 대화한 유저 수']}",
        f"OpenAI 토큰 소비량: {stats['OpenAI 토큰 소비량']}",
        stats["카드 등급별 출하량"],
        stats["레벨별 현황"]
    )

def get_full_character_ranking(character_name):
    conn = psycopg2.connect(DATABASE_URL)
    df = pd.read_sql_query('''
        SELECT a.user_id, a.emotion_score, 
               COALESCE(m.message_count, 0) as message_count
        FROM affinity a
        LEFT JOIN (
            SELECT user_id, character_name, COUNT(*) as message_count
            FROM conversations
            WHERE message_role = 'user'
            GROUP BY user_id, character_name
        ) m ON a.user_id = m.user_id AND a.character_name = m.character_name
        WHERE a.character_name = %s
        ORDER BY a.emotion_score DESC, message_count DESC
    ''', conn, params=(character_name,))
    conn.close()
    return df

def get_full_total_ranking():
    conn = psycopg2.connect(DATABASE_URL)
    df = pd.read_sql_query('''
        SELECT a.user_id, COALESCE(a.total_affinity, 0) as total_affinity, COALESCE(m.total_messages, 0) as total_messages
        FROM (
            SELECT user_id, SUM(emotion_score) as total_affinity
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
        SELECT m.user_id, COALESCE(a.total_affinity, 0) as total_affinity, COALESCE(m.total_messages, 0) as total_messages
        FROM (
            SELECT user_id, COUNT(*) as total_messages
            FROM conversations
            WHERE message_role = 'user'
            GROUP BY user_id
        ) m
        LEFT JOIN (
            SELECT user_id, SUM(emotion_score) as total_affinity
            FROM affinity
            GROUP BY user_id
        ) a ON m.user_id = a.user_id
        ORDER BY total_affinity DESC, total_messages DESC
    ''', conn)
    conn.close()
    return df

def show_all_rankings():
    kagari = get_full_character_ranking("Kagari")
    eros = get_full_character_ranking("Eros")
    elysia = get_full_character_ranking("Elysia")
    total = get_full_total_ranking()
    return kagari, eros, elysia, total

def get_level_statistics():
    conn = psycopg2.connect(DATABASE_URL)
    total_users = pd.read_sql_query("""
        SELECT COUNT(DISTINCT user_id) as total_users
        FROM affinity
    """, conn)["total_users"][0]
    level_stats = pd.read_sql_query("""
        WITH user_levels AS (
            SELECT 
                user_id,
                CASE 
                    WHEN SUM(emotion_score) < 10 THEN 'Rookie'
                    WHEN SUM(emotion_score) < 50 THEN 'Iron'
                    WHEN SUM(emotion_score) < 100 THEN 'Silver'
                    ELSE 'Gold'
                END as level
            FROM affinity
            GROUP BY user_id
        )
        SELECT 
            level,
            COUNT(*) as user_count,
            ROUND(COUNT(*) * 100.0 / %s, 2) as percentage
        FROM user_levels
        GROUP BY level
        ORDER BY 
            CASE level
                WHEN 'Rookie' THEN 1
                WHEN 'Iron' THEN 2
                WHEN 'Silver' THEN 3
                WHEN 'Gold' THEN 4
            END
    """, conn, params=(int(total_users),))
    conn.close()
    return level_stats

def get_user_story_progress(user_id):
    conn = psycopg2.connect(DATABASE_URL)
    # 스토리 챕터 진행 현황
    chapter_progress = pd.read_sql_query("""
        SELECT 
            character_name,
            chapter_number,
            completed_at,
            selected_choice,
            ending_type
        FROM story_progress
        WHERE user_id = %s
        ORDER BY character_name, chapter_number
    """, conn, params=(user_id,))
    conn.close()
    return chapter_progress

def get_all_story_progress():
    conn = psycopg2.connect(DATABASE_URL)
    # 전체 스토리 진행 현황
    story_stats = pd.read_sql_query("""
        SELECT 
            character_name,
            chapter_number,
            COUNT(DISTINCT user_id) as completed_users,
            COUNT(DISTINCT CASE WHEN ending_type = 'Good' THEN user_id END) as good_endings,
            COUNT(DISTINCT CASE WHEN ending_type = 'Bad' THEN user_id END) as bad_endings,
            COUNT(DISTINCT CASE WHEN ending_type = 'Normal' THEN user_id END) as normal_endings
        FROM story_progress
        GROUP BY character_name, chapter_number
        ORDER BY character_name, chapter_number
    """, conn)
    conn.close()
    return story_stats

def get_emotion_score_history(user_id, character_name=None):
    conn = psycopg2.connect(DATABASE_URL)
    query = """
        SELECT 
            e.message,
            e.score,
            e.timestamp
        FROM emotion_log e
        WHERE e.user_id = %s
    """
    params = [user_id]

    if character_name:
        query += " AND e.character_name = %s"
        params.append(character_name)

    query += " ORDER BY e.timestamp DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_emotion_score_summary(user_id):
    conn = psycopg2.connect(DATABASE_URL)
    df = pd.read_sql_query("""
        SELECT 
            character_name,
            MAX(score) as current_score,
            COUNT(*) as total_interactions,
            AVG(score) as avg_score,
            MAX(timestamp) as last_interaction
        FROM emotion_log
        WHERE user_id = %s
        GROUP BY character_name
    """, conn, params=(user_id,))
    conn.close()
    return df

def get_user_cards(user_id):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT card_id, character_name, obtained_at FROM user_cards WHERE user_id = %s", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    # DataFrame으로 변환 (Gradio에서 표로 보기 좋음)
    df = pd.DataFrame(rows, columns=["card_id", "character_name", "obtained_at"])
    return df

def dashboard(user_id):
    df = get_user_cards(user_id)
    return df

def get_all_users_data():
    conn = psycopg2.connect(DATABASE_URL)
    # 1. 전체 통계
    total_stats = pd.read_sql_query("""
        SELECT 
            COUNT(*) as total_messages,
            COUNT(DISTINCT user_id) as total_users
        FROM conversations
        WHERE message_role = 'user'
    """, conn)

    # 2. 유저별 상세 정보 (가입일, ID, 캐릭터별 메시지/호감도, 토탈)
    user_details = pd.read_sql_query("""
        WITH first_msg AS (
            SELECT user_id, MIN(timestamp) as joined_at
            FROM conversations
            WHERE message_role = 'user'
            GROUP BY user_id
        ),
        msg_counts AS (
            SELECT user_id, character_name,
                   COUNT(*) as msg_count
            FROM conversations
            WHERE message_role = 'user'
            GROUP BY user_id, character_name
        ),
        affinity_scores AS (
            SELECT user_id, character_name, emotion_score
            FROM affinity
        ),
        total_msg AS (
            SELECT user_id, COUNT(*) as total_msg
            FROM conversations
            WHERE message_role = 'user'
            GROUP BY user_id
        ),
        total_affinity AS (
            SELECT user_id, SUM(emotion_score) as total_affinity
            FROM affinity
            GROUP BY user_id
        )
        SELECT
            f.user_id,
            f.joined_at,
            COALESCE(k.msg_count, 0) as kagari_messages,
            COALESCE(e.msg_count, 0) as eros_messages,
            COALESCE(l.msg_count, 0) as elysia_messages,
            COALESCE(ka.emotion_score, 0) as kagari_affinity,
            COALESCE(ea.emotion_score, 0) as eros_affinity,
            COALESCE(la.emotion_score, 0) as elysia_affinity,
            COALESCE(tm.total_msg, 0) as total_messages,
            COALESCE(ta.total_affinity, 0) as total_affinity
        FROM first_msg f
        LEFT JOIN msg_counts k ON f.user_id = k.user_id AND k.character_name = 'Kagari'
        LEFT JOIN msg_counts e ON f.user_id = e.user_id AND e.character_name = 'Eros'
        LEFT JOIN msg_counts l ON f.user_id = l.user_id AND l.character_name = 'Elysia'
        LEFT JOIN affinity_scores ka ON f.user_id = ka.user_id AND ka.character_name = 'Kagari'
        LEFT JOIN affinity_scores ea ON f.user_id = ea.user_id AND ea.character_name = 'Eros'
        LEFT JOIN affinity_scores la ON f.user_id = la.user_id AND la.character_name = 'Elysia'
        LEFT JOIN total_msg tm ON f.user_id = tm.user_id
        LEFT JOIN total_affinity ta ON f.user_id = ta.user_id
        ORDER BY f.joined_at DESC
    """, conn)

    # 3. 캐릭터별 랭킹
    rankings = pd.read_sql_query("""
        WITH user_stats AS (
            SELECT 
                user_id,
                character_name,
                emotion_score,
                COUNT(*) as message_count
            FROM conversations c
            LEFT JOIN affinity a ON c.user_id = a.user_id AND c.character_name = a.character_name
            WHERE message_role = 'user'
            GROUP BY user_id, character_name, emotion_score
        )
        SELECT 
            user_id,
            character_name,
            emotion_score,
            message_count,
            RANK() OVER (PARTITION BY character_name ORDER BY emotion_score DESC, message_count DESC) as rank
        FROM user_stats
        ORDER BY character_name, rank
    """, conn)

    conn.close()
    return {
        "total_stats": total_stats,
        "user_details": user_details,
        "rankings": rankings
    }

if __name__ == "__main__":
    with gr.Blocks(title="디스코드 챗봇 통합 대시보드") as demo:
        gr.Markdown("# 디스코드 챗봇 통합 대시보드")

        with gr.Tab("유저 검색"):
            gr.Markdown("## 유저 정보 검색")
            user_id = gr.Textbox(label="디스코드 유저 ID 입력", value="")
            btn = gr.Button("유저 정보 조회")
            out1 = gr.Dataframe(label="기본 정보")
            out2 = gr.Dataframe(label="캐릭터별 친밀도")
            out3 = gr.Dataframe(label="카드 목록")
            out4 = gr.Dataframe(label="카드 등급 비율")
            out5 = gr.Dataframe(label="캐릭터별 카드 분류")
            out6 = gr.Dataframe(label="최근 획득 카드")
            out7 = gr.Dataframe(label="주간 대화 수")
            out8 = gr.Dataframe(label="주간 카드 획득")
            out9 = gr.Dataframe(label="스토리 진행 현황")
            out10 = gr.Dataframe(label="감정 스코어 요약")
            btn.click(user_dashboard, inputs=user_id, outputs=[out1, out2, out3, out4, out5, out6, out7, out8, out9, out10])

        with gr.Tab("감정 스코어 기록"):
            gr.Markdown("## 감정 스코어 상세 기록")
            emotion_user_id = gr.Textbox(label="디스코드 유저 ID 입력", value="")
            character_select = gr.Dropdown(
                choices=["전체", "Kagari", "Eros", "Elysia"],
                value="전체",
                label="캐릭터 선택"
            )
            emotion_btn = gr.Button("감정 스코어 기록 조회")
            emotion_out = gr.Dataframe(
                label="감정 스코어 기록",
                headers=["대화 내용", "스코어 변경", "총 스코어", "시간"]
            )

            def show_emotion_history(user_id, character):
                if character == "전체":
                    return get_emotion_score_history(user_id)
                return get_emotion_score_history(user_id, character)

            emotion_btn.click(
                show_emotion_history,
                inputs=[emotion_user_id, character_select],
                outputs=emotion_out
            )

        with gr.Tab("전체 통계"):
            gr.Markdown("## 전체 통계 요약")
            stats_btn = gr.Button("전체 통계 새로고침")
            stats_out1 = gr.Textbox(label="총 유저 메시지 수")
            stats_out2 = gr.Textbox(label="총 친밀도 점수")
            stats_out3 = gr.Textbox(label="총 대화한 유저 수")
            stats_out4 = gr.Textbox(label="오늘 대화한 유저 수")
            stats_out5 = gr.Textbox(label="OpenAI 토큰 소비량")
            stats_out6 = gr.Dataframe(label="카드 등급별 출하량 및 백분율")
            stats_out7 = gr.Dataframe(label="레벨별 현황")
            stats_btn.click(show_dashboard_stats, inputs=None, outputs=[stats_out1, stats_out2, stats_out3, stats_out4, stats_out5, stats_out6, stats_out7])

        with gr.Tab("전체 랭킹"):
            gr.Markdown("## 전체 유저 랭킹")
            ranking_btn = gr.Button("전체 랭킹 새로고침")
            ranking_out1 = gr.Dataframe(label="Kagari 랭킹 (전체 유저)")
            ranking_out2 = gr.Dataframe(label="Eros 랭킹 (전체 유저)")
            ranking_out3 = gr.Dataframe(label="Elysia 랭킹 (전체 유저)")
            ranking_out4 = gr.Dataframe(label="Total 랭킹 (전체 유저)")
            ranking_btn.click(show_all_rankings, inputs=None, outputs=[ranking_out1, ranking_out2, ranking_out3, ranking_out4])

        with gr.Tab("스토리 진행 현황"):
            gr.Markdown("## 전체 스토리 진행 현황")
            story_btn = gr.Button("스토리 진행 현황 새로고침")
            story_out = gr.Dataframe(label="캐릭터별 챕터 진행 현황")
            story_btn.click(get_all_story_progress, inputs=None, outputs=[story_out])

        with gr.Tab("전체 유저 데이터"):
            gr.Markdown("## 전체 유저 데이터")
            user_details_out = gr.Dataframe(
                label="User Details",
                headers=[
                    "User ID", "Join Date",
                    "Kagari Messages", "Eros Messages", "Elysia Messages",
                    "Kagari Affinity", "Eros Affinity", "Elysia Affinity",
                    "Total Messages", "Total Affinity"
                ]
            )
            get_all_users_data_btn = gr.Button("전체 유저 데이터 새로고침")
            get_all_users_data_btn.click(get_all_users_data, inputs=None, outputs=user_details_out)

    demo.launch(share=True)