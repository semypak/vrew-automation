"""
대본 생성 모듈
- 키워드 → 시놉시스 → 챕터 → 전체 대본 생성
- Claude API 사용
- 건강채널 / 북한채널 프롬프트 지원
"""

import os
import json
from typing import Optional

# API 키 설정
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

def set_api_key(api_key: str):
    """API 키 설정"""
    global ANTHROPIC_API_KEY
    ANTHROPIC_API_KEY = api_key


# ============================================================
# 채널별 마스터 프롬프트
# ============================================================

HEALTH_CHANNEL_PROMPT = """# 마스터 프롬프트 --- 건강전문가 1인칭 롱폼 스크립트 생성

각종 이모티콘을 써서 스크립트를 예쁘고 정돈되게 작성해줘

다음 조건을 **모두** 지켜 **유튜브 롱폼 스크립트**를 작성하라.

주제: 【{keyword}】

타깃: 중장년·시니어 시청자

화자 설정: **의사가 아닌 건강 관련 분야 전문가로 되도록이면 남성 전문가로 설정해줘**(예: 노년영양학 연구자, 생활습관 코치, 재활운동 전문가, 노년치과 위생사 출신 컨설턴트 등). 직함은 과장되게 꾸미지 말고, **경력·검증 가능 활동·현장 경험**으로 설득하라.

## 0) 전역 규칙(절대 위반 금지)
* **작성**: **부드러운 구어체 말투**로 작성
* **시점**: 철저히 **1인칭 내레이션**.
* **금지**: 대사·대본 연출 지시(표정·행동), 특수문자, 영어, 한자.
* **영문 표기**: 전부 **한글**
* **문장 스타일**: 길고 짧은 문장 **리듬 혼합**, 어미 다양화.
* **몰입 장치**: 감정·행동·상황을 **구체 묘사**, 대명사 대신 **이름 직접 호명**.
* **전문성 표현**: 의학 조언은 '치료'가 아닌 **생활습관·행동 변화 중심**. **진단·처방 단정 금지**.
* **출처 언급 방식**: 영어 원문 대신 **한글 기관명·한글화 명칭**으로 서술. 연도·수치·표본 규모는 **한글 숫자**로 표기.

## 1) 서론(최소 천 자, 목표 천이백 자 내외)
1. **후킹 문장**: 시청자가 후킹이 될만큼 강력한 도입부로 시작하기
2. **자기소개 서사**: 이름, 나이, 전공 배경, 실무 경력, 현장 연구·상담 사례 수, 자격·수료 이력 중 **검증 가능한 것 중심**으로 신뢰감 부여.
3. **시청자 초대 멘트(문구 고정)**: "**이 이야기가 도움이 되신다면 구독과 좋아요로 함께해 주세요. 여러분의 건강한 노후를 응원합니다. 궁금하신 점이 있다면 댓글로 남겨주시면 제가 직접 답글로 친절히 도와드리겠습니다.**"

## 2) 본론 --- **네 개 이상 챕터**(각 최소 천오백 자, 목표 이천 자 내외)
각 챕터는 아래 **A~D** 블록을 모두 포함한다.

### 챕터 구성:
**A. 핵심 정보(레퍼런스 기반)**: 최근 연도·기관·표본 규모·핵심 수치를 한글로 명시. 어려운 개념은 **생활 비유**로 풀어 설명.
**B. 공감 질문(최소 한 문장)**: 시청자가 자신의 경험을 즉시 떠올리게 하는 생활 맥락형 질문.
**C. 실행 팁(즉시 적용 가능)**: 시청자가 오늘부터 할 수 있는 단계별·시간대별 행동 제안.
**D. 주의사항**: 흔한 오해와 민간요법의 한계 근거로 반박. 기저 질환·복용 약이 있는 경우의 유의점.

**브릿지 문장**: "지금까지는 ○○를 정리했다. 다음은 △△을 현실에서 적용하는 순서다."처럼 다음 챕터로 자연 연결.

> **사례 규칙(본론 전체에서 단 한 개만 사용, 핵심 챕터에 배치)**
> 길이: 팔백 자 이상 천 자 이하.
> 구성: 초기 상태 → 심리·생활 맥락 → 관찰·상담 과정 → 개입 전후 변화 → 재발 방지.
> 이름 표기: 첫 언급 **성함 전체(예: 김호철님)**, 이후 **이름만(호철님)**.

## 3) 결론(최소 천오백 자, 목표 이천 자 내외)
* 오늘 핵심 요지 **세 가지**로 압축 요약.
* **행동 촉구 문장(고정 문구 포함)**: "**내일 저녁부터 작은 습관 하나만 바꿔보세요. 그 변화가 여러분의 노후 건강을 완전히 달라지게 할 수 있습니다.**"
* 시청자 참여 유도: 오늘의 체크리스트, 일주일 실험 과제, 댓글 약속.

## 4) 출처 정리(스크립트 끝에서 한글로만 표기)

## 5) 마지막 줄에 [공백 포함 글자수] 표기

## 6) 썸네일 프롬프트
스크립트 마지막에 Whisk에서 사용할 수 있는 썸네일 이미지 프롬프트를 영문으로 제작:
Photorealistic portrait, Korean senior expert (age fifty-plus), trustworthy and calm expression, front-facing, chest-up, centered composition. Background subtly implies the topic. 16:9, high resolution. No text, no white coat, no stethoscope."""


