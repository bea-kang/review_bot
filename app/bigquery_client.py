import os
import json
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd

# 피부 고민 매핑 (지그재그 → Piyonna 카테고리)
SKIN_CONCERN_MAPPING = {
    # 트러블 케어 (Soin anti-imperfections)
    "ACNE": "트러블 케어",
    "BLACKHEAD": "트러블 케어",
    "EXCESS_SEBUM": "트러블 케어",
    "ACNE_SCARS": "트러블 케어",
    # 안티에이징 (Soin anti-rides & anti-âge)
    "WRINKLES": "안티에이징",
    "ELASTICITY": "안티에이징",
    "HAIR_LOSS": "안티에이징",
    # 보습 & 영양 (Soin hydratant & nourrissant)
    "EXFOLIATION": "보습 & 영양",
    "OIL_AND_WATER_BALANCE": "보습 & 영양",
    "DANDRUFF": "보습 & 영양",
    # 미백 & 잡티 케어 (Soin anti tache)
    "BLEMISHES": "미백 & 잡티 케어",
    "WHITENING": "미백 & 잡티 케어",
    "DARK_CIRCLES": "미백 & 잡티 케어",
    "MELASMA": "미백 & 잡티 케어",
    # 진정 & 홍조 케어 (Soin anti-rougeurs)
    "ECZEMA": "진정 & 홍조 케어",
    "SENSITIVITY": "진정 & 홍조 케어",
    "REDNESS": "진정 & 홍조 케어",
}

SKIN_CONCERN_FRENCH = {
    "트러블 케어": "Soin anti-imperfections",
    "안티에이징": "Soin anti-rides & anti-âge",
    "보습 & 영양": "Soin hydratant & nourrissant",
    "미백 & 잡티 케어": "Soin anti tache",
    "진정 & 홍조 케어": "Soin anti-rougeurs",
}


def get_bigquery_client():
    """BigQuery 클라이언트 생성"""
    credentials_json = os.getenv("GOOGLE_CREDENTIALS")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    if not credentials_json or not project_id:
        raise ValueError("GOOGLE_CREDENTIALS 또는 GOOGLE_CLOUD_PROJECT 환경변수가 설정되지 않았습니다.")

    credentials_dict = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(credentials_dict)
    client = bigquery.Client(credentials=credentials, project=project_id)

    return client


def fetch_reviews(product_id: str) -> dict:
    """
    상품 ID로 리뷰 조회

    Returns:
        {
            "product_id": str,
            "reviews": list[dict],  # 개별 리뷰 목록
            "total_count": int,     # 전체 리뷰 수
            "text_review_count": int,  # 텍스트 리뷰 수
            "satisfaction_rate": float,  # 만족도 (4-5점 비율)
            "skin_concern_stats": dict,  # 피부고민별 통계
        }
    """
    client = get_bigquery_client()

    query = f"""
    SELECT
        pr.id AS review_id,
        pr.contents AS review_content,
        pr.rating,
        pr.date_created AT TIME ZONE 'Asia/Seoul' AS created_at,
        pr.user_account_id,
        ci.name AS product_option,
        uab.skin_concern
    FROM review.product_reviews pr
    LEFT JOIN catalog.items ci
        ON pr.product_item_id = ci.id
    LEFT JOIN zigzag.user_account_bodies uab
        ON pr.user_account_id = uab.user_account_id
        AND uab.deprecated = 0
    WHERE pr.product_id = {product_id}
      AND COALESCE(pr.is_deleted, 0) = 0
      AND COALESCE(pr.is_fraud_deleted, 0) = 0
    ORDER BY pr.date_created DESC
    """

    df = client.query(query).to_dataframe()

    if df.empty:
        return {
            "product_id": product_id,
            "reviews": [],
            "total_count": 0,
            "text_review_count": 0,
            "satisfaction_rate": 0,
            "skin_concern_stats": {},
        }

    # 기본 통계
    total_count = len(df)
    text_reviews = df[df['review_content'].notna() & (df['review_content'] != '')]
    text_review_count = len(text_reviews)

    # 만족도 계산 (4-5점 비율)
    satisfied = df[df['rating'] >= 4]
    satisfaction_rate = round(len(satisfied) / total_count * 100, 1) if total_count > 0 else 0

    # 피부 고민 통계
    skin_concern_stats = calculate_skin_concern_stats(df)

    # 리뷰 목록 (텍스트가 있는 것만)
    reviews = []
    for _, row in text_reviews.iterrows():
        # skin_concern 파싱 (JSON array 형태일 수 있음)
        skin_concerns = parse_skin_concerns(row.get('skin_concern'))
        mapped_concerns = [SKIN_CONCERN_MAPPING.get(sc, sc) for sc in skin_concerns if sc in SKIN_CONCERN_MAPPING]

        reviews.append({
            "review_id": str(row['review_id']),
            "content": row['review_content'],
            "rating": int(row['rating']) if pd.notna(row['rating']) else None,
            "created_at": str(row['created_at']) if pd.notna(row['created_at']) else None,
            "product_option": row['product_option'] if pd.notna(row['product_option']) else None,
            "skin_concerns": mapped_concerns,
            "skin_concerns_raw": skin_concerns,
        })

    return {
        "product_id": product_id,
        "reviews": reviews,
        "total_count": total_count,
        "text_review_count": text_review_count,
        "satisfaction_rate": satisfaction_rate,
        "skin_concern_stats": skin_concern_stats,
    }


