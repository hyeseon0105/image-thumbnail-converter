"""
이미지 썸네일 변환 도구
이미지들을 1024x1024 크기의 썸네일로 자동 변환합니다.
"""

import os
from pathlib import Path
from PIL import Image
import argparse


def convert_to_thumbnail(input_path, output_dir, size=(1024, 1024), quality=95):
    """
    이미지를 썸네일로 변환합니다.
    
    Args:
        input_path: 입력 이미지 경로
        output_dir: 출력 디렉토리 경로
        size: 썸네일 크기 (기본: 1024x1024)
        quality: JPEG 품질 (1-100, 기본: 95)
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
            
            # 원본 비율 유지하면서 리사이즈
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 1024x1024 캔버스 생성 (흰색 배경)
            canvas = Image.new('RGB', size, (255, 255, 255))
            
            # 이미지를 중앙에 배치
            offset_x = (size[0] - img.size[0]) // 2
            offset_y = (size[1] - img.size[1]) // 2
            canvas.paste(img, (offset_x, offset_y))
            
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


def process_images(input_dir, output_dir=None, size=(1024, 1024), quality=95):
    """
    디렉토리 내의 모든 이미지를 처리합니다.
    
    Args:
        input_dir: 입력 이미지 디렉토리
        output_dir: 출력 디렉토리 (기본: input_dir/thumbnails)
        size: 썸네일 크기
        quality: JPEG 품질
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
    print(f"발견된 이미지: {len(image_files)}개")
    print(f"{'='*60}\n")
    
    # 이미지 변환
    success_count = 0
    for image_file in image_files:
        if convert_to_thumbnail(str(image_file), str(output_path), size, quality):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"변환 완료: {success_count}/{len(image_files)}개 성공")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='이미지를 1024x1024 썸네일로 변환합니다.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python image_thumbnail_converter.py                    # 현재 디렉토리의 이미지 변환
  python image_thumbnail_converter.py -i ./images        # 특정 디렉토리의 이미지 변환
  python image_thumbnail_converter.py -i ./images -o ./output  # 출력 디렉토리 지정
  python image_thumbnail_converter.py -s 512 512         # 크기 변경 (512x512)
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
        default=[1024, 1024],
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
    
    args = parser.parse_args()
    
    process_images(
        input_dir=args.input,
        output_dir=args.output,
        size=tuple(args.size),
        quality=args.quality
    )


if __name__ == '__main__':
    main()