NORTH_KOREA_CHANNEL_PROMPT = """# 마스터 프롬프트 --- 북한/탈북 실화 드라마 스크립트 생성

다음 조건을 **모두** 지켜 **유튜브 롱폼 드라마 스크립트**를 작성하라.

주제: 【{keyword}】

타깃: 중장년·시니어 여성 시청자 (50-70대)

## 0) 전역 규칙(절대 위반 금지)
* **작성**: **부드러운 구어체 내레이션**으로 작성
* **시점**: 철저히 **3인칭 전지적 내레이션** (나레이터가 이야기를 들려주는 형식)
* **금지**: 괄호 안 연출 지시(표정·행동), 특수문자, 영어, 한자
* **문장 스타일**: 길고 짧은 문장 **리듬 혼합**, 어미 다양화
* **몰입 장치**: 감정·행동·상황을 **구체 묘사**, 대명사 대신 **이름 직접 호명**
* **감정선**: 시니어 여성이 공감할 수 있는 가족애, 희생, 용서, 희망의 주제

## 1) 서론(최소 팔백 자)
1. **후킹 문장**: 시청자의 마음을 사로잡는 강렬한 도입부
2. **배경 설정**: 시대, 장소, 분위기를 생생하게 묘사
3. **주인공 소개**: 이름, 나이, 상황, 내면의 갈등을 섬세하게 소개
4. **시청자 초대 멘트**: "**이 이야기가 마음에 드신다면 구독과 좋아요로 응원해 주세요. 끝까지 함께해 주시면 감사하겠습니다.**"

## 2) 본론 --- **네 개 이상 챕터**(각 최소 천오백 자)

각 챕터 구성:
* **상황 묘사**: 장소, 날씨, 분위기를 오감으로 묘사
* **인물 심리**: 등장인물의 내면 갈등, 두려움, 희망을 섬세하게
* **갈등과 긴장**: 위기 상황, 선택의 기로, 감정적 충돌
* **대사 (나레이션으로 녹여내기)**: "○○는 ~라고 말했습니다" 형식

**브릿지 문장**: 각 챕터 끝에 다음 챕터로의 자연스러운 연결

## 3) 결론(최소 천 자)
* 이야기의 마무리와 여운
* 등장인물들의 현재 또는 그 후 이야기
* **마무리 멘트**: "**오늘 이야기가 여러분의 마음에 작은 울림이 되었으면 합니다. 다음 이야기도 기대해 주세요.**"

## 4) 마지막 줄에 [공백 포함 글자수] 표기

## 5) 썸네일 프롬프트
스크립트 마지막에 썸네일 이미지 프롬프트를 영문으로 제작:
Cinematic scene, Korean drama style, emotional moment, [주요 장면 묘사], dramatic lighting, film grain, 16:9, high resolution. No text overlay."""


