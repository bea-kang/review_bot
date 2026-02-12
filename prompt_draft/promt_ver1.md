# [PDP>리뷰] 리뷰 AI 프롬프트 정책 (테스트 포함)

# 구현 플로우 (예상)

![Zigzag Review DB Pipeline-2026-01-20-062050.png](%5BPPD%5D%20%EA%B8%80%EB%A1%9C%EB%B2%8C%20%EB%B7%B0%ED%8B%B0%20%ED%94%8C%EB%9E%AB%ED%8F%BC/%5BPRD%5D%20%EA%B8%80%EB%A1%9C%EB%B2%8C%20%EB%B7%B0%ED%8B%B0%20PDP%20%EB%A6%AC%EB%B7%B0%20%EC%A0%95%EC%B1%85/Zigzag_Review_DB_Pipeline-2026-01-20-062050.png)

- 쇼피파이 내 업로드 된 데이터는 후처리 대상에서 제외한다.
    - [BE] 번역본 100% 저장 관리할 예정, 딕셔너리 등의 퀄리티용 데이터 역시 함께 처리할 예정
    - [BE] 리뷰 app 에서의 기능 (e.g. 금칙어) 은 활용하지 않는 방향으로 생각으로, 리뷰 전체 파이프라인 거쳐 피어나 앱 내 노출 (일 갱신) → 전부 개발하진 않는 방향으로 논의 완료하였음

# category mapping

|  | PIYONNA SKIN CONCERN | REVIEW_RAW_피부고민 |
| --- | --- | --- |
| **1** | 트러블 케어
(Soin anti-imperfections) | - 여드름 ACNE
- 블랙헤드 BLACKHEAD
- 피지과다 EXCESS_SEBUM
- 트러블 자국 ACNE_SCARS |
| **2** | 안티에이징
(Soin anti-rides & anti-âge) | - 주름 WRINKLES
- 탄력 ELASTICITY
- 탈모 HAIR_LOSS |
| **3** | 보습 & 영양
(Soin hydratant & nourrissant) | - 각질 EXFOLIATION
- 유수분밸런스 OIL_AND_WATER_BALANCE
- 비듬 DANDRUFF |
| **4** | 미백 & 잡티 케어
(Soin anti tache) | - 잡티 BLEMISHES
- 미백 WHITENING
- 다크서클 DARK_CIRCLES
- 기미 MELASMA |
| **5** | 진정 & 홍조 케어
(Soin anti-rougeurs) | - 아토피 ECZEMA
- 민감성 SENSITIVITY
- 홍조 REDNESS |

# [공통] 요약 rule

```python
## main rule

1. 문장 끝은 "~해요", "~있어요" 형태로 자연스럽게 한국어로 변환
2. 이모지는 요약 문장에 포함하지 않음
3. 리뷰 본문을 요약하는 행위 외 새로운 표현을 사용하거나, 가공하지 않아야 함 
4. 실제 리뷰어가 말하는 것 처럼 자연스러워야 하기 때문에, '~한 분이' '~한 분들이' 처럼 통계적 표현 지양

## 금칙어
 
다음 표현은 요약 대상에서 반드시 제외해야 한다.
1. 피부색 관련 모든 표현 
	- 하얘지다	blanchir, devenir blanc(he)
  - 백옥 피부	peau de porcelaine blanche
  - 우유빛 피부	peau laiteuse
  - 피부가 밝아지다	la peau devient plus claire
  - 뽀얀 피부	peau d'un blanc éclatant
  - 까만 피부 
  - 어두운 피부 
  - 환해지다	s'éclaircir
  - 톤업되다	rehausser le teint
  - 까무잡잡하다	basané(e), mat(e)
  - 피부가 검다/어둡다	peau foncée/sombre
  - 누렇다/노랗다	jaunâtre
2. 황인/동양인/백인/흑인/서양인 직접 언급 (예: 백인같이, 흑인같이, 동양인, 황인 같 백인 같아요. 흑인 같아요. 동양인 같아요) 
3. 단순 감탄사만 있는 리뷰 (예: "너무 좋아요!", "그냥 그래요", "좋아요ㅎㅎ")
4. 작성한 리뷰의 브랜드, 관련 제품과 완전 무관한 제품을 언급하여 비교하는 경우 (예: A회사 제품이 더 좋아요.)

## 요약 수행 조건 
1. 전체 리뷰가 3개 이상일 경우 수행한다. (2개 이하일 경우 요약하지 않음)
```

| case | 전체 리뷰 | 피부 고민 리뷰  | 요약 섹션 UI  |
| --- | --- | --- | --- |
| 1 | O  | O | 노출 |
| 2 | O | < 고민별 1개 | 노출 (고민 영역 제외) |
| 3 | < 3개  | - | 비노출 |
| 4 | X  | X | 비노출 |

# [스킨케어] UI 전시용 프롬프트

코멘트 : 

- 피부 타입에서 데이터 적은 케이스를 커버하기 위해 가장 많이 구매했어요~ 문구를 채택하는 방향
- ATF영역에서 보이는 리뷰 만족도와, 하단 AI요약의 전반 요약 섹션 타이틀 정보는 동일 or 구분하는 방향 (시안 잡으시고 확정)

```kotlin
## 노출 문구 format
1. **[만족도 요약] 문장: 실제로 제품을 사용한 한국인 {n}%가 만족했어요.**
2. [리뷰 전반 요약] 세부 문장1: **제품 사용 후 효과/제품의 장점** 언급량 위주로 요약(구체적 키워드)
3. [리뷰 전반 요약] 세부 문장2: **제품 특징/사용 방법** 언급량 위주로 요약
4. [피부 고민 요약] 두번째 문장: {대표피부고민} 고민이 있는 한국인이 가장 많이 구매했어요. 

## [만족도 요약] 규칙 
- {N}의 산출 방식은 모든 리뷰 개수로 한다
- {n}% 의 산출 방식은, 리뷰의 전체 수 대비 별점이 4, 5점인 리뷰 개수 합산을 백분율로 계산하여 노출한다. 

## [리뷰 전반 요약] 규칙

1. 첫번째 문장: 가장 많이 언급된 **제품 사용 효과/제품 장점** 요약 (구체적 키워드가 있다면 도출)
2. 두번째 문장: 가장 많이 언급된 **제품 특징/사용 방법** 요약 (구체적 키워드가 있다면 도출)
3. 숫자가 있으면 포함 (예: "2주 후", "3일 만에")
4. 재구매 표현이 있다면 두번째 문장 내 포함하여 도출

## [피부 고민 요약] 규칙
- {대표피부고민}는 다섯가지 카테고리 중, 작성된 리뷰 중 가장 많이 작성된 피부 고민 속성을 대표로 지정한다.
- 피부 고민 속성이 없는 리뷰만 있는 상품이면, [피부 고민 요약] 문장을 노출하지 않는다. 
```

