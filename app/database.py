import json
import os
from datetime import datetime
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    USE_POSTGRES = True
else:
    import sqlite3
    USE_POSTGRES = False
    DB_PATH = Path(__file__).parent / "review_translator.db"


def get_connection():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        # 프롬프트 버전 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                prompt_type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 번역 사전 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_dictionary (
                id SERIAL PRIMARY KEY,
                korean TEXT NOT NULL UNIQUE,
                english TEXT,
                french TEXT NOT NULL,
                category TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 번역 결과 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_results (
                id SERIAL PRIMARY KEY,
                product_id TEXT NOT NULL,
                product_category TEXT,
                review_count INTEGER,
                satisfaction_rate FLOAT,
                summary_kr TEXT,
                summary_fr TEXT,
                skin_concern_summary_kr TEXT,
                skin_concern_summary_fr TEXT,
                claude_evaluation TEXT,
                human_evaluation TEXT,
                human_comment TEXT,
                flagged_words TEXT,
                prompt_version_id INTEGER,
                summary_prompt TEXT,
                translation_prompt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # SQLite 버전
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                prompt_type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_dictionary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                korean TEXT NOT NULL UNIQUE,
                english TEXT,
                french TEXT NOT NULL,
                category TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                product_category TEXT,
                review_count INTEGER,
                satisfaction_rate FLOAT,
                summary_kr TEXT,
                summary_fr TEXT,
                skin_concern_summary_kr TEXT,
                skin_concern_summary_fr TEXT,
                claude_evaluation TEXT,
                human_evaluation TEXT,
                human_comment TEXT,
                flagged_words TEXT,
                prompt_version_id INTEGER,
                summary_prompt TEXT,
                translation_prompt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # 기존 테이블에 새 컬럼 추가 (마이그레이션)
    try:
        if USE_POSTGRES:
            cursor.execute("ALTER TABLE translation_results ADD COLUMN IF NOT EXISTS summary_prompt TEXT")
            cursor.execute("ALTER TABLE translation_results ADD COLUMN IF NOT EXISTS translation_prompt TEXT")
        else:
            # SQLite는 IF NOT EXISTS 지원 안 함, 에러 무시
            try:
                cursor.execute("ALTER TABLE translation_results ADD COLUMN summary_prompt TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE translation_results ADD COLUMN translation_prompt TEXT")
            except:
                pass
    except:
        pass

    conn.commit()
    conn.close()


# ========== 프롬프트 버전 관리 ==========

def save_prompt_version(name: str, prompt_type: str, content: str) -> int:
    """프롬프트 저장 (prompt_type: summary_skincare, summary_makeup, translation, quality_check)"""
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute(
            "INSERT INTO prompt_versions (name, prompt_type, content) VALUES (%s, %s, %s) RETURNING id",
            (name, prompt_type, content)
        )
        version_id = cursor.fetchone()[0]
    else:
        cursor.execute(
            "INSERT INTO prompt_versions (name, prompt_type, content) VALUES (?, ?, ?)",
            (name, prompt_type, content)
        )
        version_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return version_id


def get_prompt_versions(prompt_type: str = None):
    """프롬프트 버전 목록 조회"""
    conn = get_connection()

    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if prompt_type:
            cursor.execute(
                "SELECT * FROM prompt_versions WHERE prompt_type = %s ORDER BY created_at DESC",
                (prompt_type,)
            )
        else:
            cursor.execute("SELECT * FROM prompt_versions ORDER BY created_at DESC")
    else:
        cursor = conn.cursor()
        if prompt_type:
            cursor.execute(
                "SELECT * FROM prompt_versions WHERE prompt_type = ? ORDER BY created_at DESC",
                (prompt_type,)
            )
        else:
            cursor.execute("SELECT * FROM prompt_versions ORDER BY created_at DESC")

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_prompt_version(version_id: int):
    """특정 프롬프트 버전 조회"""
    conn = get_connection()

    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM prompt_versions WHERE id = %s", (version_id,))
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prompt_versions WHERE id = ?", (version_id,))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_latest_prompt(prompt_type: str):
    """특정 타입의 최신 프롬프트 조회"""
    conn = get_connection()

    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT * FROM prompt_versions WHERE prompt_type = %s ORDER BY created_at DESC LIMIT 1",
            (prompt_type,)
        )
    else:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM prompt_versions WHERE prompt_type = ? ORDER BY created_at DESC LIMIT 1",
            (prompt_type,)
        )

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ========== 번역 사전 관리 ==========