# ============================================================
# 메인 함수들
# ============================================================

def generate_synopsis(keyword: str, genre: str = "드라마", channel_type: str = "drama", used_names: list = None) -> dict:
    """
    키워드로부터 시놉시스 생성 (Claude API 사용)
    
    Args:
        keyword: 주제 키워드
        genre: 장르
        channel_type: "drama", "health", "overseas", "yadam"
        used_names: 이미 사용된 이름 리스트 (중복 방지용)
    
    Returns:
        시놉시스 딕셔너리
    """
    
    if not ANTHROPIC_API_KEY:
        print("[API 키 없음 - 예시 데이터 사용]")
        return _get_example_synopsis(keyword, genre, channel_type)
    
    try:
        import anthropic
        import random
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # 랜덤 시드로 매번 다른 결과 유도
        random_seed = random.randint(1000, 9999)
        
        # 사용된 이름 목록 문자열 생성
        used_names_str = ""
        if used_names and len(used_names) > 0:
            used_names_str = f"""
[절대 금지 - 이미 사용된 이름들]
다음 이름들은 이전 콘텐츠에서 이미 사용되었으므로 절대 사용하지 마세요:
{', '.join(used_names[:50])}

위 이름들과 비슷한 이름도 피해주세요. 완전히 새롭고 독창적인 이름을 만들어주세요.
"""
        
        if channel_type == "health":
            prompt = f"""당신은 한국 시니어(50-70대) 대상 유튜브 건강 콘텐츠 전문 작가입니다.

[중요 - 독창성 규칙]
- 매번 완전히 새로운 전문가 이름과 프로필을 창작하세요
- 흔한 이름(김철수, 이영희 등) 대신 독특하고 기억에 남는 이름을 사용하세요
- 전문가의 배경 스토리를 구체적이고 독창적으로 만드세요
- 이 요청의 랜덤 시드: {random_seed}
{used_names_str}

키워드: {keyword}
장르: {genre}

반드시 아래 JSON 형식으로만 응답하세요:

{{
    "title": "클릭을 유도하는 매력적이고 독창적인 제목",
    "expert_profile": "독창적인 전문가 이름, 구체적 경력(숫자 포함), 독특한 전문 분야",
    "background": "왜 이 주제가 지금 시니어에게 중요한지 시의성 있는 배경 설명",
    "plot": "전체 내용 요약 (핵심 정보 3-4가지, 구체적 수치나 사례 포함)",
    "chapters": [
        "챕터1: 독창적인 제목 - 핵심 내용",
        "챕터2: 독창적인 제목 - 핵심 내용",
        "챕터3: 독창적인 제목 - 핵심 내용",
        "챕터4: 독창적인 제목 - 핵심 내용"
    ],
    "characters": ["전문가 프로필 상세 (구체적 숫자와 경력 포함)"]
}}"""

        elif channel_type == "overseas":
            prompt = f"""당신은 해외 감동 실화 전문 유튜브 콘텐츠 작가입니다.

[중요 - 독창성 규칙]
- 매번 완전히 새로운 인물, 국가, 상황을 창작하세요
- 실제 있을 법한 구체적인 지명, 날짜, 상황을 포함하세요
- 흔한 스토리(입양, 재회)를 피하고 독특한 각도로 접근하세요
- 한국인이 해외에서 겪은 이야기 또는 외국인의 감동 스토리
- 이 요청의 랜덤 시드: {random_seed}
{used_names_str}

키워드: {keyword}
장르: {genre}

반드시 아래 JSON 형식으로만 응답하세요:

{{
    "title": "클릭을 유도하는 감동적이고 독창적인 제목",
    "characters": [
        "독창적인 외국 이름: 나이, 국적, 직업. 구체적인 성격과 배경",
        "독창적인 이름: 나이, 역할. 주인공과의 관계와 갈등",
        "독창적인 이름: 나이, 역할. 스토리의 전환점이 되는 인물",
        "독창적인 이름: 나이, 역할. 결말에 중요한 역할"
    ],
    "background": "구체적인 국가, 도시, 연도를 포함한 배경 (예: 2019년 독일 뮌헨)",
    "plot": "전체 줄거리 요약 (5-7문장, 반전과 감동 포인트 포함)",
    "chapters": [
        "1장: 독창적 제목 - 긴장감 있는 도입",
        "2장: 독창적 제목 - 갈등의 심화",
        "3장: 독창적 제목 - 예상치 못한 전환",
        "4장: 독창적 제목 - 감동적인 결말"
    ]
}}

시니어 여성이 눈물 흘릴 만한 진정성 있는 감동 스토리를 만들어주세요."""

        elif channel_type == "yadam":
            prompt = f"""당신은 한국 전통 야담/기담 전문 유튜브 콘텐츠 작가입니다.

[중요 - 독창성 규칙]
- 매번 완전히 새로운 시대, 지역, 인물을 창작하세요
- 조선시대뿐 아니라 고려, 삼국시대, 근대 등 다양한 시대 배경 활용
- 실제 역사적 사건이나 지명을 창의적으로 활용하세요
- 단순한 귀신 이야기가 아닌 교훈과 반전이 있는 이야기
- 이 요청의 랜덤 시드: {random_seed}
{used_names_str}

키워드: {keyword}
장르: {genre}

반드시 아래 JSON 형식으로만 응답하세요:

{{
    "title": "호기심을 자극하는 독창적이고 신비로운 제목",
    "characters": [
        "독창적인 옛 이름: 나이, 신분(양반/평민/천민 등). 성격과 운명",
        "독창적인 이름: 나이, 역할. 주인공과의 관계",
        "독창적인 이름: 나이, 역할. 초자연적 존재 또는 조력자",
        "독창적인 이름: 나이, 역할. 갈등의 원인이 되는 인물"
    ],
    "background": "구체적인 시대(연호 포함), 지역(실제 지명), 계절과 분위기",
    "plot": "전체 줄거리 요약 (5-7문장, 권선징악 또는 기이한 반전 포함)",
    "chapters": [
        "1장: 독창적 제목 - 기이한 사건의 시작",
        "2장: 독창적 제목 - 진실을 향한 여정",
        "3장: 독창적 제목 - 충격적인 진실",
        "4장: 독창적 제목 - 운명의 결말"
    ]
}}

소름 돋으면서도 교훈이 있는, 시니어가 좋아할 만한 전통 야담을 만들어주세요."""

        else:  # drama (북한/탈북)
            prompt = f"""당신은 한국 시니어(50-70대 여성) 대상 유튜브 드라마 콘텐츠 전문 작가입니다.

[중요 - 독창성 규칙]
- 매번 완전히 새로운 인물 이름을 창작하세요 (리철, 선희 같은 흔한 이름 금지!)
- 북한의 다양한 지역 배경 활용 (함경도뿐 아니라 평안도, 황해도, 양강도 등)
- 1990년대뿐 아니라 다양한 시대 배경 (1980년대, 2000년대, 2010년대 등)
- 탈북 외에도 다양한 스토리 (이산가족, 북한 내부 이야기, 통일 이후 등)
- 이 요청의 랜덤 시드: {random_seed}
{used_names_str}

키워드: {keyword}
장르: {genre}

반드시 아래 JSON 형식으로만 응답하세요:

{{
    "title": "클릭을 유도하는 감동적이고 독창적인 제목 (부제 포함)",
    "characters": [
        "독창적인 북한식 이름: 나이, 직업/신분. 구체적인 성격과 내면의 갈등",
        "독창적인 이름: 나이, 역할. 주인공과의 관계와 감정선",
        "독창적인 이름: 나이, 역할. 스토리에 긴장감을 주는 인물",
        "독창적인 이름: 나이, 역할. 감동을 주는 조력자"
    ],
    "background": "구체적인 연도, 북한의 특정 지역(군/리 단위까지), 시대 상황",
    "plot": "전체 줄거리 요약 (5-7문장, 기승전결과 감동 포인트 포함)",
    "chapters": [
        "1장: 독창적 제목 - 운명의 시작",
        "2장: 독창적 제목 - 갈등의 심화",
        "3장: 독창적 제목 - 결단의 순간",
        "4장: 독창적 제목 - 시련과 고난",
        "5장: 독창적 제목 - 예상치 못한 전환",
        "6장: 독창적 제목 - 희망의 빛",
        "7장: 독창적 제목 - 감동의 재회",
        "8장: 독창적 제목 - 새로운 시작"
    ]
}}

시니어 여성 시청자가 눈물 흘리며 공감할 수 있는 진정성 있는 이야기를 만들어주세요.
다른 유튜브 채널과 차별화되는 독창적인 스토리가 필수입니다!"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        synopsis = json.loads(response_text.strip())
        return synopsis
        
    except Exception as e:
        print(f"[API 호출 오류: {e}]")
        return _get_example_synopsis(keyword, genre, channel_type)


def generate_full_script(synopsis: dict, channel_type: str = "drama") -> list:
    """
    시놉시스로부터 전체 대본 생성 (마스터 프롬프트 적용)
    """
    
    if not ANTHROPIC_API_KEY:
        print("[API 키 없음 - 예시 데이터 사용]")
        return _get_example_script()
    
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # 채널 타입에 따라 마스터 프롬프트 선택
        if channel_type == "health":
            master_prompt = HEALTH_CHANNEL_PROMPT.format(keyword=synopsis.get('title', ''))
        else:
            master_prompt = NORTH_KOREA_CHANNEL_PROMPT.format(keyword=synopsis.get('title', ''))
        
        prompt = f"""{master_prompt}