# [메이크업] UI 전시용 프롬프트

```python
## 노출 문구 format
1. **[만족도 요약] 문장: 실제로 제품을 사용한 한국인 {N}명 중 {n}%가 만족했어요.**
2. [리뷰 전반 요약] 첫번째 문장: 가장 많이 언급된 **제품 사용 효과/제품의 장점**
3. [리뷰 전반 요약] 두번째 문장: **제품 특징/사용 방법/사용팁** 위주로 요약

## [만족도 요약] 규칙 
- {N}의 산출 방식은 모든 리뷰 개수로 한다
- {n}% 의 산출 방식은, 리뷰의 전체 수 대비 별점이 4, 5점인 리뷰 개수 합산을 백분율로 계산하여 노출한다. 

## [리뷰 전반 요약] 규칙
1. 리뷰 전반 요약 문장 내 다음과 같은 키워드가 있다면 도출합니다.
	- 지속력/발색/커버력
```

# 번역 프롬프트

- 출처 : 현지화 best practice 리서치
- 비고 : 프랑스 운영 인턴시 해당 사항 검수 및 보완 요청 예정 및 딕셔너리 구성 참여 필요*

```python
당신은 K-뷰티 전문 한국어-프랑스어 번역가입니다. 
프랑스 뷰티 시장에서 10년 이상 경력을 가진 네이티브 프랑스어 화자로서 번역합니다.

---

## TASK (작업)
아래 한국어 리뷰 요약을 프랑스어로 현지화 번역하세요.
단순 번역이 아닌, 프랑스 소비자가 자연스럽게 느낄 수 있는 **transcreation(창의적 번역)**을 수행합니다.

---

## CONTEXT (맥락)
- 플랫폼: Piyonna (피어나) - 프랑스 진출 K-뷰티 이커머스
- 타겟: 프랑스 10-30대 여성, K-뷰티에 관심 있는 소비자
- 톤앤매너: 친근하면서도 신뢰감 있는, 전문적이지만 딱딱하지 않은
- 용도: 상품 상세페이지(PDP) 리뷰 AI 요약 영역에 노출하기 위함

---

## STYLE GUIDE (스타일 가이드)

### 문장 스타일
- 간결하고 임팩트 있게 (원문 길이와 비슷하게 유지)
- 프랑스어 자연스러운 어순으로 재구성
- 능동태 선호, 긍정적 표현 사용 
- 한국에서만 사용하는 단어를 해석하여 번역한다. 
(예: 생얼 = 화장 하지 않은 상태의 얼굴, 닦토 = 피부를 닦는 토너, 팩토 = 팩 하듯이 피부에 오래 붙여두는 토너, 1일 1팩 = 매일 마스크팩 하는 루틴, 퍼스널 컬러, 데일리 메이크업 = 일상에서 하는 가벼운 메이크업)

### 톤
- 친근함: "vous" 대신 직접적 표현 가능
- 전문성: 뷰티 업계 용어 정확히 사용
- 신뢰감: 구체적 수치와 효과 강조
```

# 샘플링

- **1차 2026년 1월 16일**
    
    코멘트 : 리뷰 전반 요약 영역을 좀 더 재밌게 긁어오면 좋을 것 같음. 타사 제품이나 팁에 대한 내용 등 처리 방법도 고민 필요. 일단 요약하는 것 외에 줄 수 있는 포인트가 있을지 고민.. 
    
    https://zigzag.kr/catalog/products/136469153
    
    https://zigzag.kr/catalog/products/112211239
    
    https://zigzag.kr/catalog/products/110610718
    
    ```markdown
    ## 테스트 상품 개요
    
    | 구분 | 상품명 | 리뷰 수 | 텍스트 리뷰 | 만족도 |
    | --- | --- | --- | --- | --- |
    | 상위 | VT 리들샷 300 50ml | 1,215개 | 622개 | 98.1% |
    | 중위 | 파티온 노스카나인 트러블 세럼 30ml | 453개 | 294개 | 94.9% |
    | 하위 | 구달 청귤 비타C 잡티 케어 세럼 30ml | 192개 | 156개 | 95.8% |
    
    ---
    
    ## 요약 결과
    
    ### 1. VT 리들샷 300 50ml
    
    **[리뷰 전반 요약]**
    1. 모공이 작아지고 피부결이 정돈되며, 다음 날 피부에 광채가 생겨요.
    2. 100에서 300으로 업그레이드하는 분들이 많고, 3일에 한 번 밤에 재생크림과 함께 사용해요.
    
    **[피부 고민 요약]**
    1. 진정 & 홍조 케어 고민이 있는 한국인이 100% 만족했어요.
    2. 트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ### 2. 파티온 노스카나인 트러블 세럼 30ml
    
    **[리뷰 전반 요약]**
    1. 여드름과 좁쌀이 가라앉고, 피부가 진정되며 피부결이 정돈돼요.
    2. 순하고 자극 없이 사용할 수 있고, 파티온 앰플과 함께 아침저녁으로 발라요.
    
    **[피부 고민 요약]**
    1. 진정 & 홍조 케어 고민이 있는 한국인이 98% 만족했어요.
    2. 트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ### 3. 구달 청귤 비타C 잡티 케어 세럼 30ml
    
    **[리뷰 전반 요약]**
    1. 잡티가 옅어지고 피부가 환해지며, 꾸준히 쓰면 피부결이 맑아져요.
    2. 순하고 촉촉하며, 저녁에 크림과 함께 바르면 효과가 더 좋아요.
    
    **[피부 고민 요약]**
    1. 미백 & 잡티 케어 고민이 있는 한국인이 100% 만족했어요.
    2. 미백 & 잡티 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ## 프랑스어 번역 결과
    
    ### 1. VT Riddle Shot 300 50ml
    
    **[Résumé général des avis]**
    1. Les pores paraissent resserrés, la texture de la peau est affinée et un éclat naturel apparaît dès le lendemain.
    2. Beaucoup passent de la version 100 à 300, à utiliser tous les 3 jours le soir avec une crème régénérante.
    
    **[Résumé par préoccupation cutanée]**
    1. 100% des Coréens ayant des problèmes de Soin anti-rougeurs sont satisfaits.
    2. Les Coréens ayant des problèmes de Soin anti-imperfections l'ont le plus acheté.
    
    ---
    
    ### 2. Parteon Noscanine Trouble Serum 30ml
    
    **[Résumé général des avis]**
    1. L'acné et les petits boutons s'apaisent, la peau est calmée et la texture affinée.
    2. Doux et sans irritation, à appliquer matin et soir avec l'ampoule Parteon.
    
    **[Résumé par préoccupation cutanée]**
    1. 98% des Coréens ayant des problèmes de Soin anti-rougeurs sont satisfaits.
    2. Les Coréens ayant des problèmes de Soin anti-imperfections l'ont le plus acheté.
    
    ---
    
    ### 3. Goodal Green Tangerine Vita C Serum 30ml
    
    **[Résumé général des avis]**
    1. Les taches s'estompent et le teint s'éclaircit, une utilisation régulière affine le grain de peau.
    2. Doux et hydratant, plus efficace appliqué le soir avec une crème.
    
    **[Résumé par préoccupation cutanée]**
    1. 100% des Coréens ayant des problèmes de Soin anti tache sont satisfaits.
    2. Les Coréens ayant des problèmes de Soin anti tache l'ont le plus acheté.
    
    ---
    
    ## 파일 구조
    
    ```
    test_results_bea1/
    ├── 00_테스트결과_요약.md     ← 현재 파일
    ├── 01_VT_리들샷300.md
    ├── 02_파티온_노스카나인.md
    ├── 03_구달_청귤비타C.md
    └── product_data.json        ← 원본 데이터
    ```
    
    ---
    
    ## 품질 체크리스트
    
    | 항목 | VT 리들샷 | 파티온 | 구달 |
    | --- | --- | --- | --- |
    | 리뷰 전반 요약 자연스러움 | O | O | O |
    | 피부고민 요약 정확성 | O | O | O |
    | 금칙어 미포함 | O | O | O |
    | 프랑스어 번역 자연스러움 | O | O | O |
    
    ---
    
    ## 비고
    
    - 모든 상품의 전체 텍스트 리뷰를 분석하여 요약 생성
    - 피부고민 카테고리는 피어나 5가지 분류 기준 적용
    - 대표피부고민(1): 만족도가 가장 높은 카테고리
    - 대표피부고민(2): 리뷰 수가 가장 많은 카테고리
    
    ```
    
