"""
콘텐츠 로그 관리 모듈
- 생성된 모든 콘텐츠 기록
- 중복 검사 (이름, 제목, 스토리)
- 유사도 체크
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict

# 로그 파일 경로
LOG_FILE = "content_history.json"


def get_log_path(base_dir: str = None) -> str:
    """로그 파일 경로 반환"""
    if base_dir:
        return os.path.join(base_dir, LOG_FILE)
    return LOG_FILE


def load_history(base_dir: str = None) -> List[Dict]:
    """기존 콘텐츠 히스토리 로드"""
    log_path = get_log_path(base_dir)
    
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_history(history: List[Dict], base_dir: str = None):
    """콘텐츠 히스토리 저장"""
    log_path = get_log_path(base_dir)
    
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def log_content(synopsis: Dict, channel_type: str, keyword: str, base_dir: str = None) -> Dict:
    """
    새 콘텐츠를 로그에 기록
    
    Args:
        synopsis: 시놉시스 딕셔너리
        channel_type: 채널 타입
        keyword: 키워드
        base_dir: 로그 파일 저장 경로
    
    Returns:
        저장된 로그 항목
    """
    history = load_history(base_dir)
    
    # 등장인물 이름 추출
    characters = synopsis.get('characters', [])
    character_names = []
    for char in characters:
        # "이름: 설명" 형식에서 이름만 추출
        if ':' in str(char):
            name = str(char).split(':')[0].strip()
            character_names.append(name)
        else:
            character_names.append(str(char)[:10])
    
    log_entry = {
        "id": len(history) + 1,
        "created_at": datetime.now().isoformat(),
        "channel_type": channel_type,
        "keyword": keyword,
        "title": synopsis.get('title', ''),
        "character_names": character_names,
        "background": synopsis.get('background', ''),
        "plot_summary": synopsis.get('plot', '')[:200],  # 줄거리 앞 200자
        "chapters": synopsis.get('chapters', [])[:4]
    }
    
    history.append(log_entry)
    save_history(history, base_dir)
    
    return log_entry


def check_duplicates(synopsis: Dict, channel_type: str, base_dir: str = None) -> Dict:
    """
    중복 검사 수행
    
    Args:
        synopsis: 새로 생성된 시놉시스
        channel_type: 채널 타입
        base_dir: 로그 파일 경로
    
    Returns:
        {
            "has_duplicates": bool,
            "duplicate_names": [중복된 이름들],
            "similar_titles": [유사한 제목들],
            "similar_stories": [유사한 스토리들],
            "matched_entries": [매칭된 로그 항목들]
        }
    """
    history = load_history(base_dir)
    
    if not history:
        return {
            "has_duplicates": False,
            "duplicate_names": [],
            "similar_titles": [],
            "similar_stories": [],
            "matched_entries": []
        }
    
    # 새 콘텐츠의 이름들 추출
    new_characters = synopsis.get('characters', [])
    new_names = set()
    for char in new_characters:
        if ':' in str(char):
            name = str(char).split(':')[0].strip()
            new_names.add(name)
    
    new_title = synopsis.get('title', '')
    new_plot = synopsis.get('plot', '')
    
    # 중복 검사 결과
    duplicate_names = []
    similar_titles = []
    similar_stories = []
    matched_entries = []
    
    # 같은 채널 타입의 기존 콘텐츠와 비교
    for entry in history:
        if entry.get('channel_type') != channel_type:
            continue
        
        is_matched = False
        
        # 1. 이름 중복 검사
        old_names = set(entry.get('character_names', []))
        common_names = new_names & old_names
        if common_names:
            duplicate_names.extend(list(common_names))
            is_matched = True
        
        # 2. 제목 유사도 검사 (단어 기반)
        old_title = entry.get('title', '')
        title_similarity = _calculate_similarity(new_title, old_title)
        if title_similarity > 0.5:  # 50% 이상 유사
            similar_titles.append({
                "old_title": old_title,
                "similarity": f"{title_similarity*100:.0f}%",
                "created_at": entry.get('created_at', '')[:10]
            })
            is_matched = True
        
        # 3. 줄거리 유사도 검사
        old_plot = entry.get('plot_summary', '')
        plot_similarity = _calculate_similarity(new_plot, old_plot)
        if plot_similarity > 0.4:  # 40% 이상 유사
            similar_stories.append({
                "old_title": old_title,
                "similarity": f"{plot_similarity*100:.0f}%",
                "created_at": entry.get('created_at', '')[:10]
            })
            is_matched = True
        
        if is_matched:
            matched_entries.append(entry)
    
    # 중복 이름 제거
    duplicate_names = list(set(duplicate_names))
    
    has_duplicates = bool(duplicate_names or similar_titles or similar_stories)
    
    return {
        "has_duplicates": has_duplicates,
        "duplicate_names": duplicate_names,
        "similar_titles": similar_titles,
        "similar_stories": similar_stories,
        "matched_entries": matched_entries
    }


def _calculate_similarity(text1: str, text2: str) -> float:
    """
    두 텍스트의 유사도 계산 (단어 기반 Jaccard 유사도)
    
    Returns:
        0.0 ~ 1.0 사이의 유사도
    """
    if not text1 or not text2:
        return 0.0
    
    # 단어 집합 생성 (2글자 이상)
    words1 = set(w for w in text1.split() if len(w) >= 2)
    words2 = set(w for w in text2.split() if len(w) >= 2)
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard 유사도
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


def get_used_names(channel_type: str, base_dir: str = None) -> List[str]:
    """특정 채널에서 이미 사용된 모든 이름 반환"""
    history = load_history(base_dir)
    
    used_names = set()
    for entry in history:
        if entry.get('channel_type') == channel_type:
            used_names.update(entry.get('character_names', []))
    
    return list(used_names)


def get_history_summary(channel_type: str = None, base_dir: str = None) -> Dict:
    """히스토리 요약 정보 반환"""
    history = load_history(base_dir)
    
    if channel_type:
        history = [h for h in history if h.get('channel_type') == channel_type]
    
    return {
        "total_count": len(history),
        "by_channel": _count_by_channel(history),
        "recent_5": history[-5:] if history else []
    }


def _count_by_channel(history: List[Dict]) -> Dict:
    """채널별 콘텐츠 수 집계"""
    counts = {}
    for entry in history:
        ch = entry.get('channel_type', 'unknown')
        counts[ch] = counts.get(ch, 0) + 1
    return counts


def format_duplicate_warning(check_result: Dict) -> str:
    """중복 검사 결과를 사용자 친화적 메시지로 변환"""
    messages = []
    
    if check_result.get('duplicate_names'):
        names = ', '.join(check_result['duplicate_names'])
        messages.append(f"⚠️ **중복된 이름**: {names}")
    
    if check_result.get('similar_titles'):
        for item in check_result['similar_titles'][:3]:
            messages.append(f"⚠️ **유사한 제목** ({item['similarity']}): {item['old_title']} ({item['created_at']})")
    
    if check_result.get('similar_stories'):
        for item in check_result['similar_stories'][:3]:
            messages.append(f"⚠️ **유사한 스토리** ({item['similarity']}): {item['old_title']} ({item['created_at']})")
    
    return '\n\n'.join(messages) if messages else ""


if __name__ == "__main__":
    # 테스트
    test_synopsis = {
        "title": "운명의 선택 - 두만강을 건너다",
        "characters": [
            "김철수: 50대 보위부 중장",
            "이영희: 20대 딸"
        ],
        "background": "1997년 함경북도",
        "plot": "탈북을 결심한 가족의 이야기"
    }
    
    # 로그 기록
    log_content(test_synopsis, "drama", "탈북", ".")
    
    # 중복 검사
    result = check_duplicates(test_synopsis, "drama", ".")
    print("중복 검사 결과:", result)
