"""
이미지 생성 모듈
- Pollinations.ai (무료, API 키 불필요) ⭐
- Replicate (FLUX) - 유료
- 플레이스홀더 이미지 생성
"""

import os
import requests
import urllib.parse
import base64
from typing import Optional
import time

# API 키 설정
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")


def generate_image_pollinations(prompt: str, output_path: str, 
                                width: int = 1920, height: int = 1080) -> Optional[str]:
    """
    Pollinations.ai로 이미지 생성 (무료, API 키 불필요!)
    
    Args:
        prompt: 이미지 프롬프트 (영어)
        output_path: 저장 경로
        width: 이미지 너비 (기본 1920)
        height: 이미지 높이 (기본 1080)
    
    Returns:
        저장된 이미지 경로 또는 None
    """
    try:
        # URL 인코딩
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Pollinations.ai URL (16:9, 로고 없음)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
        
        print(f"[Pollinations] 생성 중: {prompt[:50]}...")
        
        # 이미지 다운로드 (타임아웃 120초)
        response = requests.get(url, timeout=120)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"[Pollinations] ✅ 완료: {output_path}")
            return output_path
        else:
            print(f"[Pollinations] ❌ 실패: HTTP {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"[Pollinations] ❌ 타임아웃 (120초 초과)")
        return None
    except Exception as e:
        print(f"[Pollinations] ❌ 오류: {e}")
        return None


def generate_images_batch_pollinations(prompts: list, output_dir: str, 
                                       delay: float = 3.0,
                                       progress_callback=None) -> list:
    """
    여러 이미지 일괄 생성 (Pollinations.ai - 무료)
    
    Args:
        prompts: 프롬프트 딕셔너리 리스트 [{"prompt": "...", "text": "..."}]
        output_dir: 출력 폴더
        delay: 요청 간 딜레이 (초) - 서버 부하 방지
        progress_callback: 진행률 콜백 함수
    
    Returns:
        생성된 이미지 경로 리스트
    """
    os.makedirs(output_dir, exist_ok=True)
    
    generated_images = []
    total = len(prompts)
    
    for i, p in enumerate(prompts):
        prompt_text = p.get('prompt', p.get('text', f'scene {i+1}'))
        output_path = os.path.join(output_dir, f"scene_{i+1:03d}.png")
        
        if progress_callback:
            progress_callback(i + 1, total, f"이미지 {i+1}/{total} 생성 중...")
        
        result = generate_image_pollinations(prompt_text, output_path)
        
        if result:
            generated_images.append(result)
        else:
            # 실패시 플레이스홀더 생성
            placeholder = generate_placeholder_image(
                p.get('text', f'Scene {i+1}'),
                output_path
            )
            if placeholder:
                generated_images.append(placeholder)
        
        # 다음 요청 전 딜레이 (마지막 제외)
        if i < total - 1:
            time.sleep(delay)
    
    return generated_images


def generate_image_replicate(prompt: str, output_path: str, 
                             model: str = "black-forest-labs/flux-schnell") -> Optional[str]:
    """
    Replicate API를 통해 이미지 생성 (FLUX 모델)
    
    Args:
        prompt: 이미지 프롬프트
        output_path: 저장할 파일 경로
        model: 사용할 모델
    
    Returns:
        생성된 이미지 경로 또는 None
    """
    
    if not REPLICATE_API_TOKEN:
        print("[Replicate API 토큰이 설정되지 않았습니다]")
        return None
    
    try:
        import replicate
        
        output = replicate.run(
            model,
            input={
                "prompt": prompt,
                "num_outputs": 1,
                "aspect_ratio": "16:9",
                "output_format": "png"
            }
        )
        
        # 이미지 다운로드
        if output and len(output) > 0:
            image_url = output[0]
            response = requests.get(image_url)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return output_path
    
    except Exception as e:
        print(f"[이미지 생성 오류: {str(e)}]")
        return None


def generate_placeholder_image(text: str, output_path: str, 
                               width: int = 1920, height: int = 1080) -> str:
    """
    플레이스홀더 이미지 생성 (API 없이 테스트용)
    
    Args:
        text: 이미지에 표시할 텍스트
        output_path: 저장할 파일 경로
        width: 이미지 너비
        height: 이미지 높이
    
    Returns:
        생성된 이미지 경로
    """
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 그라데이션 배경 생성
        img = Image.new('RGB', (width, height), color=(30, 30, 50))
        draw = ImageDraw.Draw(img)
        
        # 그라데이션 효과
        for i in range(height):
            r = int(30 + (i / height) * 20)
            g = int(30 + (i / height) * 30)
            b = int(50 + (i / height) * 40)
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        
        # 텍스트 추가
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        # 텍스트 줄바꿈
        max_chars = 40
        lines = []
        words = text.split()
        current_line = ""
        
        for word in words:
            if len(current_line + word) < max_chars:
                current_line += word + " "
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.strip())
        
        # 텍스트 그리기
        y_offset = height // 2 - (len(lines) * 25)
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            
            # 그림자 효과
            draw.text((x+2, y_offset+2), line, font=font, fill=(0, 0, 0))
            draw.text((x, y_offset), line, font=font, fill=(255, 255, 255))
            y_offset += 50
        
        # 테두리
        draw.rectangle([(10, 10), (width-10, height-10)], outline=(100, 100, 150), width=3)
        
        img.save(output_path)
        return output_path
    
    except ImportError:
        # PIL 없으면 단순 파일 생성
        print("[PIL 라이브러리가 없습니다. 빈 이미지를 생성합니다.]")
        
        # 간단한 PNG 생성 (1x1 픽셀)
        # 실제로는 PIL 설치 필요
        return None