- **2차 2026년 1월 16일**
    
    코멘트 : 리뷰 수가 적을 때, 피부 고민 문장은 택일하는 방향으로 정리 필요. 메이크업 상품 프롬프트 정의
    
    https://zigzag.kr/catalog/products/111593562 
    
    https://zigzag.kr/catalog/products/113771424
    
    https://zigzag.kr/catalog/products/109822418
    
    ```markdown
    ## 인사이트
    
    ### 리뷰 수에 따른 분석 품질
    | 리뷰 규모 | 분석 신뢰도 | 특징 |
    |----------|:----------:|------|
    | 소 (~30개) | 중간 | 개별 리뷰 영향력 큼 |
    | 중 (~500개) | 높음 | 패턴 파악 용이, 피부고민별 분석 가능 |
    | 대 (~7,000개+) | 매우 높음 | 통계적 신뢰도 높음 |
    
    ### 프롬프트 개선점
    1. **메이크업 제품 대응**: 피부고민 카테고리가 아닌 별도 분류 필요
    2. **리뷰 수 적은 상품**: 보수적 문구 사용
    3. **금칙어 검증**: 색상 관련 표현 추가 테스트 필요
    
    ```
    
    ```markdown
    ## 테스트 샘플 개요
    
    | 구분 | 브랜드/상품명 | 전체 리뷰 | 텍스트 리뷰 | 만족도 | 지그재그 URL |
    |:----:|-------------|:--------:|:----------:|:-----:|------------|
    | 하 | 파파레서피 티트리 컨트롤 패드 | 22개 | 17개 | 95% | https://zigzag.kr/catalog/products/111593562 |
    | 중 | 코스알엑스 더 레티놀 0.1 크림 | 542개 | 435개 | 96% | https://zigzag.kr/catalog/products/113771424 |
    | 상 | 스킨푸드 패드 12종 | 13,246개 | 9,701개 | 99% | https://zigzag.kr/catalog/products/109822418 |
    
    ### 파파레서피 티트리 컨트롤 패드 KO (한국어)
    
    [리뷰 전반 요약]
    티트리 성분으로 트러블이 잘 가라앉고 진정 효과가 좋아요.
    패드가 얇아서 팩처럼 붙여 사용하기 좋고 자극 없이 순해요.
    
    [피부 고민 요약]
    안티에이징 고민이 있는 한국인이 100% 만족했어요.
    트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ### 파파레서피 티트리 컨트롤 패드 FR (프랑스어)
    
    [Résumé des avis]
    Le tea tree apaise efficacement les imperfections et offre un effet calmant remarquable.
    Les pads ultra-fins s'utilisent comme un masque, doux et sans irritation.
    
    [Résumé par préoccupation]
    100% des utilisateurs soucieux de l'anti-âge sont satisfaits.
    Ce produit est le plus acheté par ceux qui souhaitent traiter les imperfections.
    
    ### 코스알엑스 더 레티놀 0.1 크림 KO (한국어)
    
    [리뷰 전반 요약]
    모공이 줄어들고 피부결이 매끈해지는 효과가 있어요.
    소량씩 격일로 밤에 사용하고, 냉장보관하면 자극 없이 순하게 사용할 수 있어요.
    
    [피부 고민 요약]
    안티에이징 고민이 있는 한국인이 100% 만족했어요.
    트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ### 코스알엑스 더 레티놀 0.1 크림 FR (프랑스어)
    
    [Résumé des avis]
    Les pores sont visiblement réduits et le grain de peau devient plus lisse.
    Utiliser une petite quantité un soir sur deux, conserver au frais pour une application douce et sans irritation.
    
    [Résumé par préoccupation]
    100% des utilisateurs soucieux de l'anti-âge sont satisfaits.
    Ce produit est le plus acheté par ceux qui souhaitent traiter les imperfections.
    
    ### 스킨푸드 패드 12종 KO (한국어)
    
    [리뷰 전반 요약]
    촉촉하고 진정 효과가 좋아서 재재재구매하는 분들이 많아요.
    팩처럼 붙여서 사용하거나 드라이할 때 붙이면 건조해지지 않고 수분 충전이 잘 돼요.
    
    [피부 고민 요약]
    보습 & 영양 고민이 있는 한국인이 99% 만족했어요.
    트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ### 스킨푸드 패드 12종 FR (프랑스어)
    
    [Résumé des avis]
    Hydratation intense et effet apaisant remarquable, un produit racheté encore et encore.
    S'utilise comme un masque ou pendant le séchage des cheveux pour une hydratation optimale sans dessèchement.
    
    [Résumé par préoccupation]
    99% des utilisateurs soucieux de l'hydratation et nutrition sont satisfaits.
    Ce produit est le plus acheté par ceux qui souhaitent traiter les imperfections.
    
    ```
    