---

시놉시스 정보:
제목: {synopsis.get('title', '')}
등장인물/전문가: {', '.join(synopsis.get('characters', [])[:4])}
배경: {synopsis.get('background', '')}
줄거리/내용: {synopsis.get('plot', '')}
챕터: {', '.join(synopsis.get('chapters', [])[:4])}

---

위 마스터 프롬프트의 모든 규칙을 따라 완전한 스크립트를 작성하세요.
분량은 최소 8000자 이상으로 작성하세요."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}]
        )
        
        full_script = message.content[0].text
        
        # 스크립트를 챕터별로 파싱
        script_data = _parse_script_to_scenes(full_script, synopsis)
        
        return script_data
        
    except Exception as e:
        print(f"[API 호출 오류: {e}]")
        return _get_example_script()


def _parse_script_to_scenes(full_script: str, synopsis: dict) -> list:
    """전체 스크립트를 씬 단위로 파싱"""
    
    chapters = synopsis.get('chapters', [])[:4]
    scenes_per_chapter = 5
    
    # 스크립트를 문단 단위로 분리
    paragraphs = [p.strip() for p in full_script.split('\n\n') if p.strip() and len(p.strip()) > 50]
    
    result = []
    para_idx = 0
    
    for ch_idx, chapter_title in enumerate(chapters):
        chapter_scenes = []
        
        for scene_num in range(1, scenes_per_chapter + 1):
            if para_idx < len(paragraphs):
                text = paragraphs[para_idx][:200]  # 자막용으로 200자 제한
                para_idx += 1
            else:
                text = f"{chapter_title} - 씬 {scene_num}"
            
            chapter_scenes.append({
                "scene_num": scene_num,
                "text": text,
                "image_prompt": f"Korean drama scene, {chapter_title}, emotional moment, cinematic lighting, film style"
            })
        
        result.append({
            "chapter": chapter_title,
            "scenes": chapter_scenes
        })
    
    return result


