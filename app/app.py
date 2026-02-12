import streamlit as st
import streamlit.components.v1 as components
import os
import json
from datetime import datetime
from dotenv import load_dotenv

from api import (
    call_claude,
    summarize_reviews,
    summarize_reviews_openai,
    translate_to_english,
    translate_to_english_openai,
    translate_to_french,
    translate_to_french_openai,
    evaluate_translation_quality,
    evaluate_translation_quality_openai,
)
from database import (
    init_db,
    save_prompt_version,
    get_prompt_versions,
    get_prompt_version,
    get_latest_prompt,
    add_dictionary_entry,
    get_dictionary_entries,
    get_dictionary_as_text,
    delete_dictionary_entry,
    save_translation_result,
    update_human_evaluation,
    get_translation_results,
)
from bigquery_client import (
    fetch_reviews,
    SKIN_CONCERN_FRENCH,
    get_top_skin_concern,
    get_highest_satisfaction_concern,
)
from prompts import (
    DEFAULT_GUIDELINE,
    DEFAULT_SUMMARY_SKINCARE,
    DEFAULT_SUMMARY_MAKEUP,
    DEFAULT_TRANSLATION_EN,
    DEFAULT_TRANSLATION_FR,
    DEFAULT_QUALITY_CHECK,
)

load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="Review Translator",
    page_icon="◯",
    layout="wide",
)