- **3차 2026년 1월 19일**
    
    ```python
    ## 테스트 상품 개요
    
    | 구분 | 상품명 | 리뷰 수 | 텍스트 리뷰 | 만족도 |
    | --- | --- | --- | --- | --- |
    | 상위 | 에스트라 아토베리어 365 크림 80ml | 6,878개 | 4,435개 | 98.8% |
    | 중위 | 코스알엑스 더 레티놀 0.1 크림 20ml | 542개 | 435개 | 95.6% |
    | 하위 | 코스알엑스 더 나이아신아마이드 15 세럼 20ml | 296개 | 185개 | 96.3% |
    
    ---
    
    ## 요약 결과
    
    ### 1. 에스트라 아토베리어 365 크림 80ml
    
    **[리뷰 전반 요약]**
    1. 순하고 보습력이 뛰어나 민감한 피부도 자극 없이 촉촉하게 사용할 수 있어요.
    2. 겨울철 필수 크림으로 소량만 발라도 오래 유지되고, 밤에 바르면 다음 날 피부에 광이 나요.
    
    **[피부 고민 요약]**
    1. 트러블 케어 고민이 있는 한국인이 99% 만족했어요.
    2. 미백 & 잡티 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ### 2. 코스알엑스 더 레티놀 0.1 크림 20ml
    
    **[리뷰 전반 요약]**
    1. 주름과 모공 개선에 효과가 있고, 다음 날 피부가 부드럽고 탱탱해져요.
    2. 0.1% 저농도라 자극이 적어 레티놀 입문용으로 좋고, 다른 크림과 섞어 바르면 더 순해요.
    
    **[피부 고민 요약]**
    1. 안티에이징 고민이 있는 한국인이 100% 만족했어요.
    2. 트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ### 3. 코스알엑스 더 나이아신아마이드 15 세럼 20ml
    
    **[리뷰 전반 요약]**
    1. 트러블과 피지 조절에 효과가 있고, 꾸준히 사용하면 모공이 덜 눈에 띄게 돼요.
    2. 흡수가 빠르고 밀림이 없어서 밤 스킨케어 루틴에 추가하기 좋아요.
    
    **[피부 고민 요약]**
    1. 진정 & 홍조 케어 고민이 있는 한국인이 98% 만족했어요.
    2. 트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ## 프랑스어 번역 결과
    
    ### 1. Aestura Atobarrier 365 Cream 80ml
    
    **[Résumé général des avis]**
    1. Douce et très hydratante, elle convient parfaitement aux peaux sensibles sans aucune irritation.
    2. Crème indispensable en hiver, une petite quantité suffit pour une hydratation longue durée. Appliquée le soir, elle donne un éclat naturel au réveil.
    
    **[Résumé par préoccupation cutanée]**
    1. 99% des Coréens ayant des problèmes de Soin anti-imperfections sont satisfaits.
    2. Les Coréens ayant des problèmes de Soin anti tache l'ont le plus acheté.
    
    ---
    
    ### 2. COSRX The Retinol 0.1 Cream 20ml
    
    **[Résumé général des avis]**
    1. Efficace contre les rides et les pores dilatés, la peau est plus douce et rebondie dès le lendemain.
    2. Avec une concentration de 0.1%, elle est peu irritante et idéale pour débuter le rétinol. Mélangée à une crème hydratante, elle devient encore plus douce.
    
    **[Résumé par préoccupation cutanée]**
    1. 100% des Coréens ayant des problèmes de Soin anti-rides & anti-âge sont satisfaits.
    2. Les Coréens ayant des problèmes de Soin anti-imperfections l'ont le plus acheté.
    
    ---
    
    ### 3. COSRX The Niacinamide 15 Serum 20ml
    
    **[Résumé général des avis]**
    1. Efficace pour réguler les imperfections et le sébum, une utilisation régulière réduit visiblement les pores.
    2. Absorption rapide sans effet collant, parfait pour intégrer à votre routine du soir.
    
    **[Résumé par préoccupation cutanée]**
    1. 98% des Coréens ayant des problèmes de Soin anti-rougeurs sont satisfaits.
    2. Les Coréens ayant des problèmes de Soin anti-imperfections l'ont le plus acheté.
    
    ---
    
    ## 피부고민 통계 상세
    
    ### 에스트라 아토베리어 365 크림
    | 피부고민 카테고리 | 리뷰 수 | 만족도 |
    | --- | --- | --- |
    | 트러블 케어 | 1,723명 | 99% |
    | 미백 & 잡티 케어 | 1,708명 | 99% |
    | 진정 & 홍조 케어 | 1,185명 | 99% |
    | 보습 & 영양 | 1,116명 | 99% |
    | 안티에이징 | 811명 | 99% |
    
    ### 코스알엑스 더 레티놀 0.1 크림
    | 피부고민 카테고리 | 리뷰 수 | 만족도 |
    | --- | --- | --- |
    | 트러블 케어 | 172명 | 98% |
    | 미백 & 잡티 케어 | 165명 | 97% |
    | 진정 & 홍조 케어 | 115명 | 99% |
    | 보습 & 영양 | 110명 | 98% |
    | 안티에이징 | 103명 | 100% |
    
    ### 코스알엑스 더 나이아신아마이드 15 세럼
    | 피부고민 카테고리 | 리뷰 수 | 만족도 |
    | --- | --- | --- |
    | 트러블 케어 | 102명 | 96% |
    | 미백 & 잡티 케어 | 91명 | 96% |
    | 보습 & 영양 | 63명 | 95% |
    | 진정 & 홍조 케어 | 48명 | 98% |
    | 안티에이징 | 44명 | 98% |
    
    ---
    
    ## 품질 체크리스트
    
    | 항목 | 에스트라 | 레티놀 | 나이아신아마이드 |
    | --- | --- | --- | --- |
    | 리뷰 전반 요약 자연스러움 | O | O | O |
    | 피부고민 요약 정확성 | O | O | O |
    | 금칙어 미포함 | O | O | O |
    | 프랑스어 번역 자연스러움 | O | O | O |
    
    ---
    
    ## 비고
    
    - 모든 상품의 텍스트 리뷰를 분석하여 요약 생성
    - 피부고민 카테고리는 피어나 5가지 분류 기준 적용
    - 대표피부고민(1): 만족도가 가장 높은 카테고리
    - 대표피부고민(2): 리뷰 수가 가장 많은 카테고리
    - 대표피부고민(1)과 (2)가 동일할 경우, (2)는 두 번째로 많은 카테고리 사용
    ```
    
