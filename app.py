"""
엔라이트랩 Vrew 자동화 - 수동 모드
실행: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import os
import re
import time
import shutil
from datetime import datetime

st.set_page_config(page_title="엔라이트랩 Vrew 자동화", page_icon="🎬", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1E88E5; text-align: center; margin-bottom: 0.5rem; }
    .sub-header { text-align: center; color: #666; margin-bottom: 1.5rem; font-size: 1rem; }
    /* GitHub 아이콘 숨기기 */
    .stToolbar { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    /* 우측 하단 플로팅 버튼 숨기기 */
    [data-testid="stStatusWidget"] { display: none !important; }
    .stDeployButton { display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    .viewerBadge_container__r5tak { display: none !important; }
    .styles_viewerBadge__CvC9N { display: none !important; }
    /* 외부 위젯 숨기기 (Chess, Beehiiv 등) */
    #credential_picker_container { display: none !important; }
    .g_id_signin { display: none !important; }
    div[id^="gsi_"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.auth import (
    is_logged_in, get_current_user, render_auth_ui, sign_out,
    get_user_credits, use_credit
)


def cleanup_old_files(hours=12):
    """12시간 지난 파일 자동 삭제"""
    outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
    if not os.path.exists(outputs_dir):
        return

    current_time = time.time()
    cutoff_time = current_time - (hours * 60 * 60)  # 12시간 전

    deleted_count = 0

    # outputs 폴더 내 모든 파일/폴더 검사
    for item in os.listdir(outputs_dir):
        item_path = os.path.join(outputs_dir, item)

        try:
            # 파일 또는 폴더의 수정 시간 확인
            mtime = os.path.getmtime(item_path)

            if mtime < cutoff_time:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    deleted_count += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    deleted_count += 1
        except Exception as e:
            pass  # 삭제 실패해도 계속 진행

    if deleted_count > 0:
        print(f"[Cleanup] {deleted_count}개 오래된 파일/폴더 삭제됨")


# 프로그램 시작 시 12시간 지난 파일 정리
if 'cleanup_done' not in st.session_state:
    cleanup_old_files(hours=12)
    st.session_state.cleanup_done = True

# 세션 초기화
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'script_text' not in st.session_state:
    st.session_state.script_text = ""
if 'excel_df' not in st.session_state:
    st.session_state.excel_df = None
if 'scenes' not in st.session_state:
    st.session_state.scenes = []
if 'clips' not in st.session_state:
    st.session_state.clips = []
if 'images' not in st.session_state:
    st.session_state.images = []
if 'selected_images' not in st.session_state:
    st.session_state.selected_images = {}
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0


def split_text_30chars(text, max_chars=100):
    """
    문장 단위로 분할 (종결어미 기준)
    
    규칙:
    - 마침표(.), 물음표(?), 느낌표(!) 뒤에서 분할
    - 단일 문장은 분리하지 않음 (길어도 유지)
    - max_chars를 넘어도 종결어미가 나올 때까지 유지
    """
    if not text or not text.strip():
        return []

    text = text.strip()
    # 빈 행 제거 (연속된 줄바꿈을 공백으로)
    text = re.sub(r'\n\s*\n', ' ', text)
    # 모든 줄바꿈을 공백으로
    text = re.sub(r'\n', ' ', text)
    # 연속 공백을 하나로
    text = re.sub(r'\s+', ' ', text)

    # 문장 종결 기준으로만 분할 (. ? ! 뒤의 공백에서 분리)
    # 단, "..." 같은 경우는 분리하지 않음
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    result = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            result.append(sentence)
    
    # 결과가 없으면 원본 반환
    if not result:
        result = [text]
    
    return result


def parse_excel(df):
    """엑셀 파일 파싱 - A열(씬-샷), B열(시작문장), C열(프롬프트)"""
    data = []
    # 엑셀에 헤더가 없는 경우를 대비해 iloc로 접근
    # 예상 컬럼: 0:Scene-Shot(1-1), 1:Start_Text, 2:Prompt
    
    for idx, row in df.iterrows():
        # A열 Parsing (1-1 -> Scene 1, Shot 1)
        scene_shot_str = str(row.iloc[0]).strip() if len(row) > 0 else ""
        start_text = str(row.iloc[1]).strip() if len(row) > 1 else ""
        prompt = str(row.iloc[2]).strip() if len(row) > 2 else ""
        
        scene_num = -1
        shot_num = -1
        
        # 1-1, 1-2 형식 파싱
        if '-' in scene_shot_str:
            try:
                parts = scene_shot_str.split('-')
                scene_num = int(parts[0])
                shot_num = int(parts[1])
            except:
                pass
        
        if start_text and start_text != 'nan' and scene_num > 0:
            data.append({
                'scene_num': scene_num, 
                'shot_num': shot_num, 
                'start_text': start_text, 
                'prompt': prompt,
                'raw_id': scene_shot_str
            })
    
    return data


def normalize_text(text):
    """
    1. 괄호와 그 안의 내용 제거
    2. 공백, 특수문자 제거 후 정규화된 텍스트와 원본 인덱스 매핑 반환
    """
    if not text:
        return "", []
    
    # 원본 텍스트 매핑을 위해 전체 텍스트 순회
    normalized = ""
    mapping = []
    
    # 괄호 안의 내용은 매핑에서 건너뛰고 싶지만, 
    # 원본(script_text)은 괄호가 없을 수도 있고 있을 수도 있음.
    # 단순화를 위해: 원본은 alphanumeric만 남기는 정규화.
    # 검색어(markers)는 괄호를 제거하고 정규화.
    
    for i, char in enumerate(text):
        if char.isalnum():
            normalized += char
            mapping.append(i)
            
    return normalized, mapping

def normalize_search_text(text):
    """검색어 전용 정규화 (괄호 내용 삭제)"""
    if not text:
        return ""
    # (경어) 등 제거
    text_clean = re.sub(r'\(.*?\)', '', text)
    
    normalized = ""
    for char in text_clean:
        if char.isalnum():
            normalized += char
    return normalized

def find_fuzzy(full_text_norm, full_text_map, search_text, start_offset_idx=0):
    """
    정규화된 텍스트에서 검색어 위치 찾기
    """
    search_norm = normalize_search_text(search_text)
    
    if len(search_norm) < 3:
        return -1
        
    start_norm_idx = -1
    
    # start_offset_idx(원본 인덱스)에 해당하는 정규화 인덱스 찾기
    # full_text_map은 정규화된 i번째 글자가 원본의 map[i]번째 글자임을 뜻함
    # 따라서 map[k] >= start_offset_idx 인 최소 k를 찾아야 함
    # (단순 선형 탐색은 느릴 수 있으나 텍스트 크기가 크지 않아 괜찮음)
    
    current_norm_offset = 0
    if start_offset_idx > 0:
        for i, original_idx in enumerate(full_text_map):
            if original_idx >= start_offset_idx:
                current_norm_offset = i
                break
        else:
            return -1 # 범위를 벗어남
            
    # 검색 범위 제한 (검색 속도 최적화)
    search_space = full_text_norm[current_norm_offset:]
    
    # 1. 전체 매칭
    idx = search_space.find(search_norm)
    
    # 2. 앞 20자 매칭
    if idx == -1:
        snippet = search_norm[:20]
        if len(snippet) >= 5:
            idx = search_space.find(snippet)
            
    # 3. 앞 10자 매칭
    if idx == -1:
        snippet = search_norm[:10]
        if len(snippet) >= 5:
            idx = search_space.find(snippet)

    # 4. 앞 5자 매칭 (강력한 오타 대응)
    if idx == -1:
        snippet = search_norm[:5]
        if len(snippet) >= 3:
            idx = search_space.find(snippet)
            
    # 5. 뒤 20자 매칭 (앞부분 오타 대비)
    if idx == -1:
        snippet = search_norm[-20:]
        if len(snippet) >= 5:
            idx = search_space.find(snippet)
            if idx != -1:
                idx = idx - len(search_norm) + len(snippet)

    if idx != -1:
        # 찾은 정규화 인덱스를 원본 인덱스로 변환
        found_norm_abs = current_norm_offset + idx
        # 범위 체크
        if found_norm_abs < len(full_text_map):
            return full_text_map[found_norm_abs]
            
    return -1

def split_script_by_markers(script_text, markers):
    """시작 문장 기준으로 대본 분할 (Fuzzy Matching 적용) - 순서 자동 정렬"""

    # 전체 텍스트 정규화 (한 번만 수행)
    norm_full, map_full = normalize_text(script_text)

    # 1단계: 모든 마커의 위치를 먼저 찾음 (순서 제한 없이, 전체 텍스트에서)
    marker_positions = []
    for i, marker in enumerate(markers):
        start_text = marker['start_text']

        # 전체 텍스트에서 검색 (current_pos 제한 없이)
        start_pos = find_fuzzy(norm_full, map_full, start_text, 0)

        # 못 찾았을 경우 원본 find 시도
        if start_pos == -1:
            start_pos = script_text.find(start_text[:10])

        if start_pos == -1:
            print(f"Warning: Cannot find match for Scene {marker['raw_id']}: '{start_text[:20]}...'")

        marker_positions.append({
            'original_idx': i,
            'marker': marker,
            'pos': start_pos
        })

    # 2단계: 위치 순서대로 정렬 (찾은 것만)
    found_markers = [m for m in marker_positions if m['pos'] != -1]
    found_markers.sort(key=lambda x: x['pos'])

    # 3단계: 각 마커에 대해 텍스트 구간 결정
    text_map = {}  # original_idx -> scene_text

    for i, item in enumerate(found_markers):
        start_pos = item['pos']

        # 다음 마커의 시작 위치 = 현재 마커의 종료 위치
        if i + 1 < len(found_markers):
            end_pos = found_markers[i + 1]['pos']
        else:
            end_pos = len(script_text)

        scene_text = script_text[start_pos:end_pos].strip()
        text_map[item['original_idx']] = scene_text

    # 4단계: 원래 Excel 순서대로 scenes 배열 구성
    scenes = []
    for i, marker in enumerate(markers):
        scene_text = text_map.get(i, "")  # 못 찾은 경우 빈 문자열

        scenes.append({
            'scene_num': marker['scene_num'],
            'shot_num': marker['shot_num'],
            'raw_id': marker['raw_id'],
            'text': scene_text,
            'prompt': marker['prompt']
        })

    return scenes


def create_clips(scenes):
    """씬을 30자 클립으로 분할"""
    clips = []
    for scene in scenes:
        text_chunks = split_text_30chars(scene['text'])
        for chunk in text_chunks:
            clips.append({
                'scene_num': scene['scene_num'],
                'shot_num': scene['shot_num'],
                'raw_id': scene['raw_id'],
                'text': chunk,
                'prompt': scene['prompt']
            })
    return clips


def main():
    st.markdown('<p class="main-header">🎬 엔라이트랩 Vrew 자동화</p>', unsafe_allow_html=True)

    # 로그인 체크
    if not is_logged_in():
        st.markdown('<p class="sub-header">베타 테스트 버전 - 초대 코드가 필요합니다</p>', unsafe_allow_html=True)
        render_auth_ui()
        return

    # 로그인된 사용자 정보
    user = get_current_user()
    user_id = user.get("id") if user else None
    access_token = st.session_state.get("access_token")

    # 크레딧 조회
    credits = get_user_credits(access_token, user_id) if user_id else 0
    st.session_state["credits"] = credits

    # 크레딧 0이면 자동 로그아웃
    if credits <= 0:
        st.error("🎫 크레딧이 없습니다. 자동 로그아웃됩니다.")
        sign_out()
        st.rerun()

    # 상단 사용자 정보 바
    user_cols = st.columns([3, 1, 1])
    with user_cols[0]:
        st.markdown(f"👤 **{user.get('email', '사용자')}**")
    with user_cols[1]:
        st.markdown(f"🎫 크레딧: **{credits}**회")
    with user_cols[2]:
        if st.button("로그아웃", use_container_width=True):
            sign_out()
            st.rerun()

    st.markdown("---")

    # 재시작 버튼 (서브타이틀 영역)
    if st.button("🔄 엔라이트랩 Vrew 자동화 재시작", use_container_width=True):
        # outputs 폴더 삭제 (Windows 특수 파일 에러 무시)
        outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
        if os.path.exists(outputs_dir):
            shutil.rmtree(outputs_dir, ignore_errors=True)

        # uploader_key 증가 (file_uploader 리셋용)
        new_uploader_key = st.session_state.get('uploader_key', 0) + 1
        current_token = st.session_state.get('access_token')
        current_user = st.session_state.get('user')

        # 세션 초기화 (인증 정보 유지)
        for key in list(st.session_state.keys()):
            if key not in ['access_token', 'user']:
                del st.session_state[key]

        # uploader_key 재설정
        st.session_state.uploader_key = new_uploader_key
        st.rerun()

    # 진행 단계 표시
    steps = ["1️⃣ 파일 업로드", "2️⃣ 이미지 매칭", "3️⃣ Vrew 생성"]
    cols = st.columns(3)
    for i, s in enumerate(steps):
        with cols[i]:
            if i + 1 < st.session_state.step:
                st.success(f"✅ {s}")
            elif i + 1 == st.session_state.step:
                st.info(f"👉 {s}")
            else:
                st.markdown(f"⬜ {s}")

    st.markdown("---")
    
    # ==================== STEP 1 ====================
    if st.session_state.step == 1:
        # Session state 초기화
        if 'script_text' not in st.session_state:
            st.session_state.script_text = None
        if 'excel_df' not in st.session_state:
            st.session_state.excel_df = None
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📄 대본 업로드")
            script_file = st.file_uploader("대본 텍스트 파일 (.txt)", type=['txt'], key=f"script_uploader_{st.session_state.uploader_key}")
            
            if script_file:
                script_text = script_file.read().decode('utf-8')
                st.session_state.script_text = script_text
                # 대본 파일명 저장 (확장자 제거)
                st.session_state.script_filename = script_file.name.replace('.txt', '')
                st.success(f"✅ 대본 로드 완료! ({len(script_text)}자)")
                with st.expander("대본 미리보기"):
                    st.text(script_text[:500] + "..." if len(script_text) > 500 else script_text)
        
        with col2:
            st.markdown("### 📊 이미지 정보 업로드")
            excel_file = st.file_uploader("엑셀/CSV 파일 (A열: 1-1 형식, B열: 시작문장, C열: 프롬프트)", type=['xlsx', 'xls', 'csv'], key=f"excel_uploader_{st.session_state.uploader_key}")

            if excel_file:
                # CSV/Excel 분기 처리
                if excel_file.name.endswith('.csv'):
                    # CSV 한글 인코딩 처리
                    df = None
                    for encoding in ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']:
                        try:
                            excel_file.seek(0)  # 파일 포인터 리셋
                            df = pd.read_csv(excel_file, encoding=encoding)
                            break
                        except:
                            continue
                    if df is None:
                        st.error("CSV 파일 인코딩을 인식할 수 없습니다.")
                else:
                    df = pd.read_excel(excel_file)

                if df is not None:
                    st.session_state.excel_df = df
                    markers = parse_excel(df)
                    st.success(f"✅ {len(markers)}개 씬 정보 로드!")
                    with st.expander("엑셀 미리보기"):
                        st.dataframe(df.head(10), use_container_width=True)
        
        st.markdown("---")
        
        if st.session_state.get('script_text') and st.session_state.get('excel_df') is not None:
            
            if st.button("🔄 대본 분할 & 프롬프트 추출", type="primary", use_container_width=True):
                with st.spinner("처리 중..."):
                    markers = parse_excel(st.session_state.excel_df)
                    scenes = split_script_by_markers(st.session_state.script_text, markers)
                    clips = create_clips(scenes)
                    
                    st.session_state.scenes = scenes
                    st.session_state.clips = clips
                    st.session_state.processed = True
                st.rerun()
            
            if st.session_state.processed and st.session_state.scenes:
                scenes = st.session_state.scenes
                clips = st.session_state.clips
                
                # 씬/샷 카운트 계산
                unique_scenes = set(s['scene_num'] for s in scenes)
                total_scenes_count = len(unique_scenes)
                total_shots_count = len(scenes)
                
                st.success(f"✅ {total_scenes_count}개 장면 (총 {total_shots_count}개 씬) → {len(clips)}개 클립 생성!")
                
                st.markdown("### 📋 분할 결과")
                for scene in scenes[:3]:
                    with st.expander(f"씬 {scene['raw_id']}: {scene['text'][:40]}..."):
                        st.markdown(f"**📝 한글 대본:**")
                        st.text(scene['text'][:300] + ("..." if len(scene['text']) > 300 else ""))

                        st.markdown(f"**🎨 이미지 프롬프트:**")
                        st.caption(scene['prompt'])

                        scene_clips = [c for c in clips if c['raw_id'] == scene['raw_id']]
                        st.markdown(f"**📌 클립 수:** {len(scene_clips)}개")
                        for i, clip in enumerate(scene_clips[:5]):
                            st.caption(f"  클립{i+1}: {clip['text']}")
                
                st.markdown("---")
                
                # 프롬프트 다운로드 (텍스트만, 빈 줄로 구분)
                prompts_lines = []
                for idx, scene in enumerate(scenes):
                    img_num = idx * 2 + 1  # A 이미지 번호: 001, 003, 005...
                    prompts_lines.append(f"{img_num:03d} {scene['prompt']}")
                    prompts_lines.append("")  # 빈 줄
                
                prompts_text = '\n'.join(prompts_lines)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        "📥 이미지 프롬프트 다운로드 (txt)",
                        data=prompts_text,
                        file_name="prompts.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col2:
                    if st.button("다음 단계 →", type="primary", use_container_width=True):
                        st.session_state.step = 2
                        st.rerun()
    
    # ==================== STEP 2 ====================
    elif st.session_state.step == 2:
        scenes = st.session_state.scenes
        
        if not scenes:
            st.warning("먼저 파일을 업로드하고 분할해주세요.")
            if st.button("← 1단계로"):
                st.session_state.step = 1
                st.rerun()
            return
        
        st.markdown("### 🖼️ 이미지 업로드 & 매칭")
        
        # 상단 네비게이션 버튼
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🏠 처음으로", key="reset_top", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        with c2:
            if st.button("← 이전 단계", key="prev_top", use_container_width=True):
                st.session_state.step = 1
                st.rerun()
        with c3:
            if st.button("다음 단계 →", key="next_top", type="primary", use_container_width=True):
                st.session_state.step = 3
                st.rerun()
        
        st.markdown("---")
        st.markdown("---")
        st.info(f"**총 {len(scenes)}개 씬**에 대한 이미지를 업로드하세요")
        
        uploaded_files = st.file_uploader(
            "이미지/영상 업로드 (001.jpg, 002.mp4 등)",
            type=['png', 'jpg', 'jpeg', 'mp4'],
            accept_multiple_files=True,
            key=f"image_uploader_{st.session_state.uploader_key}"
        )
        
        if uploaded_files:
            # 파일명 번호 추출 함수
            def extract_file_number(filename):
                match = re.match(r'^(\d+)', filename)
                return int(match.group(1)) if match else 9999
            
            # 파일명 번호로 정렬
            sorted_files = sorted(uploaded_files, key=lambda x: extract_file_number(x.name))
            
            output_dir = os.path.join(os.path.dirname(__file__), "outputs", "images")
            os.makedirs(output_dir, exist_ok=True)
            
            # 파일명 → 씬 매핑 (고정 매핑, 밀림 방지)
            # 규칙: 파일명 번호로 고정 매핑 (순서 상관없음)
            # 씬 1-1 (idx 0): 001.jpg (A), 002.jpg (B)
            # 씬 1-2 (idx 1): 003.jpg (A), 004.jpg (B)
            # 씬 1-3 (idx 2): 005.jpg (A), 006.jpg (B)
            # 파일이 없으면 None (업로드 버튼 표시)
            if 'images_by_shot' not in st.session_state or 'uploaded_file_hash' not in st.session_state or st.session_state.uploaded_file_hash != hash(str([f.name for f in sorted_files])):
                images_by_shot = {}  # {raw_id: {'A': {...}, 'B': {...}}}

                # 1. 파일명 번호 → 파일 딕셔너리 생성
                files_by_number = {}
                for file in sorted_files:
                    file_num = extract_file_number(file.name)
                    files_by_number[file_num] = file

                # 매핑 로그
                mapping_log = []

                # 2. 각 씬에 고정 번호 매핑
                for scene_idx, target_scene in enumerate(scenes):
                    raw_id = target_scene['raw_id']
                    images_by_shot[raw_id] = {}

                    # 이 씬에 필요한 파일 번호 계산
                    expected_a_num = scene_idx * 2 + 1  # 1, 3, 5, 7...
                    expected_b_num = scene_idx * 2 + 2  # 2, 4, 6, 8...

                    shot_images = []

                    # A 이미지/영상 찾기
                    if expected_a_num in files_by_number:
                        file = files_by_number[expected_a_num]
                        file_bytes = file.read()
                        # 원본 파일 확장자 유지
                        orig_ext = os.path.splitext(file.name)[1].lower()
                        if orig_ext not in ['.png', '.jpg', '.jpeg', '.mp4']:
                            orig_ext = '.png'
                        path = os.path.join(output_dir, f"img_{expected_a_num:03d}{orig_ext}")
                        with open(path, 'wb') as f:
                            f.write(file_bytes)

                        images_by_shot[raw_id]['A'] = {
                            'path': path,
                            'bytes': file_bytes,
                            'file_num': expected_a_num,
                            'original_name': file.name
                        }
                        shot_images.append(f"{file.name} (A)")
                    else:
                        shot_images.append(f"{expected_a_num:03d}.jpg 없음 (A)")

                    # B 이미지/영상 찾기
                    if expected_b_num in files_by_number:
                        file = files_by_number[expected_b_num]
                        file_bytes = file.read()
                        # 원본 파일 확장자 유지
                        orig_ext = os.path.splitext(file.name)[1].lower()
                        if orig_ext not in ['.png', '.jpg', '.jpeg', '.mp4']:
                            orig_ext = '.png'
                        path = os.path.join(output_dir, f"img_{expected_b_num:03d}{orig_ext}")
                        with open(path, 'wb') as f:
                            f.write(file_bytes)

                        images_by_shot[raw_id]['B'] = {
                            'path': path,
                            'bytes': file_bytes,
                            'file_num': expected_b_num,
                            'original_name': file.name
                        }
                        shot_images.append(f"{file.name} (B)")
                    else:
                        shot_images.append(f"{expected_b_num:03d}.jpg 없음 (B)")

                    # 로그 기록
                    mapping_log.append(f"씬 {raw_id}: {' + '.join(shot_images)}")

                st.session_state.images_by_shot = images_by_shot
                st.session_state.uploaded_file_hash = hash(str([f.name for f in sorted_files]))

                images_by_shot = st.session_state.images_by_shot

                # 매칭 상태 표시
                total_mapped = sum(1 for shot in images_by_shot.values() for key in shot.keys())
                st.success(f"✅ {len(sorted_files)}장 업로드 → {total_mapped}개 이미지 매핑됨 (A+B 합계)")

                # 매핑 상세 로그 (처음 10개만)
                with st.expander("📋 이미지 매핑 상세 (처음 10개 씬)", expanded=True):
                    for log_line in mapping_log[:10]:
                        st.caption(log_line)
            
            
            st.markdown("---")
            st.markdown("**씬 단위 이미지 선택** (기본: A 선택)")

            # 교체 상태 초기화
            if 'replace_mode' not in st.session_state:
                st.session_state.replace_mode = {}

            # 선택된 이미지 초기화
            if 'selected_images' not in st.session_state:
                st.session_state.selected_images = {}

            # session state에서 images_by_shot 가져오기
            images_by_shot = st.session_state.get('images_by_shot', {})
            output_dir = os.path.join(os.path.dirname(__file__), "outputs", "images")
            os.makedirs(output_dir, exist_ok=True)

            for idx, scene in enumerate(scenes):
                raw_id = scene['raw_id']

                # 해당 씬의 이미지 정보 가져오기
                shot_images = images_by_shot.get(raw_id, {})
                has_a = 'A' in shot_images
                has_b = 'B' in shot_images
                has_any = has_a or has_b

                # 기본 선택: A (또는 B만 있으면 B)
                if raw_id not in st.session_state.selected_images:
                    if has_a:
                        st.session_state.selected_images[raw_id] = 'A'
                    elif has_b:
                        st.session_state.selected_images[raw_id] = 'B'

                # Expander 제목
                expander_title = f"**씬 {raw_id}**: {scene['text'][:40]}..."
                if not has_any:
                    expander_title += " ⚠️ 이미지 없음"

                with st.expander(expander_title, expanded=(idx < 2)):
                    # 이 씬에 필요한 파일 번호 계산
                    expected_a_num = idx * 2 + 1
                    expected_b_num = idx * 2 + 2
                    expected_a_name = f"{expected_a_num:03d}.jpg"
                    expected_b_name = f"{expected_b_num:03d}.jpg"

                    # 상단: 대본 표시
                    st.markdown(f"**📝 한글 대본:**")
                    if scene['text'] and scene['text'].strip():
                        st.text(scene['text'][:200] + ("..." if len(scene['text']) > 200 else ""))
                    else:
                        st.warning("(대본 없음)")

                    # 필요한 이미지 파일명 안내
                    st.caption(f"📌 필요한 이미지: **{expected_a_name}** (A), **{expected_b_name}** (B)")
                    st.markdown("---")

                    # 이미지 표시 영역
                    if has_any:
                        # A, B 이미지를 가로로 배치
                        cols = st.columns(2)

                        # A 이미지/영상
                        with cols[0]:
                            if has_a:
                                # mp4인 경우 st.video(), 이미지인 경우 st.image()
                                if shot_images['A']['original_name'].lower().endswith('.mp4'):
                                    st.video(shot_images['A']['bytes'])
                                else:
                                    st.image(shot_images['A']['bytes'], use_container_width=True)
                                st.caption(f"📁 {shot_images['A']['original_name']}")

                                # 라디오 버튼 + 교체 버튼을 한 줄로
                                btn_cols = st.columns([1, 1])
                                with btn_cols[0]:
                                    if st.button("⭐ A 선택", key=f"select_a_{raw_id}", use_container_width=True,
                                                type="primary" if st.session_state.selected_images.get(raw_id) == 'A' else "secondary"):
                                        st.session_state.selected_images[raw_id] = 'A'
                                        st.rerun()
                                with btn_cols[1]:
                                    if st.button("🔄 교체", key=f"replace_a_{raw_id}", use_container_width=True):
                                        st.session_state.replace_mode[raw_id] = 'A'
                                        st.rerun()

                                # 교체 모드
                                if st.session_state.replace_mode.get(raw_id) == 'A':
                                    new_img = st.file_uploader(
                                        "새 이미지/영상 A 선택",
                                        type=['png', 'jpg', 'jpeg', 'mp4'],
                                        key=f"upload_a_{raw_id}"
                                    )
                                    if new_img:
                                        new_bytes = new_img.read()
                                        new_path = shot_images['A']['path']
                                        with open(new_path, 'wb') as f:
                                            f.write(new_bytes)

                                        images_by_shot[raw_id]['A']['bytes'] = new_bytes
                                        images_by_shot[raw_id]['A']['original_name'] = new_img.name
                                        st.session_state.images_by_shot = images_by_shot
                                        st.session_state.replace_mode[raw_id] = None
                                        st.success("✅ A 교체 완료!")
                                        st.rerun()
                            else:
                                st.warning(f"⚠️ **{expected_a_name}** 파일이 없습니다")
                                new_img_a = st.file_uploader(
                                    f"{expected_a_name} 업로드",
                                    type=['png', 'jpg', 'jpeg', 'mp4'],
                                    key=f"new_upload_a_{raw_id}"
                                )
                                if new_img_a:
                                    new_bytes = new_img_a.read()
                                    # 원본 파일 확장자 유지
                                    orig_ext = os.path.splitext(new_img_a.name)[1].lower()
                                    if orig_ext not in ['.png', '.jpg', '.jpeg', '.mp4']:
                                        orig_ext = '.png'
                                    new_path = os.path.join(output_dir, f"img_{raw_id}_A{orig_ext}")
                                    with open(new_path, 'wb') as f:
                                        f.write(new_bytes)

                                    images_by_shot[raw_id]['A'] = {
                                        'path': new_path,
                                        'bytes': new_bytes,
                                        'file_num': 0,
                                        'original_name': new_img_a.name
                                    }
                                    st.session_state.images_by_shot = images_by_shot
                                    st.success("✅ A 업로드 완료!")
                                    st.rerun()

                        # B 이미지/영상
                        with cols[1]:
                            if has_b:
                                # mp4인 경우 st.video(), 이미지인 경우 st.image()
                                if shot_images['B']['original_name'].lower().endswith('.mp4'):
                                    st.video(shot_images['B']['bytes'])
                                else:
                                    st.image(shot_images['B']['bytes'], use_container_width=True)
                                st.caption(f"📁 {shot_images['B']['original_name']}")

                                # 라디오 버튼 + 교체 버튼을 한 줄로
                                btn_cols = st.columns([1, 1])
                                with btn_cols[0]:
                                    if st.button("⭐ B 선택", key=f"select_b_{raw_id}", use_container_width=True,
                                                type="primary" if st.session_state.selected_images.get(raw_id) == 'B' else "secondary"):
                                        st.session_state.selected_images[raw_id] = 'B'
                                        st.rerun()
                                with btn_cols[1]:
                                    if st.button("🔄 교체", key=f"replace_b_{raw_id}", use_container_width=True):
                                        st.session_state.replace_mode[raw_id] = 'B'
                                        st.rerun()

                                # 교체 모드
                                if st.session_state.replace_mode.get(raw_id) == 'B':
                                    new_img = st.file_uploader(
                                        "새 이미지/영상 B 선택",
                                        type=['png', 'jpg', 'jpeg', 'mp4'],
                                        key=f"upload_b_{raw_id}"
                                    )
                                    if new_img:
                                        new_bytes = new_img.read()
                                        new_path = shot_images['B']['path']
                                        with open(new_path, 'wb') as f:
                                            f.write(new_bytes)

                                        images_by_shot[raw_id]['B']['bytes'] = new_bytes
                                        images_by_shot[raw_id]['B']['original_name'] = new_img.name
                                        st.session_state.images_by_shot = images_by_shot
                                        st.session_state.replace_mode[raw_id] = None
                                        st.success("✅ B 교체 완료!")
                                        st.rerun()
                            else:
                                st.warning(f"⚠️ **{expected_b_name}** 파일이 없습니다")
                                new_img_b = st.file_uploader(
                                    f"{expected_b_name} 업로드",
                                    type=['png', 'jpg', 'jpeg', 'mp4'],
                                    key=f"new_upload_b_{raw_id}"
                                )
                                if new_img_b:
                                    new_bytes = new_img_b.read()
                                    # 원본 파일 확장자 유지
                                    orig_ext = os.path.splitext(new_img_b.name)[1].lower()
                                    if orig_ext not in ['.png', '.jpg', '.jpeg', '.mp4']:
                                        orig_ext = '.png'
                                    new_path = os.path.join(output_dir, f"img_{raw_id}_B{orig_ext}")
                                    with open(new_path, 'wb') as f:
                                        f.write(new_bytes)

                                    images_by_shot[raw_id]['B'] = {
                                        'path': new_path,
                                        'bytes': new_bytes,
                                        'file_num': 0,
                                        'original_name': new_img_b.name
                                    }
                                    st.session_state.images_by_shot = images_by_shot
                                    st.success("✅ B 업로드 완료!")
                                    st.rerun()
                    else:
                        # 이미지가 하나도 없을 때
                        st.error(f"⚠️ **{expected_a_name}**, **{expected_b_name}** 파일이 없습니다. 아래에서 업로드하세요.")
                        cols = st.columns(2)

                        with cols[0]:
                            st.markdown(f"**이미지 A ({expected_a_name})**")
                            new_img_a = st.file_uploader(
                                f"{expected_a_name} 업로드",
                                type=['png', 'jpg', 'jpeg', 'mp4'],
                                key=f"empty_upload_a_{raw_id}",
                                label_visibility="collapsed"
                            )
                            if new_img_a:
                                new_bytes = new_img_a.read()
                                # 원본 파일 확장자 유지
                                orig_ext = os.path.splitext(new_img_a.name)[1].lower()
                                if orig_ext not in ['.png', '.jpg', '.jpeg', '.mp4']:
                                    orig_ext = '.png'
                                new_path = os.path.join(output_dir, f"img_{raw_id}_A{orig_ext}")
                                with open(new_path, 'wb') as f:
                                    f.write(new_bytes)

                                if raw_id not in images_by_shot:
                                    images_by_shot[raw_id] = {}

                                images_by_shot[raw_id]['A'] = {
                                    'path': new_path,
                                    'bytes': new_bytes,
                                    'file_num': 0,
                                    'original_name': new_img_a.name
                                }
                                st.session_state.images_by_shot = images_by_shot
                                st.session_state.selected_images[raw_id] = 'A'
                                st.success("✅ A 업로드 완료!")
                                st.rerun()

                        with cols[1]:
                            st.markdown(f"**이미지 B ({expected_b_name})**")
                            new_img_b = st.file_uploader(
                                f"{expected_b_name} 업로드",
                                type=['png', 'jpg', 'jpeg', 'mp4'],
                                key=f"empty_upload_b_{raw_id}",
                                label_visibility="collapsed"
                            )
                            if new_img_b:
                                new_bytes = new_img_b.read()
                                # 원본 파일 확장자 유지
                                orig_ext = os.path.splitext(new_img_b.name)[1].lower()
                                if orig_ext not in ['.png', '.jpg', '.jpeg', '.mp4']:
                                    orig_ext = '.png'
                                new_path = os.path.join(output_dir, f"img_{raw_id}_B{orig_ext}")
                                with open(new_path, 'wb') as f:
                                    f.write(new_bytes)

                                if raw_id not in images_by_shot:
                                    images_by_shot[raw_id] = {}

                                images_by_shot[raw_id]['B'] = {
                                    'path': new_path,
                                    'bytes': new_bytes,
                                    'file_num': 0,
                                    'original_name': new_img_b.name
                                }
                                st.session_state.images_by_shot = images_by_shot
                                if raw_id not in st.session_state.selected_images:
                                    st.session_state.selected_images[raw_id] = 'B'
                                st.success("✅ B 업로드 완료!")
                                st.rerun()
            
            st.markdown("---")
            
            # 하단 네비게이션 버튼
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🏠 처음으로", key="reset_bottom", use_container_width=True):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
            with c2:
                if st.button("← 이전 단계", key="prev_bottom", use_container_width=True):
                    st.session_state.step = 1
                    st.rerun()
            with c3:
                if st.button("다음 단계 →", key="next_bottom", type="primary", use_container_width=True):
                    st.session_state.step = 3
                    st.rerun()
    
    # ==================== STEP 3 ====================
    elif st.session_state.step == 3:
        clips = st.session_state.clips
        scenes = st.session_state.scenes
        images_by_shot = st.session_state.get('images_by_shot', {})
        selected = st.session_state.selected_images
        
        if not clips or not images_by_shot:
            st.warning("이전 단계를 완료해주세요.")
            if st.button("← 1단계로"):
                st.session_state.step = 1
                st.rerun()
            return
        
        st.markdown("### 📦 Vrew 파일 생성")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            total_shots = len(scenes)

            st.markdown(f"**📋 요약:** 총 {total_shots}개 씬 | {len(clips)}개 클립")

            st.markdown("---")
            st.markdown("**씬 단위 분할 설정**")

            # 씬 분할 선택 버튼
            col_all, col_5, col_10, col_20 = st.columns(4)
            with col_all:
                if st.button("전체", use_container_width=True, type="secondary" if st.session_state.get('split_size') != 0 else "primary"):
                    st.session_state.split_size = 0  # 0 = 전체
                    st.rerun()
            with col_5:
                if st.button("5씬씩", use_container_width=True, type="secondary" if st.session_state.get('split_size') != 5 else "primary"):
                    st.session_state.split_size = 5
                    st.rerun()
            with col_10:
                if st.button("10씬씩", use_container_width=True, type="secondary" if st.session_state.get('split_size') != 10 else "primary"):
                    st.session_state.split_size = 10
                    st.rerun()
            with col_20:
                if st.button("20씬씩", use_container_width=True, type="secondary" if st.session_state.get('split_size') != 20 else "primary"):
                    st.session_state.split_size = 20
                    st.rerun()
            
            # 분할 미리보기
            split_size = st.session_state.get('split_size', 10)
            parts = []

            if split_size == 0:  # 전체
                parts.append((0, total_shots - 1))
            else:
                # 씬 인덱스 기반으로 청크 나눔
                for i in range(0, total_shots, split_size):
                    start_idx = i
                    end_idx = min(i + split_size - 1, total_shots - 1)
                    parts.append((start_idx, end_idx))

            if split_size == 0:
                st.info(f"**전체** → 1개 파일 생성")
            else:
                st.info(f"**{split_size}씬씩 분할** → {len(parts)}개 파일 생성")

            with st.expander("분할 범위 미리보기"):
                for idx, (start_idx, end_idx) in enumerate(parts):
                    shots_in_range = scenes[start_idx:end_idx+1]
                    first_shot = scenes[start_idx]['raw_id']
                    last_shot = scenes[end_idx]['raw_id']
                    st.caption(f"장면 {idx+1}: {first_shot} ~ {last_shot} (총 {len(shots_in_range)}씬)")
            
            st.markdown("---")
            
            c1, c2 = st.columns(2)
            
            with c1:
                if st.button("← 이전 단계", use_container_width=True):
                    st.session_state.step = 2
                    st.rerun()
            
            with c2:
                # 크레딧 체크
                current_credits = st.session_state.get("credits", 0)
                button_disabled = current_credits <= 0

                if button_disabled:
                    st.error("🎫 크레딧이 부족합니다. 관리자에게 문의하세요.")

                if st.button("🎬 모든 Vrew 파일 생성", type="primary", use_container_width=True, disabled=button_disabled):
                    # 크레딧 차감
                    user = get_current_user()
                    user_id = user.get("id") if user else None
                    access_token = st.session_state.get("access_token")

                    if not use_credit(access_token, user_id):
                        st.error("크레딧 차감에 실패했습니다.")
                        st.stop()

                    new_credits = current_credits - 1
                    st.session_state["credits"] = new_credits

                    with st.spinner("Vrew 파일 생성 중..."):
                        try:
                            from modules.vrew_creator import create_vrew_project
                            
                            # 대본 파일명 가져오기
                            script_name = st.session_state.get('script_filename', 'vrew')
                            split_size = st.session_state.get('split_size', 10)

                            # 씬 인덱스 범위 계산
                            total_shots = len(scenes)
                            parts = []

                            if split_size == 0:  # 전체
                                parts.append((0, total_shots - 1))
                            else:
                                for i in range(0, total_shots, split_size):
                                    start_idx = i
                                    end_idx = min(i + split_size - 1, total_shots - 1)
                                    parts.append((start_idx, end_idx))
                            
                            template_path = os.path.join(os.path.dirname(__file__), "templates", "TEMPLATE.vrew")
                            output_dir = os.path.join(os.path.dirname(__file__), "outputs")
                            os.makedirs(output_dir, exist_ok=True)
                            
                            # 각 범위별로 파일 생성
                            generated_files = []
                            
                            for part_idx, (start_idx, end_idx) in enumerate(parts):
                                # 해당 범위의 clips 필터링
                                part_images = []
                                part_captions = []

                                # 1. 이 범위(씬 인덱스 start_idx~end_idx)에 해당하는 씬들을 슬라이싱
                                target_shots = scenes[start_idx:end_idx+1]

                                # 2. 각 씬(raw_id)에 대해 루프
                                for shot in target_shots:
                                    raw_id = shot['raw_id']

                                    # 해당 씬의 클립들 가져오기
                                    shot_clips = [c for c in clips if c['raw_id'] == raw_id]

                                    # 해당 씬의 선택된 이미지 가져오기
                                    if raw_id in images_by_shot:
                                        # 선택된 이미지 (A 또는 B)
                                        selected_img = st.session_state.selected_images.get(raw_id, 'A')

                                        # 선택된 이미지가 실제로 존재하는지 확인
                                        if selected_img in images_by_shot[raw_id]:
                                            img_path = images_by_shot[raw_id][selected_img]['path']
                                        else:
                                            # 선택된 이미지가 없으면 A 또는 B 중 존재하는 것 사용
                                            if 'A' in images_by_shot[raw_id]:
                                                img_path = images_by_shot[raw_id]['A']['path']
                                            elif 'B' in images_by_shot[raw_id]:
                                                img_path = images_by_shot[raw_id]['B']['path']
                                            else:
                                                continue  # 이미지가 아예 없으면 스킵

                                        for clip in shot_clips:
                                            part_images.append(img_path)
                                            part_captions.append(clip['text'])
                                
                                # 파일명: 대본명_장면N.vrew
                                first_shot = target_shots[0]['raw_id']
                                last_shot = target_shots[-1]['raw_id']
                                output_filename = f"{script_name}_장면{part_idx+1}.vrew"
                                output_path = os.path.join(output_dir, output_filename)

                                create_vrew_project(
                                    template_path=template_path,
                                    images=part_images,
                                    captions=part_captions,
                                    output_path=output_path
                                )

                                generated_files.append({
                                    'path': output_path,
                                    'filename': output_filename,
                                    'range': f"씬 {first_shot} ~ {last_shot}"
                                })
                            
                            st.session_state.generated_vrew_files = generated_files
                            st.success(f"✅ {len(generated_files)}개 Vrew 파일 생성 완료!")

                            # 크레딧 0회 시 메시지 표시 (파일 생성 완료 후)
                            if new_credits <= 0:
                                st.session_state["logout_after_download"] = True
                                st.warning("🎫 크레딧이 모두 소진되었습니다. 파일 다운로드 후 로그아웃됩니다.")

                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"오류: {e}")
                            import traceback
                            st.code(traceback.format_exc())
            
            # 생성된 파일 다운로드 UI
            if 'generated_vrew_files' in st.session_state and st.session_state.generated_vrew_files:
                st.markdown("---")
                st.markdown("### 📥 생성된 파일")
                
                for file_info in st.session_state.generated_vrew_files:
                    col_info, col_btn = st.columns([3, 1])
                    
                    with col_info:
                        st.caption(f"**{file_info['filename']}**")
                        st.caption(f"({file_info['range']})")
                    
                    with col_btn:
                        with open(file_info['path'], 'rb') as f:
                            st.download_button(
                                "📥",
                                data=f,
                                file_name=file_info['filename'],
                                mime="application/zip",
                                use_container_width=True,
                                key=f"download_{file_info['filename']}"
                            )

                # 작업 완료 & 파일 정리 버튼
                st.markdown("---")
                # 크레딧 소진 시 로그아웃 예정 알림
                if st.session_state.get("logout_after_download"):
                    st.warning("⚠️ 크레딧이 모두 소진되었습니다. 파일 다운로드 후 아래 버튼을 누르면 로그아웃됩니다.")

                if st.button("🗑️ 작업 완료 & 파일 정리", type="secondary", use_container_width=True):
                    # outputs/images 폴더 삭제
                    images_dir = os.path.join(os.path.dirname(__file__), "outputs", "images")
                    if os.path.exists(images_dir):
                        shutil.rmtree(images_dir)

                    # 생성된 vrew 파일 삭제
                    for file_info in st.session_state.generated_vrew_files:
                        if os.path.exists(file_info['path']):
                            os.remove(file_info['path'])

                    # 크레딧 소진 시 로그아웃
                    should_logout = st.session_state.get("logout_after_download", False)

                    # 세션 초기화
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]

                    if should_logout:
                        st.success("✅ 파일 정리 완료! 크레딧 소진으로 로그아웃됩니다.")
                    else:
                        st.success("✅ 파일 정리 완료! 처음으로 돌아갑니다.")
                    st.rerun()

                st.caption("⚠️ 다운로드 완료 후 눌러주세요. 업로드한 이미지와 생성된 파일이 삭제됩니다.")

        with col2:
            st.markdown("**💡 다음 단계**")
            st.info("1. Vrew 파일 다운로드\n2. Vrew에서 열기\n3. 전체 선택 (Ctrl+A)\n4. AI 목소리 다시 만들기\n5. 영상 내보내기")
        
        # 목소리 추천 섹션 (토글 가능)
        st.markdown("---")
        with st.expander("🎤 추천 목소리", expanded=False):
            st.markdown('''
            <style>
            .voice-table {
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }
            .voice-table th {
                background-color: #f0f2f6;
                padding: 12px;
                text-align: left;
                font-weight: bold;
                border-bottom: 2px solid #ddd;
            }
            .voice-table td {
                padding: 10px 12px;
                border-bottom: 1px solid #eee;
            }
            .category-cell {
                background-color: #e8f4f8;
                font-weight: bold;
                text-align: center;
                vertical-align: middle;
            }
            .category-icon {
                font-size: 24px;
                display: block;
                margin-bottom: 5px;
            }
            .gender-male {
                color: #4a90e2;
            }
            .gender-female {
                color: #e24a90;
            }
            </style>
            
            <table class="voice-table">
            <tr>
                <th>카테고리</th>
                <th>성별</th>
                <th>추천 목소리</th>
                <th>특징</th>
            </tr>
            <tr>
                <td class="category-cell" rowspan="4"><span class="category-icon">🔥</span>북한</td>
                <td class="gender-female" rowspan="2">여성</td>
                <td>손혜린</td>
                <td>무겁고 진지한 내용</td>
            </tr>
            <tr>
                <td>손수지</td>
                <td>가장 대중적인</td>
            </tr>
            <tr>
                <td class="gender-male" rowspan="2">남성</td>
                <td>기림</td>
                <td>무게감 있고 진중한</td>
            </tr>
            <tr>
                <td>무성</td>
                <td>무게감 있고 진중한</td>
            </tr>
            <tr>
                <td class="category-cell" rowspan="4"><span class="category-icon">💪</span>건강채널</td>
                <td class="gender-male" rowspan="4">남성</td>
                <td>류용석</td>
                <td>가장 대중적인</td>
            </tr>
            <tr>
                <td>류영진</td>
                <td>류용석 다음으로 많이 쓰임</td>
            </tr>
            <tr>
                <td>남정훈</td>
                <td>젊은 남성</td>
            </tr>
            <tr>
                <td>남준</td>
                <td>할아버지</td>
            </tr>
            <tr>
                <td class="category-cell" rowspan="4"><span class="category-icon">🌏</span>해외감동사연</td>
                <td class="gender-male" rowspan="2">남성</td>
                <td>무성</td>
                <td>임팩트 있는 인트로</td>
            </tr>
            <tr>
                <td>카이저</td>
                <td>강하고 특이한</td>
            </tr>
            <tr>
                <td class="gender-female" rowspan="2">여성</td>
                <td>손수지</td>
                <td>가장 대중적인</td>
            </tr>
            <tr>
                <td>손혜린</td>
                <td>무겁고 진지한</td>
            </tr>
            </table>
            ''', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
