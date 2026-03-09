"""
이미지 썸네일 변환 도구
이미지들을 1024x1024 크기의 썸네일로 자동 변환합니다.
"""

import os
from pathlib import Path
from PIL import Image
import argparse

TARGET_SIZE = (1024, 1024)
DEFAULT_PADDING = 130


def crop_margins(img, threshold=30):
    """원본 이미지에서 흰색 배경 여백을 제거하고 실제 콘텐츠만 남깁니다."""
    from PIL import ImageOps
    # 그레이스케일로 변환 후 반전: 흰색→0(배경), 어두운색→밝음(콘텐츠)
    gray = img.convert('L')
    inverted = ImageOps.invert(gray)
    # threshold보다 큰 값(=원본에서 충분히 어두운 픽셀)만 콘텐츠로 처리
    binary = inverted.point(lambda v: 255 if v > threshold else 0)
    bbox = binary.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def convert_to_thumbnail(input_path, output_dir, size=TARGET_SIZE, quality=95, padding=DEFAULT_PADDING):
    """
    이미지를 썸네일로 변환합니다.
    
    Args:
        input_path: 입력 이미지 경로
        output_dir: 출력 디렉토리 경로
        size: 썸네일 크기 (기본: 1024x1024)
        quality: JPEG 품질 (1-100, 기본: 95)
        padding: 실제 콘텐츠와 캔버스 가장자리 사이 여백(px, 기본: 130)
    """
    try:
        with Image.open(input_path) as img:
            # RGBA 이미지의 경우 RGB로 변환 (JPEG 저장을 위해)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # 원본 이미지에서 흰색 여백 제거 → 실제 콘텐츠만 남김
            before_size = img.size
            img = crop_margins(img)
            print(f"  여백 제거: {before_size} → {img.size}")

            # 패딩을 고려한 최대 이미지 영역 계산
            max_width = size[0] - padding * 2
            max_height = size[1] - padding * 2
            if max_width <= 0 or max_height <= 0:
                raise ValueError(f"패딩 값이 너무 큽니다. 썸네일 크기: {size}, 패딩: {padding}")

            # 원본 비율을 유지하면서 패딩을 제외한 최대 영역 안에 맞춤
            ratio = min(max_width / img.width, max_height / img.height)
            new_width = max(1, round(img.width * ratio))
            new_height = max(1, round(img.height * ratio))
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 1024x1024 캔버스 생성 (흰색 배경)
            canvas = Image.new('RGB', size, (255, 255, 255))

            # 이미지를 중앙에 배치
            offset_x = (size[0] - new_width) // 2
            offset_y = (size[1] - new_height) // 2
            canvas.paste(resized_img, (offset_x, offset_y))
            
            # 출력 파일명 생성
            filename = Path(input_path).stem + '_thumbnail.jpg'
            output_path = os.path.join(output_dir, filename)
            
            # 저장
            canvas.save(output_path, 'JPEG', quality=quality, optimize=True)
            print(f"[OK] 변환 완료: {Path(input_path).name} -> {filename}")
            return True
            
    except Exception as e:
        print(f"[ERROR] 오류 발생 ({Path(input_path).name}): {str(e)}")
        return False


def process_images(input_dir, output_dir=None, size=TARGET_SIZE, quality=95, padding=DEFAULT_PADDING):
    """
    디렉토리 내의 모든 이미지를 처리합니다.
    
    Args:
        input_dir: 입력 이미지 디렉토리
        output_dir: 출력 디렉토리 (기본: input_dir/thumbnails)
        size: 썸네일 크기
        quality: JPEG 품질
        padding: 이미지와 캔버스 가장자리 사이 최소 여백(px, 기본: 130)
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"오류: 입력 디렉토리를 찾을 수 없습니다: {input_dir}")
        return
    
    # 출력 디렉토리 설정
    if output_dir is None:
        output_path = input_path / 'thumbnails'
    else:
        output_path = Path(output_dir)
    
    # 출력 디렉토리 생성
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 지원하는 이미지 확장자
    supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
    
    # 이미지 파일 찾기
    image_files = [
        f for f in input_path.iterdir()
        if f.is_file() and f.suffix.lower() in supported_extensions
    ]
    
    if not image_files:
        print(f"경고: {input_dir}에서 이미지 파일을 찾을 수 없습니다.")
        return
    
    print(f"\n{'='*60}")
    print(f"이미지 썸네일 변환 시작")
    print(f"{'='*60}")
    print(f"입력 디렉토리: {input_path}")
    print(f"출력 디렉토리: {output_path}")
    print(f"썸네일 크기: {size[0]}x{size[1]}")
    print(f"패딩: {padding}px")
    print(f"발견된 이미지: {len(image_files)}개")
    print(f"{'='*60}\n")
    
    # 이미지 변환
    success_count = 0
    for image_file in image_files:
        if convert_to_thumbnail(str(image_file), str(output_path), size, quality, padding):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"변환 완료: {success_count}/{len(image_files)}개 성공")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='이미지를 1024x1024 썸네일로 변환합니다. (기본 여백 130px)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python image_thumbnail_converter.py                    # 현재 디렉토리의 이미지 변환
  python image_thumbnail_converter.py -i ./images        # 특정 디렉토리의 이미지 변환
  python image_thumbnail_converter.py -i ./images -o ./output  # 출력 디렉토리 지정
  python image_thumbnail_converter.py -s 512 512         # 크기 변경 (512x512)
  python image_thumbnail_converter.py -p 130             # 패딩 변경 (130px)
  python image_thumbnail_converter.py -q 85              # 품질 조정 (85%)
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        default='.',
        help='입력 이미지 디렉토리 (기본: 현재 디렉토리)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='출력 디렉토리 (기본: 입력_디렉토리/thumbnails)'
    )
    
    parser.add_argument(
        '-s', '--size',
        type=int,
        nargs=2,
        default=list(TARGET_SIZE),
        metavar=('WIDTH', 'HEIGHT'),
        help='썸네일 크기 (기본: 1024 1024)'
    )
    
    parser.add_argument(
        '-q', '--quality',
        type=int,
        default=95,
        choices=range(1, 101),
        metavar='QUALITY',
        help='JPEG 품질 1-100 (기본: 95)'
    )

    parser.add_argument(
        '-p', '--padding',
        type=int,
        default=DEFAULT_PADDING,
        metavar='PADDING',
        help='이미지와 캔버스 가장자리 사이 최소 여백(px, 기본: 130)'
    )
    
    args = parser.parse_args()
    
    process_images(
        input_dir=args.input,
        output_dir=args.output,
        size=tuple(args.size),
        quality=args.quality,
        padding=args.padding
    )


if __name__ == '__main__':
    main()