- **4차 2026년 1월 19일 (리뷰 수 적은 상품 샘플링)**
    - 코멘트 : 리뷰 요약에 한국어 축약어, 신조어 등의 표현 딕셔너리 생성 필요
        - 닦토 / 팩토 / 1일 1팩 / 퍼스널 컬러 (팔레트) 등의 한국 유행, 축약어, 최신 언어가 요약본에 포함 되었으나, 번역시 뉘앙스 전달되지 않음
    
    ```python
     | 구간       | 추천 상품                          | 총 리뷰 | 텍스트 리뷰 | 텍스트 비율 |
      |----------|--------------------------------|------|--------|---
      -----|
      | 20개 미만   | 썸바이미 AHA BHA PHA 30 데이즈 미라클 토너 |  14개  | 14개    | 100%   |
      | 20-50개   | 바이오던스 겔 토너 패드 60매                | 29개  | 28개    | 97%    |
      | 50-100개  | 메디힐 비타민씨 에센셜 마스크 10매           |  78개  | 64개    | 82%    |
      | 100-200개 | 토리든 비타C 브라이트닝 흔적 토닝 패드 70매     | 108개 | 103개   | 95%    |
    
      ---
      
      **### 1. 썸바이미 아하 바하 파하 30 데이즈 미라클 토너 한국어 (KR)**
    
    	**[리뷰 전반 요약]**
    	1. 각질 제거와 피부결 정돈에 효과가 있고, 바르면 시원한 느낌이 나요.
    	2. 닦토로 일주일에 3-4번 사용하면 피부결이 매끈해져요.
    	
    	**[피부 고민 요약]**
    	1. 트러블 케어 고민이 있는 한국인이 100% 만족했어요.
    	2. 트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    	
    	---
    	
    	**### 1. 썸바이미 아하 바하 파하 30 데이즈 미라클 토너 프랑스어 (FR)**
    	
    	**[Résumé général des avis]**
    	1. Efficace pour éliminer les cellules mortes et affiner le grain de peau, avec une sensation de fraîcheur à l'application.
    	2. Utilisé 3-4 fois par semaine en lotion tonique, il rend la peau visiblement plus lisse.
    	
    	**[Résumé par préoccupation cutanée]**
    	1. 100% des Coréens ayant des problèmes de Soin anti-imperfections sont satisfaits.
    	2. Les Coréens ayant des problèmes de Soin anti-imperfections l'ont le plus acheté.
    	
    	---
    	
    	**### 2. 바이오던스 겔 토너 패드 60매 (KR)** 
    	
    	
    	**[리뷰 전반 요약]**
    	1. 촉촉하고 진정 효과가 뛰어나며, 민감한 피부도 자극 없이 사용할 수 있어요.
    	2. 겔 타입이라 밀착력이 좋고, 15-20분 팩처럼 사용하면 수분이 꽉 차요.
    	
    	**[피부 고민 요약]**
    	1. 트러블 케어 고민이 있는 한국인이 100% 만족했어요.
    	2. 트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
     **### 2. 바이오던스 겔 토너 패드 60매 (FR)** 
    
    		**[Résumé général des avis]**
    		1. Très hydratant avec un excellent effet apaisant, convient parfaitement aux peaux sensibles sans irritation.
    		2. La texture gel offre une excellente adhérence, utilisé comme masque pendant 15-20 minutes pour une hydratation intense.
    		
    		**[Résumé par préoccupation cutanée]**
    		1. 100% des Coréens ayant des problèmes de Soin anti-imperfections sont satisfaits.
    		2. Les Coréens ayant des problèmes de Soin anti-imperfections l'ont le plus acheté.
    	  
    	  
    ---
    
    	### 3. 메디힐 비타민씨 에센셜 마스크 10매 한국어 (KR)
    
    		**[리뷰 전반 요약]**
    		1. 촉촉하고 얼굴이 밝아지며, 잡티 개선에 도움이 돼요.
    		2. 에센스 양이 넉넉하고, 1일 1팩 데일리 사용에 적합해요.
    		
    		**[피부 고민 요약]**
    		1. 진정 & 홍조 케어 고민이 있는 한국인이 100% 만족했어요.
    		2. 미백 & 잡티 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    	### 3. 메디힐 비타민씨 에센셜 마스크 10매프랑스어 (FR)
    
    		**[Résumé général des avis]**
    		1. Hydratant et éclaircissant, il aide à atténuer les taches pigmentaires.
    		2. Généreusement imbibé d'essence, parfait pour une utilisation quotidienne.
    		
    		**[Résumé par préoccupation cutanée]**
    		1. 100% des Coréens ayant des problèmes de Soin anti-rougeurs sont satisfaits.
    		2. Les Coréens ayant des problèmes de Soin anti tache l'ont le plus acheté.
    		
    		
    		
    	--- 
    	
    	 ### 4. 토리든 셀메이징 비타 C 브라이트닝 흔적 토닝 패드 70매 한국어 (KR) 
    	 
    	 
    	 ** [리뷰 전반 요약]**
    		1. 잡티와 흔적 개선에 효과가 있고, 피부톤이 밝아지며 촉촉해져요.
    		2. 양면 듀얼 패드로 거즈면은 닦토, 겔면은 팩토로 활용하기 좋아요.
    		
    		**[피부 고민 요약]**
    		1. 미백 & 잡티 케어 고민이 있는 한국인이 100% 만족했어요.
    		2. 트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    		
    ---
    
    		### 4. 토리든 셀메이징 비타 C 브라이트닝 흔적 토닝 패드 70매 프랑스어 (FR)
    		
    		**[Résumé général des avis]**
    		1. Efficace pour atténuer les taches et les marques, éclaircit le teint tout en hydratant.
    		2. Pad double face : côté gaze pour nettoyer, côté gel pour un effet masque.
    		
    		**[Résumé par préoccupation cutanée]**
    		1. 100% des Coréens ayant des problèmes de Soin anti tache sont satisfaits.
    		2. Les Coréens ayant des problèmes de Soin anti-imperfections l'ont le plus acheté.
    ```
    