def _get_example_synopsis(keyword: str, genre: str, channel_type: str = "drama") -> dict:
    """예시 시놉시스 반환 (채널별로 다른 예시)"""
    import random
    
    if channel_type == "health":
        names = ["박진우", "이상훈", "김태영", "정민호", "최동현"]
        expert = random.choice(names)
        return {
            "title": f"{keyword} - 전문가가 알려주는 핵심 비법",
            "characters": [f"{expert}: 노년건강학 박사, 20년 경력의 생활습관 전문가"],
            "background": f"현대 시니어들이 가장 궁금해하는 {keyword}에 대한 과학적 접근",
            "plot": f"{keyword}의 원인부터 예방법, 생활 속 실천 방법까지 체계적으로 알려드립니다.",
            "chapters": [
                f"1장: {keyword}의 진짜 원인",
                f"2장: 전문가가 추천하는 핵심 습관",
                f"3장: 피해야 할 위험한 실수",
                f"4장: 오늘부터 시작하는 실천법"
            ]
        }
    
    elif channel_type == "overseas":
        return {
            "title": f"{keyword} - 눈물 없이 볼 수 없는 실화",
            "characters": [
                "마리아 슈미트: 45세, 독일 간호사. 운명적인 만남의 주인공.",
                "김영수: 70세, 한국인 노인. 50년 전의 약속을 지키려는 사람.",
                "한스 뮐러: 50세, 마리아의 남편. 아내의 결정을 지지하는 조력자.",
                "박순덕: 75세, 영수의 아내. 남편의 여정을 응원하는 사람."
            ],
            "background": "2019년 독일 뮌헨, 한 장의 낡은 사진에서 시작된 기적 같은 이야기",
            "plot": f"{keyword}를 주제로 한 감동 실화. 50년의 시간을 뛰어넘어 다시 만난 두 사람의 이야기.",
            "chapters": [
                "1장: 낡은 사진 한 장",
                "2장: 50년 전의 약속",
                "3장: 운명의 재회",
                "4장: 눈물의 포옹"
            ]
        }
    
    elif channel_type == "yadam":
        return {
            "title": f"{keyword} - 조선시대 기이한 이야기",
            "characters": [
                "서린: 25세, 한양 양반가의 규수. 기이한 능력을 가진 여인.",
                "박문수: 30세, 암행어사. 진실을 밝히려는 청렴한 관리.",
                "월향: 나이 불명, 정체불명의 여인. 서린의 운명을 바꾸는 존재.",
                "이판서: 60세, 탐관오리. 마을의 비극의 원인."
            ],
            "background": "조선 영조 시대, 경상도 어느 산골 마을에서 벌어진 기이한 사건",
            "plot": f"{keyword}를 배경으로 한 야담. 권선징악과 반전이 있는 이야기.",
            "chapters": [
                "1장: 달 없는 밤의 비명",
                "2장: 사라진 사람들",
                "3장: 암행어사의 추적",
                "4장: 충격적인 진실"
            ]
        }
    
    else:  # drama (북한)
        # 랜덤 이름 생성
        first_names = ["현", "준", "성", "영", "철", "광", "명", "동", "상", "정"]
        last_names = ["강", "리", "김", "박", "최", "장", "한", "윤", "조", "임"]
        
        name1 = random.choice(last_names) + random.choice(first_names) + random.choice(["호", "철", "수", "민", "혁"])
        name2 = random.choice(last_names) + random.choice(["순", "영", "미", "정", "희"]) + random.choice(["아", "이", "자"])
        name3 = random.choice(last_names) + random.choice(first_names) + random.choice(["만", "식", "봉", "길"])
        
        locations = ["양강도 혜산시", "함경남도 단천시", "평안북도 신의주시", "황해북도 사리원시"]
        years = ["1985년", "1998년", "2005년", "2012년"]
        
        return {
            "title": f"{keyword} - 눈물의 이야기",
            "characters": [
                f"{name1}: 50대, 당 간부. 체제에 회의를 느끼는 인물.",
                f"{name2}: 20대 여성, {name1}의 딸. 희망을 잃지 않는 강인한 여성.",
                f"{name3}: 40대, 브로커. 위험을 무릅쓰고 돕는 조력자.",
                f"{random.choice(last_names)}씨 할머니: 70대, 마을의 어른. 지혜로운 조언자."
            ],
            "background": f"{random.choice(years)}, {random.choice(locations)}의 작은 마을",
            "plot": f"{keyword}를 주제로 한 감동 드라마. 가족의 사랑과 희생, 그리고 희망의 이야기.",
            "chapters": [
                "1장: 운명의 시작",
                "2장: 흔들리는 마음",
                "3장: 결단의 순간",
                "4장: 새로운 희망"
            ]
        }