# CSS 스타일
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    * {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif;
    }

    .stApp {
        background-color: #fafafa;
    }

    h1, h2, h3 {
        font-weight: 600 !important;
        color: #1d1d1f !important;
    }

    .stButton > button {
        background-color: #1d1d1f !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }

    .stButton > button:hover {
        background-color: #424245 !important;
    }

    .stButton > button:disabled {
        background-color: #e0e0e0 !important;
        color: #a0a0a0 !important;
        cursor: not-allowed !important;
        opacity: 0.6 !important;
    }

    .piyonna-preview {
        background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
        border: 1px solid #ffd4d4;
        border-radius: 16px;
        padding: 20px;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .piyonna-header {
        font-size: 14px;
        color: #ff6b6b;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .piyonna-satisfaction {
        font-size: 24px;
        font-weight: 700;
        color: #1d1d1f;
        margin-bottom: 16px;
    }

    .piyonna-section {
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    .piyonna-section-title {
        font-size: 12px;
        color: #86868b;
        font-weight: 500;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .piyonna-text {
        font-size: 15px;
        color: #1d1d1f;
        line-height: 1.6;
    }

    .concern-badge {
        display: inline-block;
        background: #fff0f0;
        color: #ff6b6b;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
        margin-right: 8px;
        margin-bottom: 8px;
    }

    .quality-pass {
        background-color: #d4edda;
        color: #155724;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 500;
    }

    .quality-fail {
        background-color: #f8d7da;
        color: #721c24;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 500;
    }

    .quality-review {
        background-color: #fff3cd;
        color: #856404;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 500;
    }

    /* CSV 업로드 영역 강조 */
    [data-testid="stFileUploader"] {
        background-color: #f0f8ff;
        border: 2px dashed #4a90d9;
        border-radius: 12px;
        padding: 20px;
    }

    [data-testid="stFileUploader"] > div {
        min-height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    [data-testid="stFileUploader"] label {
        font-size: 16px !important;
        font-weight: 500 !important;
        color: #1d1d1f !important;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화 (새로고침 시 항상 초기화)
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.reviews_data = None
    # Claude 결과
    st.session_state.summary_kr = None
    st.session_state.summary_en = None
    st.session_state.summary_fr = None
    # OpenAI 결과
    st.session_state.summary_kr_openai = None
    st.session_state.summary_en_openai = None
    st.session_state.summary_fr_openai = None
    st.session_state.quality_result = None
    st.session_state.quality_result_openai = None
    st.session_state.current_result_id = None

# 기존 세션에 새 변수 추가 (마이그레이션)
if "summary_kr_openai" not in st.session_state:
    st.session_state.summary_kr_openai = None
if "summary_en_openai" not in st.session_state:
    st.session_state.summary_en_openai = None
if "summary_fr_openai" not in st.session_state:
    st.session_state.summary_fr_openai = None
if "quality_result_openai" not in st.session_state:
    st.session_state.quality_result_openai = None
if "selected_category" not in st.session_state:
    st.session_state.selected_category = "스킨케어"

    # 프롬프트 초기화: DB에서 최신 버전 로드 (없으면 기본값)
    prompt_types = {
        "guideline": DEFAULT_GUIDELINE,
        "summary_skincare": DEFAULT_SUMMARY_SKINCARE,
        "summary_makeup": DEFAULT_SUMMARY_MAKEUP,
        "translation_en": DEFAULT_TRANSLATION_EN,
        "translation_fr": DEFAULT_TRANSLATION_FR,
        "quality_check": DEFAULT_QUALITY_CHECK,
    }

    for prompt_type, default_value in prompt_types.items():
        latest = get_latest_prompt(prompt_type)
        if latest:
            st.session_state[f"prompt_{prompt_type}"] = latest['content']
        else:
            st.session_state[f"prompt_{prompt_type}"] = default_value

# API 키 확인
api_key = os.getenv("ANTHROPIC_API_KEY")
bq_configured = os.getenv("GOOGLE_CREDENTIALS") and os.getenv("GOOGLE_CLOUD_PROJECT")

# 헤더
st.title("Review Translator")
st.caption("지그재그 리뷰 요약, 번역용 프롬프트를 테스트 할 수 있는 사이트 입니다. (수정자 bea)")

# 사이드바: 설정 및 프롬프트 관리
with st.sidebar:
    st.markdown("### 설정")

    # API 키 입력 (환경변수 없을 때)
    if not api_key:
        api_key = st.text_input("Anthropic API Key", type="password")

    if not bq_configured:
        st.warning("BigQuery 미설정 (GOOGLE_CREDENTIALS, GOOGLE_CLOUD_PROJECT)")

    st.divider()

    # 탭: 프롬프트 / 히스토리
    sidebar_tab = st.radio("관리", ["프롬프트", "히스토리"], horizontal=True, label_visibility="collapsed")

    if sidebar_tab == "프롬프트":
        st.markdown("### 저장된 버전 불러오기")
        st.caption("프롬프트 저장은 각 탭에서 직접 하세요")

        prompt_type = st.selectbox(
            "프롬프트 유형",
            ["guideline", "summary_skincare", "summary_makeup", "translation_en", "translation_fr", "quality_check"],
            format_func=lambda x: {
                "guideline": "공통 지침",
                "summary_skincare": "요약 (스킨케어)",
                "summary_makeup": "요약 (메이크업)",
                "translation_en": "번역 (EN)",
                "translation_fr": "번역 (FR)",
                "quality_check": "품질 평가",
            }.get(x, x),
            key="sidebar_prompt_type"
        )

        versions = get_prompt_versions(prompt_type)

        if versions:
            for v in versions[:5]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.caption(f"{v['name']} ({str(v['created_at'])[:10]})")
                with col2:
                    if st.button("적용", key=f"apply_{prompt_type}_{v['id']}"):
                        st.session_state[f"prompt_{prompt_type}"] = v['content']
                        st.success(f"'{v['name']}' 적용됨")
                        st.rerun()
        else:
            st.caption("저장된 버전 없음")

    else:  # 히스토리
        st.markdown("### 번역 히스토리")

        # 통계
        results = get_translation_results(50)
        if results:
            pass_cnt = len([r for r in results if r.get('human_evaluation') == 'pass'])
            fail_cnt = len([r for r in results if r.get('human_evaluation') == 'fail'])
            pending_cnt = len([r for r in results if r.get('human_evaluation') is None])
            st.caption(f"✅ {pass_cnt} | ❌ {fail_cnt} | ⏳ {pending_cnt}")

        # 필터
        filter_status = st.selectbox(
            "필터",
            ["전체", "Pass", "Fail", "Review", "미평가"],
            key="history_filter",
            label_visibility="collapsed"
        )

        # 필터링 적용
        filtered = results
        if filter_status == "Pass":
            filtered = [r for r in results if r.get('human_evaluation') == 'pass']
        elif filter_status == "Fail":
            filtered = [r for r in results if r.get('human_evaluation') == 'fail']
        elif filter_status == "Review":
            filtered = [r for r in results if r.get('human_evaluation') == 'review']
        elif filter_status == "미평가":
            filtered = [r for r in results if r.get('human_evaluation') is None]

        st.caption(f"{len(filtered)}건 표시")

        for r in filtered[:20]:
            status_emoji = {"pass": "✅", "fail": "❌", "review": "⚠️"}.get(r.get('human_evaluation'), "⏳")

            with st.expander(f"{status_emoji} {r['product_id']} ({str(r['created_at'])[:10]})"):
                st.caption(f"카테고리: {r.get('product_category', 'N/A')} | 리뷰: {r.get('review_count', 0)}개 | 만족도: {r.get('satisfaction_rate', 0)}%")

                st.markdown("**한국어 요약**")
                st.text(r.get('summary_kr', '')[:200] + "..." if len(r.get('summary_kr', '')) > 200 else r.get('summary_kr', ''))

                st.markdown("**프랑스어 번역**")
                st.text(r.get('summary_fr', '')[:200] + "..." if len(r.get('summary_fr', '')) > 200 else r.get('summary_fr', ''))

                # 프롬프트 정보 표시
                if r.get('summary_prompt') or r.get('translation_prompt'):
                    st.markdown("**사용된 프롬프트**")
                    if r.get('summary_prompt'):
                        with st.popover("요약 프롬프트"):
                            st.text(r.get('summary_prompt', '')[:500] + "..." if len(r.get('summary_prompt', '')) > 500 else r.get('summary_prompt', ''))
                    if r.get('translation_prompt'):
                        with st.popover("번역 프롬프트"):
                            st.text(r.get('translation_prompt', '')[:500] + "..." if len(r.get('translation_prompt', '')) > 500 else r.get('translation_prompt', ''))

                st.markdown("**평가 변경**")
                hcol1, hcol2, hcol3 = st.columns(3)
                with hcol1:
                    if st.button("✅", key=f"hp_{r['id']}", help="Pass"):
                        update_human_evaluation(r['id'], "pass")
                        st.rerun()
                with hcol2:
                    if st.button("❌", key=f"hf_{r['id']}", help="Fail"):
                        update_human_evaluation(r['id'], "fail")
                        st.rerun()
                with hcol3:
                    if st.button("⚠️", key=f"hr_{r['id']}", help="Review"):
                        update_human_evaluation(r['id'], "review")
                        st.rerun()

# 메인 영역
main_col1, main_col2 = st.columns([1, 1])

with main_col1:
    st.subheader("입력")

    # 현재 세션 상태 표시 및 초기화 버튼
    if st.session_state.reviews_data:
        status_col1, status_col2 = st.columns([3, 1])
        with status_col1:
            data = st.session_state.reviews_data
            st.caption(f"현재 데이터: {data.get('product_id', 'N/A')} ({data.get('text_review_count', 0)}개 리뷰)")
        with status_col2:
            if st.button("초기화", key="reset_top"):
                st.session_state.reviews_data = None
                st.session_state.summary_kr = None
                st.session_state.summary_en = None
                st.session_state.summary_fr = None
                st.session_state.quality_result = None
                st.session_state.current_result_id = None
                st.rerun()

    # 카테고리 선택
    category_options = ["스킨케어", "메이크업"]
    category_index = category_options.index(st.session_state.selected_category) if st.session_state.selected_category in category_options else 0
    category = st.radio(
        "카테고리",
        category_options,
        horizontal=True,
        index=category_index,
        key="main_category"
    )
    # 선택이 변경되면 session state 업데이트
    if category != st.session_state.selected_category:
        st.session_state.selected_category = category

    # CSV 파일 업로드
    st.markdown("#### CSV 파일 업로드")
    st.caption("Redash에서 다운로드한 리뷰 CSV를 드래그앤드롭 하세요")
    uploaded_file = st.file_uploader(
        "CSV 파일을 여기에 드래그하거나 클릭해서 선택",
        type=['csv'],
        help="컬럼: content(리뷰내용), rating(평점), skin_concern(피부고민) | 파일 크기 제한 없음",
        key="csv_upload"
    )

    # 파일이 없으면 last_uploaded_file 초기화 (파일 삭제 시)
    if uploaded_file is None:
        if "last_uploaded_file" in st.session_state:
            del st.session_state["last_uploaded_file"]
    else:
        # 새 파일인지 확인 (파일명 + 크기로 구분)
        file_key = f"{uploaded_file.name}_{uploaded_file.size}"
        is_new_file = st.session_state.get("last_uploaded_file") != file_key

        if is_new_file:
            try:
                import pandas as pd
                import io

                # 새 CSV 업로드 시 세션 완전 초기화 (이전 데이터 맥락 제거)
                st.session_state.summary_kr = None
                st.session_state.summary_en = None
                st.session_state.summary_fr = None
                st.session_state.quality_result = None
                st.session_state.current_result_id = None
                st.session_state.last_uploaded_file = file_key

                # CSV 읽기
                df = pd.read_csv(uploaded_file)

                # 컬럼명 매핑 (다양한 컬럼명 지원)
                content_col = None
                rating_col = None
                concern_col = None

                for col in df.columns:
                    col_lower = col.lower()
                    if col_lower in ['content', 'contents', 'review', 'review_contents', '리뷰', '리뷰내용', '리뷰본문', 'text', 'body']:
                        content_col = col
                    elif col_lower in ['rating', 'review_rating', 'score', '평점', '별점', 'star']:
                        rating_col = col
                    elif col_lower in ['skin_concern', 'concern', '피부고민', '고민', 'skin_type']:
                        concern_col = col

                if content_col is None:
                    st.error(f"리뷰 내용 컬럼을 찾을 수 없습니다. 현재 컬럼: {list(df.columns)}")
                else:
                    # 자동 적용
                    processed_reviews = []
                    satisfied_count = 0

                    for idx, row in df.iterrows():
                        content = str(row[content_col]) if pd.notna(row[content_col]) else ""
                        rating = int(row[rating_col]) if rating_col and pd.notna(row[rating_col]) else 0
                        concern = str(row[concern_col]) if concern_col and pd.notna(row[concern_col]) else ""

                        if rating >= 4:
                            satisfied_count += 1

                        processed_reviews.append({
                            "review_id": str(idx),
                            "content": content,
                            "rating": rating,
                            "skin_concerns": [concern] if concern else [],
                            "skin_concerns_raw": [concern] if concern else [],
                        })

                    text_reviews = [r for r in processed_reviews if r['content'].strip()]
                    satisfaction_rate = round(satisfied_count / len(df) * 100, 1) if len(df) > 0 else 0

                    st.session_state.reviews_data = {
                        "product_id": f"csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "reviews": processed_reviews,
                        "total_count": len(df),
                        "text_review_count": len(text_reviews),
                        "satisfaction_rate": satisfaction_rate,
                        "skin_concern_stats": {},
                    }

                    st.toast(f"CSV 로드 완료: {len(text_reviews)}개 리뷰")
                    st.rerun()

            except Exception as e:
                st.error(f"CSV 파싱 실패: {str(e)}")

    # 조회 결과 표시
    if st.session_state.reviews_data:
        data = st.session_state.reviews_data
        st.divider()

        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("전체 리뷰", f"{data['total_count']}개")
        with col_stat2:
            st.metric("텍스트 리뷰", f"{data['text_review_count']}개")
        with col_stat3:
            st.metric("만족도", f"{data['satisfaction_rate']}%")

        # 피부 고민 통계
        if data['skin_concern_stats']:
            st.markdown("**피부 고민별 통계**")
            for concern, stats in sorted(data['skin_concern_stats'].items(), key=lambda x: x[1]['count'], reverse=True):
                st.caption(f"• {concern}: {stats['count']}명 ({stats['satisfaction_rate']}% 만족)")

        # 리뷰 샘플 보기
        with st.expander(f"리뷰 샘플 보기 ({min(5, len(data['reviews']))}개)"):
            for r in data['reviews'][:5]:
                st.markdown(f"**⭐ {r['rating']}점** | {', '.join(r['skin_concerns']) if r['skin_concerns'] else '피부고민 없음'}")
                st.caption(r['content'][:200] + "..." if len(r['content']) > 200 else r['content'])
                st.divider()

    # 프롬프트 편집 영역
    st.divider()
    st.subheader("프롬프트 편집")

    prompt_tabs = st.tabs(["요약", "번역", "품질평가"])

    with prompt_tabs[0]:
        # 스킨케어/메이크업 각각 별도 표시
        st.caption(f"현재 선택: **{category}**")

        if category == "스킨케어":
            skincare_prompt = st.text_area(
                "요약 프롬프트 (스킨케어)",
                value=st.session_state.get("prompt_summary_skincare", DEFAULT_SUMMARY_SKINCARE),
                height=400,
                key="prompt_summary_skincare",
                label_visibility="collapsed"
            )
            prompt_key = "summary_skincare"
        else:
            makeup_prompt = st.text_area(
                "요약 프롬프트 (메이크업)",
                value=st.session_state.get("prompt_summary_makeup", DEFAULT_SUMMARY_MAKEUP),
                height=400,
                key="prompt_summary_makeup",
                label_visibility="collapsed"
            )
            prompt_key = "summary_makeup"

        # 저장 UI
        save_col1, save_col2 = st.columns([3, 1])
        with save_col1:
            save_name_summary = st.text_input("버전명", placeholder="v1.0", key=f"save_name_{prompt_key}", label_visibility="collapsed")
        with save_col2:
            if st.button("저장", key=f"save_btn_{prompt_key}", use_container_width=True):
                if save_name_summary:
                    save_prompt_version(save_name_summary, prompt_key, st.session_state.get(f"prompt_{prompt_key}", ""))
                    st.success(f"'{save_name_summary}' 저장됨 ({category})")
                    st.rerun()
                else:
                    st.warning("버전명을 입력하세요")

        # 공통 지침 (하단에 위치, 접기 가능)
        st.divider()
        with st.expander("공통 지침 (금칙어/기본 규칙)", expanded=False):
            st.caption("스킨케어/메이크업 요약 시 공통으로 적용되는 지침입니다")
            guideline_prompt = st.text_area(
                "공통 지침 프롬프트",
                value=st.session_state.get("prompt_guideline", DEFAULT_GUIDELINE),
                height=300,
                key="prompt_guideline",
                label_visibility="collapsed"
            )

            # 공통 지침 저장 UI
            guide_col1, guide_col2 = st.columns([3, 1])
            with guide_col1:
                save_name_guideline = st.text_input("버전명", placeholder="v1.0", key="save_name_guideline", label_visibility="collapsed")
            with guide_col2:
                if st.button("저장", key="save_btn_guideline", use_container_width=True):
                    if save_name_guideline:
                        save_prompt_version(save_name_guideline, "guideline", st.session_state.get("prompt_guideline", ""))
                        st.success(f"'{save_name_guideline}' 저장됨 (공통 지침)")
                        st.rerun()
                    else:
                        st.warning("버전명을 입력하세요")

    with prompt_tabs[1]:
        # EN/FR 번역 프롬프트 서브탭
        trans_subtabs = st.tabs(["EN 번역", "FR 번역"])

        with trans_subtabs[0]:
            st.caption("영어 번역 프롬프트")
            translation_en_prompt = st.text_area(
                "EN 번역 프롬프트",
                value=st.session_state.get("prompt_translation_en", DEFAULT_TRANSLATION_EN),
                height=350,
                key="prompt_translation_en",
                label_visibility="collapsed"
            )

            save_col1, save_col2 = st.columns([3, 1])
            with save_col1:
                save_name_trans_en = st.text_input("버전명", placeholder="v1.0", key="save_name_translation_en", label_visibility="collapsed")
            with save_col2:
                if st.button("저장", key="save_btn_translation_en", use_container_width=True):
                    if save_name_trans_en:
                        save_prompt_version(save_name_trans_en, "translation_en", st.session_state.get("prompt_translation_en", ""))
                        st.success(f"'{save_name_trans_en}' 저장됨 (EN 번역)")
                        st.rerun()
                    else:
                        st.warning("버전명을 입력하세요")

        with trans_subtabs[1]:
            st.caption("프랑스어 번역 프롬프트")
            translation_fr_prompt = st.text_area(
                "FR 번역 프롬프트",
                value=st.session_state.get("prompt_translation_fr", DEFAULT_TRANSLATION_FR),
                height=350,
                key="prompt_translation_fr",
                label_visibility="collapsed"
            )

            save_col1, save_col2 = st.columns([3, 1])
            with save_col1:
                save_name_trans_fr = st.text_input("버전명", placeholder="v1.0", key="save_name_translation_fr", label_visibility="collapsed")
            with save_col2:
                if st.button("저장", key="save_btn_translation_fr", use_container_width=True):
                    if save_name_trans_fr:
                        save_prompt_version(save_name_trans_fr, "translation_fr", st.session_state.get("prompt_translation_fr", ""))
                        st.success(f"'{save_name_trans_fr}' 저장됨 (FR 번역)")
                        st.rerun()
                    else:
                        st.warning("버전명을 입력하세요")

    with prompt_tabs[2]:
        st.caption("품질 평가 프롬프트")
        quality_prompt = st.text_area(
            "품질 평가 프롬프트",
            value=st.session_state.get("prompt_quality_check", DEFAULT_QUALITY_CHECK),
            height=400,
            key="prompt_quality_check",
            label_visibility="collapsed"
        )

        save_col1, save_col2 = st.columns([3, 1])
        with save_col1:
            save_name_qual = st.text_input("버전명", placeholder="v1.0", key="save_name_quality", label_visibility="collapsed")
        with save_col2:
            if st.button("저장", key="save_btn_quality", use_container_width=True):
                if save_name_qual:
                    save_prompt_version(save_name_qual, "quality_check", st.session_state.get("prompt_quality_check", ""))
                    st.success(f"'{save_name_qual}' 저장됨 (품질평가)")
                    st.rerun()
                else:
                    st.warning("버전명을 입력하세요")

    # 실행 버튼
    st.divider()
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

    with col_btn1:
        run_summary = st.button("1. 요약 생성", use_container_width=True, disabled=not st.session_state.reviews_data)

    with col_btn2:
        run_translate_en = st.button("2. EN 번역", use_container_width=True, disabled=not st.session_state.summary_kr)

    with col_btn3:
        run_translate_fr = st.button("3. FR 번역", use_container_width=True, disabled=not st.session_state.summary_kr)

    with col_btn4:
        run_quality = st.button("4. 품질 평가", use_container_width=True, disabled=not (st.session_state.summary_en or st.session_state.summary_fr))

    # 사전 관리 (하단 고정)
    st.divider()
    st.subheader("번역 사전")

    entries = get_dictionary_entries()
    st.caption(f"총 {len(entries)}개 단어 등록됨")

    # 새 단어 추가
    dict_col1, dict_col2, dict_col3, dict_col4 = st.columns([2, 2, 2, 1])
    with dict_col1:
        new_kr = st.text_input("한국어", placeholder="닦토", key="main_dict_kr", label_visibility="collapsed")
    with dict_col2:
        new_en = st.text_input("영어", placeholder="wipe-off toner", key="main_dict_en", label_visibility="collapsed")
    with dict_col3:
        new_fr = st.text_input("프랑스어", placeholder="tonique à essuyer", key="main_dict_fr", label_visibility="collapsed")
    with dict_col4:
        if st.button("추가", key="main_dict_add", use_container_width=True):
            if new_kr and new_fr:
                add_dictionary_entry(new_kr, new_fr, new_en, "뷰티용어")
                st.success(f"'{new_kr}' 추가됨")
                st.rerun()
            else:
                st.warning("한국어, 프랑스어 필수")

    # CSV 다운로드 (추출)
    if entries:
        import io
        csv_buffer = io.StringIO()
        csv_buffer.write("korean,english,french,category,notes\n")
        for entry in entries:
            kr = entry['korean'].replace('"', '""')
            en = (entry.get('english') or '').replace('"', '""')
            fr = entry['french'].replace('"', '""')
            cat = (entry.get('category') or '').replace('"', '""')
            notes = (entry.get('notes') or '').replace('"', '""')
            csv_buffer.write(f'"{kr}","{en}","{fr}","{cat}","{notes}"\n')

        st.download_button(
            label="📥 사전 CSV 다운로드",
            data=csv_buffer.getvalue(),
            file_name="translation_dictionary.csv",
            mime="text/csv",
        )

    # 등록된 사전 목록 (접기)
    with st.expander(f"등록된 단어 보기 ({len(entries)}개)"):
        if entries:
            for entry in entries:
                ecol1, ecol2 = st.columns([5, 1])
                with ecol1:
                    en_part = f" ({entry['english']})" if entry.get('english') else ""
                    cat_part = f" [{entry['category']}]" if entry.get('category') else ""
                    st.caption(f"**{entry['korean']}**{en_part} → {entry['french']}{cat_part}")
                with ecol2:
                    if st.button("삭제", key=f"main_del_{entry['id']}"):
                        delete_dictionary_entry(entry['id'])
                        st.rerun()
        else:
            st.caption("등록된 단어 없음")

# 우측 컬럼: 결과 및 프리뷰
with main_col2:
    st.subheader("결과")

    # 요약 실행 (Claude + OpenAI 동시)
    if run_summary and st.session_state.reviews_data and api_key:
        with st.spinner("요약 생성 중... (Claude + OpenAI)"):
            data = st.session_state.reviews_data
            prompt_key = "summary_skincare" if category == "스킨케어" else "summary_makeup"
            openai_key = os.getenv("OPENAI_API_KEY")

            # Claude 요약
            try:
                result_claude = summarize_reviews(
                    api_key=api_key,
                    reviews=data['reviews'],
                    product_category=category,
                    satisfaction_rate=data['satisfaction_rate'],
                    skin_concern_stats=data['skin_concern_stats'],
                    prompt_template=st.session_state.get(f"prompt_{prompt_key}", ""),
                    guideline_prompt=st.session_state.get("prompt_guideline", DEFAULT_GUIDELINE),
                )
                st.session_state.summary_kr = result_claude['raw_response']
            except Exception as e:
                st.error(f"Claude 요약 실패: {str(e)}")
                st.session_state.summary_kr = None

            # OpenAI 요약
            if openai_key:
                try:
                    result_openai = summarize_reviews_openai(
                        api_key=openai_key,
                        reviews=data['reviews'],
                        product_category=category,
                        satisfaction_rate=data['satisfaction_rate'],
                        skin_concern_stats=data['skin_concern_stats'],
                        prompt_template=st.session_state.get(f"prompt_{prompt_key}", ""),
                        guideline_prompt=st.session_state.get("prompt_guideline", DEFAULT_GUIDELINE),
                    )
                    st.session_state.summary_kr_openai = result_openai['raw_response']
                except Exception as e:
                    st.error(f"OpenAI 요약 실패: {str(e)}")
                    st.session_state.summary_kr_openai = None
            else:
                st.warning("OPENAI_API_KEY 미설정")
                st.session_state.summary_kr_openai = None

            st.session_state.summary_en = None
            st.session_state.summary_fr = None
            st.session_state.summary_en_openai = None
            st.session_state.summary_fr_openai = None
            st.session_state.quality_result = None
            st.rerun()

    # EN 번역 실행 (Claude + OpenAI 동시)
    if run_translate_en and st.session_state.summary_kr and api_key:
        with st.spinner("EN 번역 중... (Claude + OpenAI)"):
            openai_key = os.getenv("OPENAI_API_KEY")
            korean_text_claude = st.session_state.summary_kr
            korean_text_openai = st.session_state.summary_kr_openai or st.session_state.summary_kr

            # Claude 번역
            try:
                result_claude = translate_to_english(
                    api_key=api_key,
                    korean_text=korean_text_claude,
                    prompt_template=st.session_state.get("prompt_translation_en", DEFAULT_TRANSLATION_EN),
                    dictionary_text=get_dictionary_as_text(),
                )
                st.session_state.summary_en = result_claude
            except Exception as e:
                st.error(f"Claude EN 번역 실패: {str(e)}")
                st.session_state.summary_en = None

            # OpenAI 번역
            if openai_key:
                try:
                    result_openai = translate_to_english_openai(
                        api_key=openai_key,
                        korean_text=korean_text_openai,
                        prompt_template=st.session_state.get("prompt_translation_en", DEFAULT_TRANSLATION_EN),
                        dictionary_text=get_dictionary_as_text(),
                    )
                    st.session_state.summary_en_openai = result_openai
                except Exception as e:
                    st.error(f"OpenAI EN 번역 실패: {str(e)}")
                    st.session_state.summary_en_openai = None
            else:
                st.session_state.summary_en_openai = None

            st.session_state.quality_result = None
            st.session_state.quality_result_openai = None
            st.rerun()

    # FR 번역 실행 (Claude + OpenAI 동시)
    if run_translate_fr and st.session_state.summary_kr and api_key:
        with st.spinner("FR 번역 중... (Claude + OpenAI)"):
            openai_key = os.getenv("OPENAI_API_KEY")
            # 각 모델의 요약 결과를 각각의 모델로 번역
            korean_text_claude = st.session_state.summary_kr
            korean_text_openai = st.session_state.summary_kr_openai or st.session_state.summary_kr

            # Claude 번역
            try:
                result_claude = translate_to_french(
                    api_key=api_key,
                    korean_text=korean_text_claude,
                    prompt_template=st.session_state.get("prompt_translation_fr", DEFAULT_TRANSLATION_FR),
                    dictionary_text=get_dictionary_as_text(),
                )
                st.session_state.summary_fr = result_claude
            except Exception as e:
                st.error(f"Claude FR 번역 실패: {str(e)}")
                st.session_state.summary_fr = None

            # OpenAI 번역
            if openai_key:
                try:
                    result_openai = translate_to_french_openai(
                        api_key=openai_key,
                        korean_text=korean_text_openai,
                        prompt_template=st.session_state.get("prompt_translation_fr", DEFAULT_TRANSLATION_FR),
                        dictionary_text=get_dictionary_as_text(),
                    )
                    st.session_state.summary_fr_openai = result_openai
                except Exception as e:
                    st.error(f"OpenAI FR 번역 실패: {str(e)}")
                    st.session_state.summary_fr_openai = None
            else:
                st.session_state.summary_fr_openai = None

            st.session_state.quality_result = None
            st.session_state.quality_result_openai = None
            st.rerun()

    # 품질 평가 실행 (Claude + OpenAI 동시)
    if run_quality and (st.session_state.summary_en or st.session_state.summary_fr) and api_key:
        with st.spinner("품질 평가 중... (Claude + OpenAI)"):
            openai_key = os.getenv("OPENAI_API_KEY")

            # Claude 번역에 대한 Claude 평가
            try:
                translation_text_claude = st.session_state.summary_fr or st.session_state.summary_en
                result = evaluate_translation_quality(
                    api_key=api_key,
                    korean_text=st.session_state.summary_kr,
                    french_text=translation_text_claude,
                    prompt_template=st.session_state.get("prompt_quality_check", DEFAULT_QUALITY_CHECK),
                )
                st.session_state.quality_result = result

                # 결과 저장 (프롬프트 포함)
                if st.session_state.reviews_data:
                    data = st.session_state.reviews_data
                    prompt_key = "summary_skincare" if category == "스킨케어" else "summary_makeup"

                    result_id = save_translation_result(
                        product_id=data['product_id'],
                        product_category=category,
                        review_count=data['text_review_count'],
                        satisfaction_rate=data['satisfaction_rate'],
                        summary_kr=st.session_state.summary_kr,
                        summary_fr=st.session_state.summary_fr or "",
                        claude_evaluation=result['status'],
                        flagged_words=result.get('flagged_words', []),
                        summary_prompt=st.session_state.get(f"prompt_{prompt_key}", ""),
                        translation_prompt=st.session_state.get("prompt_translation_fr", ""),
                    )
                    st.session_state.current_result_id = result_id
            except Exception as e:
                st.error(f"Claude 품질 평가 실패: {str(e)}")

            # OpenAI 번역에 대한 OpenAI 평가
            if openai_key and (st.session_state.summary_fr_openai or st.session_state.summary_en_openai):
                try:
                    translation_text_openai = st.session_state.summary_fr_openai or st.session_state.summary_en_openai
                    korean_text_openai = st.session_state.summary_kr_openai or st.session_state.summary_kr
                    result_openai = evaluate_translation_quality_openai(
                        api_key=openai_key,
                        korean_text=korean_text_openai,
                        french_text=translation_text_openai,
                        prompt_template=st.session_state.get("prompt_quality_check", DEFAULT_QUALITY_CHECK),
                    )
                    st.session_state.quality_result_openai = result_openai
                except Exception as e:
                    st.error(f"OpenAI 품질 평가 실패: {str(e)}")
                    st.session_state.quality_result_openai = None

    # 1. 한국어 요약 (모델 비교)
    st.markdown("#### 1. 한국어 요약")
    if st.session_state.summary_kr or st.session_state.summary_kr_openai:
        col_claude, col_openai = st.columns(2)
        with col_claude:
            st.markdown("**Claude**")
            if st.session_state.summary_kr:
                st.text_area("", value=st.session_state.summary_kr, height=200, key="preview_kr_claude", disabled=True, label_visibility="collapsed")
            else:
                st.caption("결과 없음")
        with col_openai:
            st.markdown("**OpenAI**")
            if st.session_state.summary_kr_openai:
                st.text_area("", value=st.session_state.summary_kr_openai, height=200, key="preview_kr_openai", disabled=True, label_visibility="collapsed")
            else:
                st.caption("결과 없음")
    else:
        st.caption("요약 결과가 여기에 표시됩니다")

    # 2. EN 번역 (모델 비교)
    st.markdown("#### 2. EN 번역")
    if st.session_state.summary_en or st.session_state.summary_en_openai:
        col_claude_en, col_openai_en = st.columns(2)
        with col_claude_en:
            st.markdown("**Claude**")
            if st.session_state.summary_en:
                st.text_area("", value=st.session_state.summary_en, height=200, key="preview_en_claude", disabled=True, label_visibility="collapsed")
            else:
                st.caption("결과 없음")
        with col_openai_en:
            st.markdown("**OpenAI**")
            if st.session_state.summary_en_openai:
                st.text_area("", value=st.session_state.summary_en_openai, height=200, key="preview_en_openai", disabled=True, label_visibility="collapsed")
            else:
                st.caption("결과 없음")
    else:
        st.caption("EN 번역 결과가 여기에 표시됩니다")

    # 3. FR 번역 (모델 비교)
    st.markdown("#### 3. FR 번역")
    if st.session_state.summary_fr or st.session_state.summary_fr_openai:
        col_claude_fr, col_openai_fr = st.columns(2)
        with col_claude_fr:
            st.markdown("**Claude**")
            if st.session_state.summary_fr:
                st.text_area("", value=st.session_state.summary_fr, height=200, key="preview_fr_claude", disabled=True, label_visibility="collapsed")
            else:
                st.caption("결과 없음")
        with col_openai_fr:
            st.markdown("**OpenAI**")
            if st.session_state.summary_fr_openai:
                st.text_area("", value=st.session_state.summary_fr_openai, height=200, key="preview_fr_openai", disabled=True, label_visibility="collapsed")
            else:
                st.caption("결과 없음")
    else:
        st.caption("FR 번역 결과가 여기에 표시됩니다")

    # 4. 품질 평가 (모델 비교)
    st.markdown("#### 4. 품질 평가")
    if st.session_state.quality_result or st.session_state.quality_result_openai:
        col_quality_claude, col_quality_openai = st.columns(2)

        with col_quality_claude:
            st.markdown("**Claude**")
            if st.session_state.quality_result:
                result = st.session_state.quality_result
                status = result.get('status', 'review')
                status_class = f"quality-{status}"
                status_text = {"pass": "PASS", "fail": "FAIL", "review": "REVIEW"}.get(status, status)
                st.markdown(f'<div class="{status_class}">{status_text}</div>', unsafe_allow_html=True)
                with st.expander("평가 상세"):
                    st.text(result.get('raw_response', ''))
            else:
                st.caption("결과 없음")

        with col_quality_openai:
            st.markdown("**OpenAI**")
            if st.session_state.quality_result_openai:
                result_openai = st.session_state.quality_result_openai
                status_openai = result_openai.get('status', 'review')
                status_class_openai = f"quality-{status_openai}"
                status_text_openai = {"pass": "PASS", "fail": "FAIL", "review": "REVIEW"}.get(status_openai, status_openai)
                st.markdown(f'<div class="{status_class_openai}">{status_text_openai}</div>', unsafe_allow_html=True)
                with st.expander("평가 상세"):
                    st.text(result_openai.get('raw_response', ''))
            else:
                st.caption("결과 없음")

        # 사람 평가
        st.markdown("**최종 평가**")
        col_eval1, col_eval2, col_eval3 = st.columns(3)
        with col_eval1:
            if st.button("Pass", use_container_width=True, key="eval_pass"):
                if st.session_state.current_result_id:
                    update_human_evaluation(st.session_state.current_result_id, "pass")
                    st.success("Pass로 저장됨")
        with col_eval2:
            if st.button("Fail", use_container_width=True, key="eval_fail"):
                if st.session_state.current_result_id:
                    update_human_evaluation(st.session_state.current_result_id, "fail")
                    st.error("Fail로 저장됨")
        with col_eval3:
            if st.button("Review", use_container_width=True, key="eval_review"):
                if st.session_state.current_result_id:
                    update_human_evaluation(st.session_state.current_result_id, "review")
                    st.warning("Review로 저장됨")
    else:
        st.caption("품질 평가 결과가 여기에 표시됩니다")

# 하단: 새 세션
st.divider()
col_reset1, col_reset2, col_reset3 = st.columns([1, 2, 1])
with col_reset2:
    if st.button("🔄 새 세션 시작 (모든 데이터 초기화)", use_container_width=True):
        # 모든 세션 데이터 완전 초기화
        st.session_state.reviews_data = None
        st.session_state.summary_kr = None
        st.session_state.summary_en = None
        st.session_state.summary_fr = None
        st.session_state.summary_kr_openai = None
        st.session_state.summary_en_openai = None
        st.session_state.summary_fr_openai = None
        st.session_state.quality_result = None
        st.session_state.quality_result_openai = None
        st.session_state.current_result_id = None
        st.rerun()