- **5차 2026년 1월 19일 (메이크업 상품 샘플링 - 프롬프트 분리 전)**
    - 코멘트 :  피부 고민 요약 걷어내기 → 어떠한 정보 전달도 되지 않음
    
    ```python
    ###  1. 울트라 파워프루프 마스카라 (3종 택1) 한국어 (KR)
    
    **[리뷰 전반 요약]**
    1. 번지지 않고 지속력이 좋으며, 속눈썹 컬 고정력이 뛰어나요.
    2. 워터프루프라 한여름에도 안 번지고, 가닥가닥 볼륨감 있게 발라져요.
    
    **[피부 고민 요약]**
    1. 트러블 케어 고민이 있는 한국인이 100% 만족했어요.
    2. 미백 & 잡티 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ###  1. 울트라 파워프루프 마스카라 (3종 택1)  프랑스어 (FR)
    
    **[Résumé général des avis]**
    1. Ne coule pas avec une excellente tenue, maintient parfaitement la courbure des cils.
    2. Waterproof, ne bave pas même en été, s'applique avec un effet volume naturel.
    
    **[Résumé par préoccupation cutanée]**
    1. 100% des Coréens ayant des problèmes de Soin anti-imperfections sont satisfaits.
    2. Les Coréens ayant des problèmes de Soin anti tache l'ont le plus acheté.
    
    ---
    
    ### 2. 미샤 섀도우 팔레트 한국어 (KR)
    
    **[리뷰 전반 요약]**
    1. 발색력이 좋고 그라데이션이 쉬우며, 자글자글한 펄이 예뻐요.
    2. 초미니 사이즈라 휴대하기 편하고, 손가락으로 슬슥 발라도 자연스럽게 발색돼요.
    
    **[피부 고민 요약]**
    1. 진정 & 홍조 케어 고민이 있는 한국인이 100% 만족했어요.
    2. 트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ### 2. 미샤 섀도우 팔레트  프랑스어 (FR)
    
    **[Résumé général des avis]**
    1. Pigmentation excellente avec un dégradé facile à réaliser, les paillettes fines sont magnifiques.
    2. Format ultra-mini pratique à transporter, s'applique naturellement même du bout des doigts.
    
    **[Résumé par préoccupation cutanée]**
    1. 100% des Coréens ayant des problèmes de Soin anti-rougeurs sont satisfaits.
    2. Les Coréens ayant des problèmes de Soin anti-imperfections l'ont le plus acheté.
    
    ---
    
    ### 3. 페리페라 립글로스 한국어 (KR)
    
    **[리뷰 전반 요약]**
    1. 광택감이 예쁘게 올라오고, 착색 없이 자연스러운 색감이에요.
    2. 브러쉬 팁이라 발림성이 부드럽고, 립밤 위에 레이어드해서 사용하기 좋아요.
    
    **[피부 고민 요약]**
    1. 미백 & 잡티 케어 고민이 있는 한국인이 98% 만족했어요.
    2. 미백 & 잡티 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ### 3. 페리페라 립글로스 프랑스어 (FR)
    
    **[Résumé général des avis]**
    1. Joli effet brillant avec une couleur naturelle sans tacher les lèvres.
    2. L'applicateur pinceau offre une application douce, idéal à superposer sur un baume à lèvres.
    
    **[Résumé par préoccupation cutanée]**
    1. 98% des Coréens ayant des problèmes de Soin anti tache sont satisfaits.
    2. Les Coréens ayant des problèmes de Soin anti tache l'ont le plus acheté.
    
    ---
    
    ### 4, 페리페라 무드 팔레트 한국어 (KR)
    
    **[리뷰 전반 요약]**
    1. 퍼스널컬러별로 딱 맞는 색 구성이고, 발색력과 지속력이 좋아요.
    2. 슬림한 디자인에 음영/베이스/애교살 가이드가 있어서 초보도 쉽게 사용해요.
    
    **[피부 고민 요약]**
    1. 트러블 케어 고민이 있는 한국인이 98% 만족했어요.
    2. 트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ### 4. 페리페라 무드 팔레트 프랑스어 (FR)
    
    **[Résumé général des avis]**
    1. Palette aux couleurs parfaitement adaptées à chaque colorimétrie, avec une excellente pigmentation et tenue.
    2. Design slim avec guide pour ombre/base/aegyo-sal, facile à utiliser même pour les débutants.
    
    **[Résumé par préoccupation cutanée]**
    1. 98% des Coréens ayant des problèmes de Soin anti-imperfections sont satisfaits.
    2. Les Coréens ayant des problèmes de Soin anti-imperfections l'ont le plus acheté.
    ```
    
