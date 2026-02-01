"""
Vrew 프로젝트 파일 생성 모듈 v6
- AI 목소리 모드 (projectStartMode: ai_voice)
- ttsClipInfosMap 추가 (TTS 정보 포함)
- 단어별 words 분리
- 더미 TTS 파일 포함 (Vrew에서 재생성 필요)
- 클립별 이미지 연결
- Ken Burns 효과
"""

import json
import zipfile
import os
import shutil
import uuid
import random
import string
import re
import cv2


def get_video_info(video_path):
    """
    영상 파일의 정보를 가져옴 (duration, width, height, fps)
    """
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        duration = frame_count / fps if fps > 0 else 5

        return {
            "duration": round(duration, 2),
            "width": width,
            "height": height,
            "fps": round(fps, 2)
        }
    except Exception as e:
        print(f"Warning: Cannot get video info for {video_path}: {e}")
        return None


def generate_id(length=10):
    """랜덤 ID 생성"""
    chars = string.ascii_letters + string.digits + '-_'
    return ''.join(random.choice(chars) for _ in range(length))


def get_kenburns_effect(index):
    """Ken Burns 효과 순환"""
    effects = [
        {
            "type": "right-to-left",
            "from": {"scale": 0.7, "centerX": 0.58, "centerY": 0.5},
            "to": {"scale": 0.7, "centerX": 0.42, "centerY": 0.5}
        },
        {
            "type": "left-to-right", 
            "from": {"scale": 0.7, "centerX": 0.42, "centerY": 0.5},
            "to": {"scale": 0.7, "centerX": 0.58, "centerY": 0.5}
        },
        {
            "type": "zoom-in",
            "from": {"scale": 0.8, "centerX": 0.5, "centerY": 0.5},
            "to": {"scale": 1.0, "centerX": 0.5, "centerY": 0.5}
        },
        {
            "type": "zoom-out",
            "from": {"scale": 1.0, "centerX": 0.5, "centerY": 0.5},
            "to": {"scale": 0.8, "centerX": 0.5, "centerY": 0.5}
        }
    ]
    return effects[index % len(effects)]


def split_caption_to_words(caption, total_duration):
    """
    자막을 단어별로 분리하고 각 단어에 duration 할당
    
    Args:
        caption: 전체 자막 텍스트
        total_duration: 전체 TTS duration
    
    Returns:
        list of {"text": str, "duration": float, "startTime": float}
    """
    # 공백 기준으로 단어 분리
    words = caption.split()
    if not words:
        return [{"text": caption, "duration": total_duration, "startTime": 0}]
    
    # 각 단어의 글자 수 기준으로 duration 비례 배분
    total_chars = sum(len(w) for w in words)
    if total_chars == 0:
        total_chars = 1
    
    result = []
    current_time = 0
    
    for word in words:
        # 글자 수 비례로 duration 계산
        word_duration = (len(word) / total_chars) * total_duration
        result.append({
            "text": word,
            "duration": round(word_duration, 2),
            "startTime": round(current_time, 2)
        })
        current_time += word_duration
    
    return result


def get_silence_duration(word):
    """
    단어에 맞는 silence duration 계산

    Args:
        word: 단어 텍스트

    Returns:
        float: silence duration (초)
    """
    # 문장 종결 부호 체크
    if word.endswith(('.', '!', '?', '。')):
        return 0.8  # 문장 끝: 긴 pause
    elif word.endswith((',', ':', ';')):
        return 0.4  # 쉼표: 중간 pause

    # 조사로 끝나는 경우 (문장 연결)
    if word.endswith(('이', '가', '을', '를', '의', '에', '에서', '으로', '로', '와', '과', '도', '만', '은', '는')):
        return 0.1  # 거의 pause 없음

    # 연결어미로 끝나는 경우 ("~다는", "~면서", "~지만" 등)
    if word.endswith(('다는', '면서', '지만', '거나', '든지', '듯이')):
        return 0.1  # 거의 pause 없음

    # 일반 단어 길이 체크 (문장부호 제외)
    clean_word = word.strip('.,!?:;。')
    word_len = len(clean_word)

    if word_len <= 2:
        return 0.15  # 짧은 단어
    else:
        return 0.2  # 일반 단어