def parse_skin_concerns(skin_concern_value) -> list:
    """피부 고민 값 파싱 (JSON array 또는 단일 값)"""
    if pd.isna(skin_concern_value) or skin_concern_value is None:
        return []

    if isinstance(skin_concern_value, list):
        return skin_concern_value

    if isinstance(skin_concern_value, str):
        # JSON array 시도
        if skin_concern_value.startswith('['):
            try:
                return json.loads(skin_concern_value)
            except:
                pass
        # 쉼표 구분
        if ',' in skin_concern_value:
            return [s.strip() for s in skin_concern_value.split(',')]
        # 단일 값
        return [skin_concern_value]

    return []


def calculate_skin_concern_stats(df: pd.DataFrame) -> dict:
    """피부 고민별 통계 계산"""
    stats = {
        "트러블 케어": {"count": 0, "satisfied": 0},
        "안티에이징": {"count": 0, "satisfied": 0},
        "보습 & 영양": {"count": 0, "satisfied": 0},
        "미백 & 잡티 케어": {"count": 0, "satisfied": 0},
        "진정 & 홍조 케어": {"count": 0, "satisfied": 0},
    }

    for _, row in df.iterrows():
        skin_concerns = parse_skin_concerns(row.get('skin_concern'))
        rating = row.get('rating', 0)
        is_satisfied = rating >= 4 if pd.notna(rating) else False

        for sc in skin_concerns:
            mapped = SKIN_CONCERN_MAPPING.get(sc)
            if mapped and mapped in stats:
                stats[mapped]["count"] += 1
                if is_satisfied:
                    stats[mapped]["satisfied"] += 1

    # 만족도 비율 계산
    result = {}
    for concern, data in stats.items():
        if data["count"] > 0:
            rate = round(data["satisfied"] / data["count"] * 100, 0)
            result[concern] = {
                "count": data["count"],
                "satisfaction_rate": rate,
                "french": SKIN_CONCERN_FRENCH[concern],
            }

    return result


def get_top_skin_concern(skin_concern_stats: dict) -> tuple:
    """가장 많은 피부 고민 반환 (count 기준)"""
    if not skin_concern_stats:
        return None, None

    top = max(skin_concern_stats.items(), key=lambda x: x[1]["count"])
    return top[0], top[1]


def get_highest_satisfaction_concern(skin_concern_stats: dict) -> tuple:
    """만족도가 가장 높은 피부 고민 반환"""
    if not skin_concern_stats:
        return None, None

    # count가 1개 이상인 것 중에서
    filtered = {k: v for k, v in skin_concern_stats.items() if v["count"] >= 1}
    if not filtered:
        return None, None

    top = max(filtered.items(), key=lambda x: x[1]["satisfaction_rate"])
    return top[0], top[1]