- **6차 2026년 1월 19일 (메이크업 상품 샘플링 ver2 - 프롬프트 1차 분리)**
    
    ```python
    ### 1. 삐아_아이라이너 (KR) 
    
    **[만족도 요약]**
    실제로 제품을 사용한 한국인 11,827명 중 95.6%가 만족했어요.
    
    **[리뷰 전반 요약]**
    1. 발색이 좋고 번지지 않으며, 픽싱 후 물이 닿아도 지워지지 않아요.
    2. 애교살 밝히는 용도로 인기가 많고, 26가지 컬러 중 퍼스널컬러에 맞게 선택해서 사용해요.
    
    ---
    
    ### 1. 삐아_아이라이너 프랑스어 (FR)
    
    **[Résumé de satisfaction]**
    95.6% des 11 827 Coréens ayant utilisé ce produit sont satisfaits.
    
    **[Résumé général des avis]**
    1. Excellente pigmentation sans bavures, résiste même à l'eau une fois fixé.
    2. Très populaire pour illuminer l'aegyo-sal, à choisir parmi 26 teintes selon sa colorimétrie.
    
    ### 2. 토니모리_틴트 한국어 (KR)
    
    **[만족도 요약]**
    실제로 제품을 사용한 한국인 8,942명 중 93.5%가 만족했어요.
    
    **[리뷰 전반 요약]**
    1. 착색이 진하고 지속력이 좋으며, 아침에 발라도 오후까지 유지돼요.
    2. 퍼스널컬러에 따라 색상 선택이 중요하고, 베이스립으로 자주 사용해요.
    
    ---
    
    ###  2. 토니모리_틴트 프랑스어 (FR)
    
    **[Résumé de satisfaction]**
    93.5% des 8 942 Coréens ayant utilisé ce produit sont satisfaits.
    
    **[Résumé général des avis]**
    1. Pigmentation intense avec une excellente tenue, reste en place du matin jusqu'à l'après-midi.
    2. Important de choisir la teinte selon sa colorimétrie, souvent utilisé comme base pour les lèvres.
    
    ---
    
    ### 3. 데이지크_팔레트 (KR) 
    
    **[만족도 요약]**
    실제로 제품을 사용한 한국인 6,015명 중 97.1%가 만족했어요.
    
    **[리뷰 전반 요약]**
    1. 발색력이 좋고 색감이 자연스러우며, 그라데이션하기 쉬워요.
    2. 뉴트럴한 컬러 구성이라 데일리 메이크업에 적합하고, 웜톤/쿨톤 모두 사용 가능해요.
    
    ---
    
    ### 3. 데이지크_팔레트 (FR) 
    
    **[Résumé de satisfaction]**
    97.1% des 6 015 Coréens ayant utilisé ce produit sont satisfaits.
    
    **[Résumé général des avis]**
    1. Excellente pigmentation avec des couleurs naturelles, dégradé facile à réaliser.
    2. Palette neutre parfaite pour un maquillage quotidien, convient aux tons chauds comme froids.
    
    --- 
    
    ### 4. 퓌_푸딩팟 (KR)
    
    **[만족도 요약]**
    실제로 제품을 사용한 한국인 3,221명 중 94.8%가 만족했어요.
    
    **[리뷰 전반 요약]**
    1. 색감이 예쁘고 뽀송한 매트 질감이라 여러 통째 재구매하는 분들이 많아요.
    2. 단독 사용이나 베이스립으로 활용하기 좋고, 블러셔와 함께 사용하면 더 예뻐요.
    
    ---
    
    ### 4. 퓌_푸딩팟 프랑스어 (FR)
    
    **[Résumé de satisfaction]**
    94.8% des 3 221 Coréens ayant utilisé ce produit sont satisfaits.
    
    **[Résumé général des avis]**
    1. Jolies couleurs avec une texture mate veloutée, beaucoup rachètent plusieurs pots.
    2. Parfait seul ou en base pour les lèvres, encore plus joli associé à un blush.
    
    ---
    
    ### 5. 프라임 프라이머 피니쉬 파우더 (KR)
    
    **[만족도 요약]**
    실제로 제품을 사용한 한국인 1,812명 중 98.3%가 만족했어요.
    
    **[리뷰 전반 요약]**
    1. 입자가 곱고 유분기를 잘 잡아주며, 화장 지속력이 오래가요.
    2. 베이킹 메이크업에 적합하고, 브러쉬로 얼굴 전체에 톡톡 발라주면 좋아요.
    
    ---
    
    ### 5. 프라임 프라이머 피니쉬 파우더 프랑스어 (FR)
    
    **[Résumé de satisfaction]**
    98.3% des 1 812 Coréens ayant utilisé ce produit sont satisfaits.
    
    **[Résumé général des avis]**
    1. Texture ultra-fine qui matifie parfaitement, tenue longue durée du maquillage.
    2. Idéal pour le baking, à appliquer au pinceau sur l'ensemble du visage par petites touches.
    
    ```
    