def generate_images_batch(prompts: list, output_dir: str, 
                          use_api: bool = False) -> list:
    """
    여러 이미지 일괄 생성
    
    Args:
        prompts: 프롬프트 정보 리스트 [{"prompt": "...", "text": "..."}, ...]
        output_dir: 출력 디렉토리
        use_api: API 사용 여부 (False면 플레이스홀더)
    
    Returns:
        생성된 이미지 경로 리스트
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    generated_images = []
    
    for i, prompt_info in enumerate(prompts):
        output_path = os.path.join(output_dir, f"scene_{i+1:03d}.png")
        
        if use_api and REPLICATE_API_TOKEN:
            result = generate_image_replicate(
                prompt_info.get("prompt", prompt_info.get("text", "")),
                output_path
            )
        else:
            result = generate_placeholder_image(
                prompt_info.get("text", f"Scene {i+1}"),
                output_path
            )
        
        if result:
            generated_images.append({
                "index": i,
                "path": result,
                "text": prompt_info.get("text", ""),
                "prompt": prompt_info.get("prompt", "")
            })
            print(f"[{i+1}/{len(prompts)}] 이미지 생성 완료: {output_path}")
        else:
            print(f"[{i+1}/{len(prompts)}] 이미지 생성 실패")
        
        # API 호출 시 딜레이
        if use_api:
            time.sleep(1)
    
    return generated_images


def download_image(url: str, output_path: str) -> Optional[str]:
    """
    URL에서 이미지 다운로드
    
    Args:
        url: 이미지 URL
        output_path: 저장할 파일 경로
    
    Returns:
        저장된 파일 경로 또는 None
    """
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        return output_path
    
    except Exception as e:
        print(f"[이미지 다운로드 오류: {str(e)}]")
        return None


if __name__ == "__main__":
    # 테스트
    test_prompts = [
        {"text": "첫 번째 장면: 탄광 마을의 아침", "prompt": "Korean mining village, morning, 1990s"},
        {"text": "두 번째 장면: 리철의 결심", "prompt": "Korean man, determined expression, dramatic lighting"},
    ]
    
    results = generate_images_batch(test_prompts, "test_images", use_api=False)
    print(f"\n생성된 이미지: {len(results)}개")
