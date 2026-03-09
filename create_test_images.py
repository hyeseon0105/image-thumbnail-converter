"""
테스트용 샘플 이미지 생성 스크립트
다양한 크기와 비율의 이미지를 생성합니다.
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_test_image(filename, size, color, text):
    """
    테스트용 이미지를 생성합니다.
    
    Args:
        filename: 저장할 파일명
        size: 이미지 크기 (width, height)
        color: 배경색 (R, G, B)
        text: 이미지에 표시할 텍스트
    """
    # 이미지 생성
    img = Image.new('RGB', size, color)
    draw = ImageDraw.Draw(img)
    
    # 그라디언트 효과
    for y in range(size[1]):
        alpha = y / size[1]
        new_color = tuple(int(c * (1 - alpha * 0.3)) for c in color)
        draw.rectangle([(0, y), (size[0], y + 1)], fill=new_color)
    
    # 장식 원 그리기
    circle_color = tuple(min(255, c + 50) for c in color)
    draw.ellipse([(size[0] * 0.1, size[1] * 0.1), 
                  (size[0] * 0.3, size[1] * 0.3)], 
                 fill=circle_color)
    draw.ellipse([(size[0] * 0.7, size[1] * 0.6), 
                  (size[0] * 0.9, size[1] * 0.8)], 
                 fill=circle_color)
    
    # 크기 정보 텍스트
    size_text = f"{size[0]} x {size[1]}"
    
    # 텍스트를 이미지 중앙에 배치
    try:
        # 시스템 기본 폰트 사용 시도
        font_large = ImageFont.truetype("arial.ttf", 60)
        font_small = ImageFont.truetype("arial.ttf", 40)
    except:
        # 기본 폰트 사용
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 텍스트 위치 계산
    bbox1 = draw.textbbox((0, 0), text, font=font_large)
    text_width1 = bbox1[2] - bbox1[0]
    text_height1 = bbox1[3] - bbox1[1]
    
    bbox2 = draw.textbbox((0, 0), size_text, font=font_small)
    text_width2 = bbox2[2] - bbox2[0]
    text_height2 = bbox2[3] - bbox2[1]
    
    x1 = (size[0] - text_width1) // 2
    y1 = (size[1] - text_height1) // 2 - 40
    
    x2 = (size[0] - text_width2) // 2
    y2 = (size[1] - text_height2) // 2 + 40
    
    # 텍스트 그림자
    shadow_color = (0, 0, 0)
    draw.text((x1 + 3, y1 + 3), text, fill=shadow_color, font=font_large)
    draw.text((x2 + 2, y2 + 2), size_text, fill=shadow_color, font=font_small)
    
    # 실제 텍스트
    text_color = (255, 255, 255)
    draw.text((x1, y1), text, fill=text_color, font=font_large)
    draw.text((x2, y2), size_text, fill=text_color, font=font_small)
    
    # 테두리
    border_color = tuple(max(0, c - 50) for c in color)
    draw.rectangle([(0, 0), (size[0] - 1, size[1] - 1)], 
                   outline=border_color, width=5)
    
    # 저장
    img.save(filename, 'JPEG', quality=95)
    print(f"[OK] 생성됨: {filename} ({size[0]}x{size[1]})")


def main():
    """테스트 이미지들을 생성합니다."""
    
    # test_images 디렉토리 생성
    os.makedirs('test_images', exist_ok=True)
    
    print("\n" + "=" * 60)
    print("테스트 이미지 생성 중...")
    print("=" * 60 + "\n")
    
    # 다양한 크기의 테스트 이미지 생성
    test_cases = [
        # (파일명, 크기, 색상, 텍스트)
        ('test_images/product_01_square.jpg', (1500, 1500), (255, 107, 107), '제품 1'),
        ('test_images/product_02_landscape.jpg', (2000, 1200), (78, 205, 196), '제품 2'),
        ('test_images/product_03_portrait.jpg', (800, 1400), (255, 195, 0), '제품 3'),
        ('test_images/product_04_wide.jpg', (3000, 1000), (147, 51, 234), '제품 4'),
        ('test_images/product_05_tall.jpg', (600, 2000), (255, 135, 189), '제품 5'),
        ('test_images/product_06_small.jpg', (400, 400), (52, 152, 219), '제품 6'),
        ('test_images/product_07_hd.jpg', (1920, 1080), (46, 204, 113), '제품 7'),
        ('test_images/product_08_large.jpg', (2500, 2500), (241, 90, 90), '제품 8'),
    ]
    
    for filename, size, color, text in test_cases:
        create_test_image(filename, size, color, text)
    
    print("\n" + "=" * 60)
    print(f"[SUCCESS] 총 {len(test_cases)}개의 테스트 이미지가 생성되었습니다!")
    print("[INFO] 위치: test_images 폴더")
    print("\n다음 단계:")
    print("1. python image_thumbnail_converter.py -i test_images")
    print("2. test_viewer.html 파일을 브라우저로 열기")
    print("3. 원본과 썸네일 이미지를 드래그하여 비교하기")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