- **7차 2026년 1월 19일 (전체 상품)**
    
    ```python
    ### 1. 스킨푸드 패드 12종 한국어 (KR)
    
    **[리뷰 전반 요약]**
    1. 촉촉하고 진정 효과가 좋아 홍조 민감피부도 자극 없이 사용할 수 있어요.
    2. 당근패드와 감자패드가 가장 인기이고, 팩처럼 붙여서 사용하면 수분 충전이 잘 돼요.
    
    **[피부 고민 요약]**
    1. 보습 & 영양 고민이 있는 한국인이 99% 만족했어요.
    2. 트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ### 1. 스킨푸드 패드 12종 프랑스어 (FR)
    
    **[Résumé général des avis]**
    1. Très hydratant avec un excellent effet apaisant, convient parfaitement aux peaux sensibles sujettes aux rougeurs.
    2. Les pads Carotte et Pomme de terre sont les plus populaires, à utiliser comme un masque pour une hydratation intense.
    
    **[Résumé par préoccupation cutanée]**
    1. 99% des Coréens soucieux de l'hydratation et nutrition sont satisfaits.
    2. Ce produit est le plus acheté par ceux qui souhaitent traiter les imperfections.
    
    ---
    
    ### 2. 페리페라 잉크 무드 글로이 틴트 한국어 (KR)
    
    **[만족도 요약]**
    실제로 제품을 사용한 한국인 10,380명 중 96.3%가 만족했어요.
    
    **[리뷰 전반 요약]**
    1. 발색이 자연스럽고 착색이 예뻐서 데일리로 사용하기 좋아요.
    2. 퍼스널컬러별로 색상이 다양해서 본인 톤에 맞는 색을 찾기 쉽고, 재구매하는 분들이 많아요.
    
    ---
    
    ### 2. 페리페라 잉크 무드 글로이 틴트 프랑스어 (FR)
    
    **[Résumé de satisfaction]**
    96.3% des 10 380 Coréens ayant utilisé ce produit sont satisfaits.
    
    **[Résumé général des avis]**
    1. Pigmentation naturelle avec une belle tenue, parfait pour un usage quotidien.
    2. Large gamme de teintes adaptées à chaque colorimétrie, beaucoup rachètent ce produit.
    
    ---
    
    ### 3. 바이오던스 겔 토너 패드 한국어 (KR)
    
    **[리뷰 전반 요약]**
    1. 촉촉하고 진정 효과가 뛰어나며, 얼굴이 울긋불긋할 때 사용하면 가라앉아요.
    2. 겔 토너라 밀착력이 좋고, 15-20분 팩처럼 붙여서 사용하면 수분이 꽉 차요.
    
    **[피부 고민 요약]**
    트러블 케어 고민이 있는 한국인이 100% 만족했어요.
    
    ---
    
    ### 3. 바이오던스 겔 토너 패드 프랑스어 (FR)
    
    **[Résumé général des avis]**
    1. Très hydratant avec un excellent effet apaisant, calme les rougeurs et irritations.
    2. La texture gel offre une excellente adhérence, utilisé comme masque pendant 15-20 minutes pour une hydratation intense.
    
    **[Résumé par préoccupation cutanée]**
    100% des Coréens ayant des problèmes de Soin anti-imperfections sont satisfaits.
    
    ---
    
    ### 4. 썸바이미 아하바하파하 30데이즈 미라클 토너 한국어 (KR)
    
    **[리뷰 전반 요약]**
    1. 각질 제거와 피지 조절에 효과가 있고, 바르면 시원한 느낌이 나요.
    2. 닦토로 일주일에 3-4번 사용하면 피부결이 매끈해져요.
    
    **[피부 고민 요약]**
    트러블 케어 고민이 있는 한국인이 100% 만족했어요.
    
    ---
    
    ### 4. 썸바이미 아하바하파하 30데이즈 미라클 토너 프랑스어 (FR)
    
    **[Résumé général des avis]**
    1. Efficace pour éliminer les cellules mortes et réguler le sébum, avec une sensation de fraîcheur à l'application.
    2. Utilisé 3-4 fois par semaine en lotion tonique exfoliante, il rend la peau visiblement plus lisse.
    
    **[Résumé par préoccupation cutanée]**
    100% des Coréens ayant des problèmes de Soin anti-imperfections sont satisfaits.
    
    ---
    
    ### 5. VT PDRN 텐션 토너 패드 한국어 (KR)
    
    **[리뷰 전반 요약]**
    1. 촉촉하고 보습이 잘 되며, 패드가 쫙쫙 늘어나서 팩처럼 붙이기 편해요.
    2. 머리 말릴 때 붙여놓으면 피부가 쫀쫀해지고, 리프팅 효과도 느껴져요.
    
    **[피부 고민 요약]**
    미백 & 잡티 케어 고민이 있는 한국인이 100% 만족했어요.
    
    ---
    
    ### 5. VT PDRN 텐션 토너 패드 프랑스어 (FR)
    
    **[Résumé général des avis]**
    1. Très hydratant, les pads s'étirent facilement pour une application façon masque.
    2. À appliquer pendant le séchage des cheveux pour une peau rebondie avec un effet liftant.
    
    **[Résumé par préoccupation cutanée]**
    100% des Coréens ayant des problèmes de Soin anti tache sont satisfaits.
    
    --- 
    
    ### 6. 아이유닉 센텔라 카밍 젤 크림 한국어 (KR)
    
    **[리뷰 전반 요약]**
    1. 촉촉하고 순해서 지성 피부도 자극 없이 사용할 수 있어요.
    2. 제형이 맑은 편이고 자기 전이나 메이크업 전에 바르기 좋아요.
    
    **[피부 고민 요약]**
    실제로 제품을 사용한 한국인 2명 중 100%가 만족했어요.
    
    ---
    
    ### 6. 아이유닉 센텔라 카밍 젤 크림 프랑스어 (FR)
    
    **[Résumé général des avis]**
    1. Hydratant et doux, convient parfaitement aux peaux grasses sans irritation.
    2. Texture légère et transparente, idéale avant le coucher ou le maquillage.
    
    **[Résumé par préoccupation cutanée]**
    100% des 2 Coréens ayant utilisé ce produit sont satisfaits.
    
    ```
    
- **8차 2026년 1월 20일**
    
    [AI_리뷰요약_20260121_수정.xlsx](%5BPDP%20%EB%A6%AC%EB%B7%B0%5D%20%EB%A6%AC%EB%B7%B0%20AI%20%ED%94%84%EB%A1%AC%ED%94%84%ED%8A%B8%20%EC%A0%95%EC%B1%85%20(%ED%85%8C%EC%8A%A4%ED%8A%B8%20%ED%8F%AC%ED%95%A8)/AI_%E1%84%85%E1%85%B5%E1%84%87%E1%85%B2%E1%84%8B%E1%85%AD%E1%84%8B%E1%85%A3%E1%86%A8_20260121_%E1%84%89%E1%85%AE%E1%84%8C%E1%85%A5%E1%86%BC.xlsx)
    
- **9차 2026년 1월 21일**
    
    ```markdown
    ## 요약 결과
    
    ### 1. 메디힐 더마 토너패드 (스킨케어)
    
    **[리뷰 전반 요약]**
    1. 촉촉하고 진정 효과가 좋아서 민감한 피부도 자극 없이 사용할 수 있어요.
    2. 패드가 얇아서 팩처럼 붙여서 사용하기 좋고, 아침에 머리 말리면서 붙여두면 화장이 잘 먹어요.
    
    **[피부 고민 요약]**
    1. 보습 & 영양 고민이 있는 한국인이 98% 만족했어요.
    2. 트러블 케어 고민이 있는 한국인이 가장 많이 구매했어요.
    
    ---
    
    ### 2. 롬앤 글래스팅 멜팅 밤 (메이크업)
    
    **[만족도 요약]**
    실제로 제품을 사용한 한국인 4,598명 중 95.1%가 만족했어요.
    
    **[리뷰 전반 요약]**
    1. 촉촉하고 발림성이 좋으며, 자연스러운 색감이라 생얼에 바르기 좋아요.
    2. 퍼스널컬러별로 색상이 다양해서 베이스 립이나 틴트 위에 덧바르기 좋아요.
    
    ---
    
    ## 프랑스어 번역 결과
    
    ### 1. Mediheal Derma Toner Pad 100 sheets + Refill 100 sheets
    
    **[Résumé général des avis]**
    1. Très hydratant avec un excellent effet apaisant, convient parfaitement aux peaux sensibles sans irritation.
    2. Les pads ultra-fins s'utilisent comme un masque, parfaits à appliquer pendant le séchage des cheveux pour un maquillage impeccable.
    
    **[Résumé par préoccupation cutanée]**
    1. 98% des Coréens soucieux de l'hydratation et nutrition sont satisfaits.
    2. Ce produit est le plus acheté par ceux qui souhaitent traiter les imperfections.
    
    ---
    
    ### 2. Rom&nd Glasting Melting Balm
    
    **[Résumé de satisfaction]**
    95.1% des 4 598 Coréens ayant utilisé ce produit sont satisfaits.
    
    **[Résumé général des avis]**
    1. Texture onctueuse et application douce, couleur naturelle parfaite pour un look sans maquillage.
    2. Large gamme de teintes adaptées à chaque colorimétrie, idéal en base ou en finition sur un tint.
    ```