def create_vrew_project(template_path, images, captions, output_path, tts_voice="va29"):
    """
    Vrew 프로젝트 생성 - AI 목소리 모드 + ttsClipInfosMap 포함

    Args:
        template_path: TEMPLATE.vrew 파일 경로
        images: 이미지 파일 경로 리스트
        captions: 자막 텍스트 리스트 (각 자막은 30자 이내 권장)
        output_path: 출력 .vrew 파일 경로
        tts_voice: TTS 음성 ID (기본: va29 = 송세아)
    """

    # 자막 텍스트 정리: 이스케이프 문자 제거
    captions = [caption.replace('\\"', '"').replace('\\n', ' ').replace('\\t', ' ') for caption in captions]
    
    # 더미 TTS 파일 경로
    dummy_tts_path = os.path.join(os.path.dirname(template_path), "dummy.mpga")
    dummy_tts_size = os.path.getsize(dummy_tts_path) if os.path.exists(dummy_tts_path) else 25913
    
    # 템플릿 압축 해제
    temp_dir = output_path + "_temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    os.makedirs(temp_dir, exist_ok=True)
    
    with zipfile.ZipFile(template_path, 'r') as zf:
        zf.extractall(temp_dir)
    
    # project.json 로드
    with open(os.path.join(temp_dir, "project.json"), 'r', encoding='utf-8') as f:
        project = json.load(f)
    
    # 미디어 폴더 비우기
    media_dir = os.path.join(temp_dir, "media")
    for f in os.listdir(media_dir):
        os.remove(os.path.join(media_dir, f))
    
    # 파일 목록 초기화
    project['files'] = []
    project['props']['assets'] = {}
    
    # 기존 템플릿의 TTS 관련 데이터 완전 초기화 (중요!)
    if 'ttsClipInfosMap' in project['props']:
        project['props']['ttsClipInfosMap'] = {}
    if 'originalClipsMap' in project['props']:
        project['props']['originalClipsMap'] = {}
    
    # ttsClipInfosMap 초기화
    tts_clip_infos_map = {}
    
    # 미디어 파일 및 asset 추가 (이미지/영상)
    image_to_media = {}
    image_to_asset = {}  # 이미지만 asset 생성
    video_info_map = {}  # 영상 정보 저장 (duration 등)
    asset_effect_counter = {}
    asset_zindex_counter = 0  # 각 asset에 고유한 zIndex 부여

    for i, img_path in enumerate(images):
        if not os.path.exists(img_path):
            continue

        if img_path not in image_to_media:
            media_id = str(uuid.uuid4())

            ext = os.path.splitext(img_path)[1].lower()
            is_video = ext == '.mp4'

            if ext not in ['.png', '.jpg', '.jpeg', '.mp4']:
                ext = '.png'

            file_size = os.path.getsize(img_path)
            media_name = f"{media_id}{ext}"

            if is_video:
                # 영상 파일 (mp4) - 실제 영상 정보 가져오기
                video_info = get_video_info(img_path)
                if video_info:
                    v_width = video_info['width']
                    v_height = video_info['height']
                    v_fps = video_info['fps']
                    v_duration = video_info['duration']
                else:
                    # 기본값
                    v_width, v_height, v_fps, v_duration = 1920, 1080, 30, 5

                project['files'].append({
                    "version": 1,
                    "mediaId": media_id,
                    "sourceOrigin": "USER",
                    "fileSize": file_size,
                    "name": media_name,
                    "type": "AVMedia",
                    "videoAudioMetaInfo": {
                        "videoInfo": {
                            "size": {"width": v_width, "height": v_height},
                            "frameRate": v_fps,
                            "codec": "h264"
                        },
                        "audioInfo": {
                            "sampleRate": 48000,
                            "codec": "aac",
                            "channelCount": 2
                        },
                        "duration": v_duration,
                        "presumedDevice": "unknown",
                        "mediaContainer": "mp4"
                    },
                    "sourceFileType": "VIDEO_AUDIO",
                    "fileLocation": "IN_MEMORY"
                })

                # 영상 복사
                shutil.copy2(img_path, os.path.join(media_dir, media_name))

                # 영상은 asset을 만들지 않음 (Vrew에서 영상 클립은 assetIds가 비어있음)
                # 대신 영상 정보를 저장
                video_info_map[img_path] = {
                    "duration": v_duration,
                    "width": v_width,
                    "height": v_height
                }
            else:
                # 이미지 파일
                asset_id = str(uuid.uuid4())

                project['files'].append({
                    "version": 1,
                    "mediaId": media_id,
                    "sourceOrigin": "USER",
                    "fileSize": file_size,
                    "name": media_name,
                    "type": "Image",
                    "isTransparent": False,
                    "fileLocation": "IN_MEMORY"
                })

                # 이미지 복사
                shutil.copy2(img_path, os.path.join(media_dir, media_name))

                # 이미지 asset 생성
                project['props']['assets'][asset_id] = {
                    "mediaId": media_id,
                    "xPos": 0,
                    "yPos": 0,
                    "height": 1,
                    "width": 1,
                    "rotation": 0,
                    "zIndex": asset_zindex_counter,
                    "type": "image",
                    "originalWidthHeightRatio": 1.7777777777777777,
                    "importType": "user_asset_panel",
                    "kenburnsAnimationInfo": get_kenburns_effect(0),
                    "editInfo": {},
                    "stats": {"fillType": "cut", "fillMenu": "floating", "rearrangeCount": 0}
                }
                asset_zindex_counter += 1
                image_to_asset[img_path] = asset_id

            image_to_media[img_path] = media_id
            asset_effect_counter[img_path] = 0
    
    # 클립 생성
    new_clips = []

    for i, (img_path, caption) in enumerate(zip(images, captions)):
        if img_path not in image_to_media:
            continue

        media_id = image_to_media[img_path]
        ext = os.path.splitext(img_path)[1].lower()
        is_video = ext == '.mp4'

        if is_video:
            # ===== 영상 클립 (TTS 없음, 영상만 재생) =====
            video_duration = video_info_map.get(img_path, {}).get("duration", 5)

            # 영상 프레임 words 생성 (type: 3) - 1초 단위
            words = []
            for sec in range(int(video_duration)):
                words.append({
                    "id": generate_id(),
                    "text": "",
                    "startTime": sec,
                    "duration": 1,
                    "aligned": True,
                    "type": 3,  # 영상 프레임 타입
                    "originalDuration": 1,
                    "originalStartTime": sec,
                    "truncatedWords": [],
                    "autoControl": False,
                    "mediaId": media_id,  # 영상 mediaId 직접 참조
                    "audioIds": [],
                    "assetIds": [],
                    "playbackRate": 1
                })

            # 끝 마커 (type: 2)
            words.append({
                "id": generate_id(),
                "text": "",
                "startTime": int(video_duration),
                "duration": 0,
                "aligned": False,
                "type": 2,
                "originalDuration": 0,
                "originalStartTime": int(video_duration),
                "truncatedWords": [],
                "autoControl": False,
                "mediaId": media_id,
                "audioIds": [],
                "assetIds": [],
                "playbackRate": 1
            })

            # 영상 클립 생성 (assetIds 비어있음!)
            clip = {
                "id": generate_id(),
                "words": words,
                "captionMode": "MANUAL",
                "captions": [
                    {"text": [{"insert": caption + "\n"}]},
                    {"text": [{"insert": "\n"}]}
                ],
                "assetIds": [],  # 영상 클립은 assetIds가 비어있음
                "dirty": {
                    "blankDeleted": False,
                    "caption": True,
                    "video": False
                },
                "translationModified": {
                    "result": False,
                    "source": True
                },
                "audioIds": []
            }
            new_clips.append(clip)

        else:
            # ===== 이미지 클립 (TTS 포함) =====
            asset_id = image_to_asset[img_path]

            # Ken Burns 효과 업데이트
            effect_idx = asset_effect_counter[img_path]
            project['props']['assets'][asset_id]['kenburnsAnimationInfo'] = get_kenburns_effect(effect_idx)
            asset_effect_counter[img_path] += 1

            # TTS 생성
            tts_media_id = generate_id()

            # 예상 duration (글자당 0.08초 + 기본)
            duration = max(1.5, len(caption) * 0.08 + 0.5)

            # TTS 파일 정보 추가
            project['files'].append({
                "version": 1,
                "mediaId": tts_media_id,
                "sourceOrigin": "VREW_RESOURCE",
                "fileSize": dummy_tts_size,
                "name": f"{caption[:10]}.mp3",
                "type": "AVMedia",
                "videoAudioMetaInfo": {
                    "duration": duration,
                    "audioInfo": {
                        "sampleRate": 24000,
                        "codec": "mp3",
                        "channelCount": 1
                    }
                },
                "sourceFileType": "TTS",
                "fileLocation": "IN_MEMORY"
            })

            # ttsClipInfosMap에 TTS 정보 추가
            tts_clip_infos_map[tts_media_id] = {
                "duration": duration,
                "text": {
                    "raw": caption,
                    "textAspectLang": "ko-KR",
                    "processed": caption
                },
                "speaker": {
                    "gender": "female",
                    "age": "middle",
                    "provider": "vrew",
                    "lang": "ko-KR",
                    "name": tts_voice,
                    "speakerId": tts_voice,
                    "versions": ["v2"]
                },
                "volume": 0,
                "speed": 0,
                "pitch": 0,
                "version": "v2"
            }

            # 단어별로 분리
            word_infos = split_caption_to_words(caption, duration)

            # words 배열 생성
            words = []
            for word_info in word_infos:
                words.append({
                    "id": generate_id(),
                    "text": word_info["text"],
                    "startTime": word_info["startTime"],
                    "duration": word_info["duration"],
                    "aligned": False,
                    "type": 0,
                    "originalDuration": word_info["duration"],
                    "originalStartTime": word_info["startTime"],
                    "truncatedWords": [],
                    "autoControl": False,
                    "mediaId": tts_media_id,
                    "audioIds": [],
                    "assetIds": [],
                    "playbackRate": 1
                })

            # 묵음 구간 (type: 1)
            last_end_time = word_infos[-1]["startTime"] + word_infos[-1]["duration"] if word_infos else duration
            last_word = word_infos[-1]["text"] if word_infos else ""
            silence_duration = get_silence_duration(last_word) if last_word else 0.5

            words.append({
                "id": generate_id(),
                "text": "",
                "startTime": round(last_end_time, 2),
                "duration": silence_duration,
                "aligned": False,
                "type": 1,
                "originalDuration": silence_duration,
                "originalStartTime": round(last_end_time, 2),
                "truncatedWords": [],
                "autoControl": False,
                "mediaId": tts_media_id,
                "audioIds": [],
                "assetIds": [],
                "playbackRate": 1
            })

            # 끝 마커 (type: 2)
            words.append({
                "id": generate_id(),
                "text": "",
                "startTime": round(last_end_time + silence_duration, 2),
                "duration": 0,
                "aligned": False,
                "type": 2,
                "originalDuration": 0,
                "originalStartTime": round(last_end_time + silence_duration, 2),
                "truncatedWords": [],
                "autoControl": False,
                "mediaId": tts_media_id,
                "audioIds": [],
                "assetIds": [],
                "playbackRate": 1
            })

            # 이미지 클립 생성
            clip = {
                "id": generate_id(),
                "words": words,
                "captionMode": "MANUAL",
                "captions": [
                    {"text": [{"insert": caption + "\n"}]},
                    {"text": [{"insert": "\n"}]}
                ],
                "assetIds": [asset_id],
                "dirty": {
                    "blankDeleted": False,
                    "caption": False,
                    "video": False
                },
                "translationModified": {
                    "result": False,
                    "source": False
                },
                "audioIds": []
            }
            new_clips.append(clip)
    
    # scenes 업데이트
    project['transcript']['scenes'] = [{
        "id": generate_id(),
        "clips": new_clips,
        "name": "",
        "dirty": False
    }]
    
    # projectStartMode를 ai_voice로 설정
    if 'statistics' not in project:
        project['statistics'] = {}
    project['statistics']['projectStartMode'] = 'ai_voice'
    
    # ttsClipInfosMap 추가 (핵심!)
    project['props']['ttsClipInfosMap'] = tts_clip_infos_map
    
    # TTS 설정
    project['props']['lastTTSSettings'] = {
        "pitch": 0,
        "speed": 0,
        "volume": 0,
        "speaker": {
            "gender": "female",
            "age": "middle",
            "provider": "vrew",
            "lang": "ko-KR",
            "name": tts_voice,
            "speakerId": tts_voice,
            "versions": ["v2"]
        },
        "version": "v2"
    }
    
    # project.json 저장
    with open(os.path.join(temp_dir, "project.json"), 'w', encoding='utf-8') as f:
        json.dump(project, f, ensure_ascii=False)
    
    # ZIP 생성
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, temp_dir)
                zf.write(file_path, arc_name)
    
    shutil.rmtree(temp_dir)
    
    print(f"[OK] Vrew 프로젝트 생성 완료: {output_path}")
    print(f"   - 클립 수: {len(new_clips)}")
    print(f"   - 이미지 수: {len(image_to_media)}")
    print(f"   - TTS 파일 수: {len(new_clips)}")
    print(f"   - ttsClipInfosMap 항목: {len(tts_clip_infos_map)}")
    
    return output_path