def add_dictionary_entry(korean: str, french: str, english: str = None, category: str = None, notes: str = None) -> int:
    """사전 항목 추가"""
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute(
            """INSERT INTO translation_dictionary (korean, english, french, category, notes)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (korean) DO UPDATE SET english = %s, french = %s, category = %s, notes = %s
               RETURNING id""",
            (korean, english, french, category, notes, english, french, category, notes)
        )
        entry_id = cursor.fetchone()[0]
    else:
        cursor.execute(
            """INSERT OR REPLACE INTO translation_dictionary (korean, english, french, category, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (korean, english, french, category, notes)
        )
        entry_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return entry_id


def get_dictionary_entries(category: str = None):
    """사전 항목 조회"""
    conn = get_connection()

    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if category:
            cursor.execute(
                "SELECT * FROM translation_dictionary WHERE category = %s ORDER BY korean",
                (category,)
            )
        else:
            cursor.execute("SELECT * FROM translation_dictionary ORDER BY korean")
    else:
        cursor = conn.cursor()
        if category:
            cursor.execute(
                "SELECT * FROM translation_dictionary WHERE category = ? ORDER BY korean",
                (category,)
            )
        else:
            cursor.execute("SELECT * FROM translation_dictionary ORDER BY korean")

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_dictionary_as_text():
    """사전을 프롬프트용 텍스트로 변환"""
    entries = get_dictionary_entries()
    if not entries:
        return ""

    lines = ["[번역 사전 - 아래 단어는 지정된 번역어를 사용하세요]"]
    for entry in entries:
        line = f"- {entry['korean']}"
        if entry['english']:
            line += f" → EN: {entry['english']}"
        line += f" → FR: {entry['french']}"
        lines.append(line)

    return "\n".join(lines)


def delete_dictionary_entry(entry_id: int):
    """사전 항목 삭제"""
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute("DELETE FROM translation_dictionary WHERE id = %s", (entry_id,))
    else:
        cursor.execute("DELETE FROM translation_dictionary WHERE id = ?", (entry_id,))

    conn.commit()
    conn.close()


# ========== 번역 결과 관리 ==========

def save_translation_result(
    product_id: str,
    product_category: str,
    review_count: int,
    satisfaction_rate: float,
    summary_kr: str,
    summary_fr: str,
    skin_concern_summary_kr: str = None,
    skin_concern_summary_fr: str = None,
    claude_evaluation: str = None,
    flagged_words: list = None,
    prompt_version_id: int = None,
    summary_prompt: str = None,
    translation_prompt: str = None
) -> int:
    """번역 결과 저장 (프롬프트 포함)"""
    conn = get_connection()
    cursor = conn.cursor()

    flagged_json = json.dumps(flagged_words, ensure_ascii=False) if flagged_words else None

    if USE_POSTGRES:
        cursor.execute(
            """INSERT INTO translation_results
               (product_id, product_category, review_count, satisfaction_rate,
                summary_kr, summary_fr, skin_concern_summary_kr, skin_concern_summary_fr,
                claude_evaluation, flagged_words, prompt_version_id, summary_prompt, translation_prompt)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (product_id, product_category, review_count, satisfaction_rate,
             summary_kr, summary_fr, skin_concern_summary_kr, skin_concern_summary_fr,
             claude_evaluation, flagged_json, prompt_version_id, summary_prompt, translation_prompt)
        )
        result_id = cursor.fetchone()[0]
    else:
        cursor.execute(
            """INSERT INTO translation_results
               (product_id, product_category, review_count, satisfaction_rate,
                summary_kr, summary_fr, skin_concern_summary_kr, skin_concern_summary_fr,
                claude_evaluation, flagged_words, prompt_version_id, summary_prompt, translation_prompt)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (product_id, product_category, review_count, satisfaction_rate,
             summary_kr, summary_fr, skin_concern_summary_kr, skin_concern_summary_fr,
             claude_evaluation, flagged_json, prompt_version_id, summary_prompt, translation_prompt)
        )
        result_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return result_id


def update_human_evaluation(result_id: int, evaluation: str, comment: str = None):
    """사람 평가 업데이트"""
    conn = get_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute(
            "UPDATE translation_results SET human_evaluation = %s, human_comment = %s WHERE id = %s",
            (evaluation, comment, result_id)
        )
    else:
        cursor.execute(
            "UPDATE translation_results SET human_evaluation = ?, human_comment = ? WHERE id = ?",
            (evaluation, comment, result_id)
        )

    conn.commit()
    conn.close()


def get_translation_results(limit: int = 50):
    """번역 결과 목록 조회"""
    conn = get_connection()

    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT * FROM translation_results ORDER BY created_at DESC LIMIT %s",
            (limit,)
        )
    else:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM translation_results ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_translation_result(result_id: int):
    """특정 번역 결과 조회"""
    conn = get_connection()

    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM translation_results WHERE id = %s", (result_id,))
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM translation_results WHERE id = ?", (result_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        result = dict(row)
        if result.get('flagged_words'):
            result['flagged_words'] = json.loads(result['flagged_words'])
        return result
    return None


# 초기화
init_db()
