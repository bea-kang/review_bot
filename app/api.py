import anthropic
import openai
import os


def get_claude_client(api_key: str = None):
    """Claude 클라이언트 생성"""
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
    return anthropic.Anthropic(api_key=key)


def call_claude(api_key: str, prompt: str, system_prompt: str = None, max_tokens: int = 4096, temperature: float = 0.3) -> str:
    """Claude API 호출

    Args:
        temperature: 낮을수록 일관된 결과 (0.0~1.0, 기본값 0.3)
    """
    client = get_claude_client(api_key)

    messages = [{"role": "user", "content": prompt}]

    kwargs = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature,
    }

    if system_prompt:
        kwargs["system"] = system_prompt

    response = client.messages.create(**kwargs)

    return response.content[0].text


def summarize_reviews(
    api_key: str,
    reviews: list,
    product_category: str,
    satisfaction_rate: float,
    skin_concern_stats: dict,
    prompt_template: str,
    guideline_prompt: str = None,
    dictionary_text: str = None,
) -> dict:
    """
    리뷰 요약 생성

    Returns:
        {
            "summary_line1": str,  # 리뷰 전반 요약 1
            "summary_line2": str,  # 리뷰 전반 요약 2
            "skin_concern_line1": str,  # 피부 고민 요약 1 (스킨케어만)
            "skin_concern_line2": str,  # 피부 고민 요약 2 (스킨케어만)
            "raw_response": str,  # 전체 응답
        }
    """
    # 리뷰 텍스트 준비
    review_texts = []
    for i, r in enumerate(reviews[:100], 1):  # 최대 100개
        text = f"[리뷰 {i}] (별점: {r.get('rating', 'N/A')}점"
        if r.get('skin_concerns'):
            text += f", 피부고민: {', '.join(r['skin_concerns'])}"
        text += f")\n{r['content']}"
        review_texts.append(text)

    reviews_combined = "\n\n".join(review_texts)

    # 피부 고민 통계 텍스트
    skin_stats_text = ""
    if skin_concern_stats:
        lines = []
        for concern, data in sorted(skin_concern_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            lines.append(f"- {concern}: {data['count']}명, 만족도 {data['satisfaction_rate']}%")
        skin_stats_text = "\n".join(lines)

    # 공통 지침 + 카테고리별 프롬프트 합치기
    combined_prompt = prompt_template
    if guideline_prompt:
        combined_prompt = f"{guideline_prompt}\n\n{prompt_template}"

    # 프롬프트 구성
    user_prompt = f"""## 상품 정보
- 카테고리: {product_category}
- 전체 만족도: {satisfaction_rate}%
- 리뷰 수: {len(reviews)}개

## 피부 고민별 통계
{skin_stats_text if skin_stats_text else "피부 고민 데이터 없음"}

## 리뷰 원문
{reviews_combined}

---

{combined_prompt}
"""

    if dictionary_text:
        user_prompt = f"{dictionary_text}\n\n---\n\n{user_prompt}"

    response = call_claude(api_key, user_prompt)

    # 응답 파싱 (간단히)
    return {
        "summary_line1": "",
        "summary_line2": "",
        "skin_concern_line1": "",
        "skin_concern_line2": "",
        "raw_response": response,
    }


# ========== OpenAI API ==========

def get_openai_client(api_key: str = None):
    """OpenAI 클라이언트 생성"""
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return openai.OpenAI(api_key=key)


def call_openai(api_key: str, prompt: str, system_prompt: str = None, max_tokens: int = 4096, temperature: float = 0.3) -> str:
    """OpenAI API 호출 (GPT-4o)

    Args:
        temperature: 낮을수록 일관된 결과 (0.0~2.0, 기본값 0.3)
    """
    client = get_openai_client(api_key)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    return response.choices[0].message.content


def summarize_reviews_openai(
    api_key: str,
    reviews: list,
    product_category: str,
    satisfaction_rate: float,
    skin_concern_stats: dict,
    prompt_template: str,
    guideline_prompt: str = None,
    dictionary_text: str = None,
) -> dict:
    """리뷰 요약 생성 (GPT-4o)"""
    # 리뷰 텍스트 준비
    review_texts = []
    for i, r in enumerate(reviews[:100], 1):
        text = f"[리뷰 {i}] (별점: {r.get('rating', 'N/A')}점"
        if r.get('skin_concerns'):
            text += f", 피부고민: {', '.join(r['skin_concerns'])}"
        text += f")\n{r['content']}"
        review_texts.append(text)

    reviews_combined = "\n\n".join(review_texts)

    # 피부 고민 통계 텍스트
    skin_stats_text = ""
    if skin_concern_stats:
        lines = []
        for concern, data in sorted(skin_concern_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            lines.append(f"- {concern}: {data['count']}명, 만족도 {data['satisfaction_rate']}%")
        skin_stats_text = "\n".join(lines)

    # 공통 지침 + 카테고리별 프롬프트 합치기
    combined_prompt = prompt_template
    if guideline_prompt:
        combined_prompt = f"{guideline_prompt}\n\n{prompt_template}"

    # 프롬프트 구성
    user_prompt = f"""## 상품 정보
- 카테고리: {product_category}
- 전체 만족도: {satisfaction_rate}%
- 리뷰 수: {len(reviews)}개

## 피부 고민별 통계
{skin_stats_text if skin_stats_text else "피부 고민 데이터 없음"}

## 리뷰 원문
{reviews_combined}

---

{combined_prompt}
"""

    if dictionary_text:
        user_prompt = f"{dictionary_text}\n\n---\n\n{user_prompt}"

    response = call_openai(api_key, user_prompt, temperature=0.3)

    return {
        "summary_line1": "",
        "summary_line2": "",
        "skin_concern_line1": "",
        "skin_concern_line2": "",
        "raw_response": response,
    }


def translate_to_english(
    api_key: str,
    korean_text: str,
    prompt_template: str,
    dictionary_text: str = None,
) -> str:
    """한국어 → 영어 번역

    개선사항:
    - system prompt로 번역 지침 분리 (지침 준수율 향상)
    - temperature 0.3 적용 (일관성 향상)
    """
    # 번역 지침은 system prompt로 분리
    system_prompt = prompt_template
    if dictionary_text:
        system_prompt = f"{dictionary_text}\n\n---\n\n{system_prompt}"

    # user prompt는 번역할 텍스트만
    user_prompt = f"""## 번역 대상 (한국어)
{korean_text}

위 한국어 텍스트를 영어로 번역해주세요."""

    response = call_claude(api_key, user_prompt, system_prompt=system_prompt, temperature=0.3)

    return response


def translate_to_french(
    api_key: str,
    korean_text: str,
    prompt_template: str,
    dictionary_text: str = None,
) -> str:
    """한국어 → 프랑스어 번역

    개선사항:
    - system prompt로 번역 지침 분리 (지침 준수율 향상)
    - temperature 0.3 적용 (일관성 향상)
    """
    # 번역 지침은 system prompt로 분리
    system_prompt = prompt_template
    if dictionary_text:
        system_prompt = f"{dictionary_text}\n\n---\n\n{system_prompt}"

    # user prompt는 번역할 텍스트만
    user_prompt = f"""## 번역 대상 (한국어)
{korean_text}

위 한국어 텍스트를 프랑스어로 번역해주세요."""

    response = call_claude(api_key, user_prompt, system_prompt=system_prompt, temperature=0.3)

    return response


def translate_to_english_openai(
    api_key: str,
    korean_text: str,
    prompt_template: str,
    dictionary_text: str = None,
) -> str:
    """한국어 → 영어 번역 (GPT-4o)"""
    system_prompt = prompt_template
    if dictionary_text:
        system_prompt = f"{dictionary_text}\n\n---\n\n{system_prompt}"

    user_prompt = f"""## 번역 대상 (한국어)
{korean_text}

위 한국어 텍스트를 영어로 번역해주세요."""

    response = call_openai(api_key, user_prompt, system_prompt=system_prompt, temperature=0.3)

    return response


def translate_to_french_openai(
    api_key: str,
    korean_text: str,
    prompt_template: str,
    dictionary_text: str = None,
) -> str:
    """한국어 → 프랑스어 번역 (GPT-4o)"""
    # 번역 지침
    system_prompt = prompt_template
    if dictionary_text:
        system_prompt = f"{dictionary_text}\n\n---\n\n{system_prompt}"

    user_prompt = f"""## 번역 대상 (한국어)
{korean_text}

위 한국어 텍스트를 프랑스어로 번역해주세요."""

    response = call_openai(api_key, user_prompt, system_prompt=system_prompt, temperature=0.3)

    return response


def evaluate_translation_quality(
    api_key: str,
    korean_text: str,
    french_text: str,
    prompt_template: str,
) -> dict:
    """
    번역 품질 자동 평가

    Returns:
        {
            "status": "pass" | "fail" | "review",
            "score": int (1-10),
            "issues": list[str],
            "flagged_words": list[str],  # 미번역/오번역 의심 단어
            "suggestions": str,
            "raw_response": str,
        }
    """

    user_prompt = f"""## 한국어 원문
{korean_text}

## 프랑스어 번역본
{french_text}

---

{prompt_template}
"""

    response = call_claude(api_key, user_prompt)

    # 기본 파싱 (실제로는 더 정교하게)
    status = "review"
    if "PASS" in response.upper():
        status = "pass"
    elif "FAIL" in response.upper():
        status = "fail"

    return {
        "status": status,
        "score": 0,
        "issues": [],
        "flagged_words": [],
        "suggestions": "",
        "raw_response": response,
    }


def evaluate_translation_quality_openai(
    api_key: str,
    korean_text: str,
    french_text: str,
    prompt_template: str,
) -> dict:
    """번역 품질 자동 평가 (GPT-4o)"""

    user_prompt = f"""## 한국어 원문
{korean_text}

## 프랑스어 번역본
{french_text}

---

{prompt_template}
"""

    response = call_openai(api_key, user_prompt, temperature=0.3)

    status = "review"
    if "PASS" in response.upper():
        status = "pass"
    elif "FAIL" in response.upper():
        status = "fail"

    return {
        "status": status,
        "score": 0,
        "issues": [],
        "flagged_words": [],
        "suggestions": "",
        "raw_response": response,
    }