def _get_example_script() -> list:
    """예시 대본 반환"""
    return [
        {
            "chapter": "1장: 고난의 그림자",
            "scenes": [
                {"scene_num": 1, "text": "1997년, 함경북도 탄광 마을. 고난의 행군이 한창인 시절이었습니다.", "image_prompt": "1990s North Korean mining village, winter, poverty, grey atmosphere, cinematic"},
                {"scene_num": 2, "text": "보위부 중장 리철은 굶주린 아이들을 바라보며 깊은 한숨을 내쉬었습니다.", "image_prompt": "Middle-aged Korean military officer, sad expression, dramatic lighting"},
                {"scene_num": 3, "text": "이대로는 안 된다. 무언가를 바꿔야 해.", "image_prompt": "Close-up determined Korean man's face, internal conflict"},
                {"scene_num": 4, "text": "그의 딸 선희가 조심스럽게 다가왔습니다.", "image_prompt": "Young Korean woman, modest room, emotional scene"},
                {"scene_num": 5, "text": "아버지, 저희... 여기서 떠나야 해요.", "image_prompt": "Father and daughter conversation, dim lighting"}
            ]
        },
        {
            "chapter": "2장: 위험한 결심",
            "scenes": [
                {"scene_num": 1, "text": "리철은 오랜 고민 끝에 결단을 내렸습니다.", "image_prompt": "Korean man deep in thought, dimly lit room"},
                {"scene_num": 2, "text": "탈북 브로커를 찾아가기로 한 것입니다.", "image_prompt": "Secret meeting, dark alley, noir atmosphere"},
                {"scene_num": 3, "text": "이건 목숨을 거는 일입니다. 정말 하시겠습니까?", "image_prompt": "Tense conversation, serious expressions"},
                {"scene_num": 4, "text": "더 이상 물러설 곳이 없소. 내 딸만은 자유롭게 해주고 싶소.", "image_prompt": "Emotional father, determined expression, tears"},
                {"scene_num": 5, "text": "그렇게 운명의 탈출이 시작되었습니다.", "image_prompt": "Night scene, preparing to escape, moonlight"}
            ]
        }
    ]


def generate_image_prompts(script: list, style: str = "cinematic realistic") -> list:
    """대본에서 이미지 프롬프트 추출"""
    prompts = []
    
    for chapter in script:
        for scene in chapter.get("scenes", []):
            prompts.append({
                "chapter": chapter.get("chapter", ""),
                "scene_num": scene.get("scene_num", 0),
                "text": scene.get("text", ""),
                "prompt": f"{scene.get('image_prompt', '')}, {style}, high quality"
            })
    
    return prompts
