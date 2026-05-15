"""
이미지 썸네일 변환 도구
이미지들을 1024x1024 크기의 썸네일로 자동 변환합니다.
선택적으로 배경 제거(누끼)도 수행할 수 있습니다.
"""

import os
import time
from pathlib import Path
from PIL import Image, ImageOps
import argparse

TARGET_SIZE = (1024, 1024)
DEFAULT_PADDING = 130

_REMBG_SESSION = None


def get_rembg_session(model_name: str = "u2net"):
    """rembg 세션을 지연 로딩합니다. 모듈이 없으면 안내 메시지를 출력하고 None을 반환합니다."""
    global _REMBG_SESSION
    if _REMBG_SESSION is not None:
        return _REMBG_SESSION
    try:
        from rembg import new_session  # type: ignore
    except ImportError:
        print("[ERROR] rembg가 설치되어 있지 않습니다. `pip install rembg onnxruntime` 후 다시 시도하세요.")
        return None
    _REMBG_SESSION = new_session(model_name)
    return _REMBG_SESSION


def remove_background(img: Image.Image, model_name: str = "u2net") -> Image.Image:
    """rembg로 배경을 제거하고 RGBA 이미지를 반환합니다."""
    from rembg import remove  # type: ignore
    session = get_rembg_session(model_name)
    result = remove(img, session=session)
    if result.mode != "RGBA":
        result = result.convert("RGBA")
    return result


def crop_margins(img, threshold=30):
    """원본 이미지에서 흰색 배경 여백을 제거하고 실제 콘텐츠만 남깁니다."""
    gray = img.convert('L')
    inverted = ImageOps.invert(gray)
    binary = inverted.point(lambda v: 255 if v > threshold else 0)
    bbox = binary.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def crop_alpha_bbox(img: Image.Image, alpha_threshold: int = 10) -> Image.Image:
    """RGBA 이미지에서 불투명 픽셀의 bbox로 잘라냅니다."""
    if img.mode != "RGBA":
        return img
    alpha = img.split()[-1]
    binary = alpha.point(lambda v: 255 if v > alpha_threshold else 0)
    bbox = binary.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def convert_to_thumbnail(
    input_path,
    output_dir,
    size=TARGET_SIZE,
    quality=95,
    padding=DEFAULT_PADDING,
    remove_bg: bool = False,
    output_format: str = "jpeg",
    model_name: str = "u2net",
):
    """
    이미지를 썸네일로 변환합니다.

    Args:
        input_path: 입력 이미지 경로
        output_dir: 출력 디렉토리 경로
        size: 썸네일 크기 (기본: 1024x1024)
        quality: JPEG 품질 (1-100, 기본: 95)
        padding: 실제 콘텐츠와 캔버스 가장자리 사이 여백(px, 기본: 130)
        remove_bg: True면 rembg로 배경 제거 후 처리
        output_format: 'jpeg'(흰 캔버스) 또는 'png'(투명 배경 유지)
        model_name: rembg 모델 이름 (예: u2net, isnet-general-use)
    """
    output_format = output_format.lower()
    if output_format not in ("jpeg", "jpg", "png"):
        raise ValueError(f"지원하지 않는 출력 형식: {output_format}")
    is_png = output_format == "png"

    t0 = time.perf_counter()
    try:
        with Image.open(input_path) as img:
            img.load()

            if remove_bg:
                rgba = remove_background(img, model_name=model_name)
                before_size = rgba.size
                content = crop_alpha_bbox(rgba)
                print(f"  배경 제거 + 알파 크롭: {before_size} -> {content.size}")
            else:
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                before_size = img.size
                content = crop_margins(img)
                print(f"  여백 제거: {before_size} -> {content.size}")

            max_width = size[0] - padding * 2
            max_height = size[1] - padding * 2
            if max_width <= 0 or max_height <= 0:
                raise ValueError(f"패딩 값이 너무 큽니다. 썸네일 크기: {size}, 패딩: {padding}")

            ratio = min(max_width / content.width, max_height / content.height)
            new_width = max(1, round(content.width * ratio))
            new_height = max(1, round(content.height * ratio))
            resized = content.resize((new_width, new_height), Image.Resampling.LANCZOS)

            offset_x = (size[0] - new_width) // 2
            offset_y = (size[1] - new_height) // 2

            if is_png:
                canvas = Image.new('RGBA', size, (0, 0, 0, 0))
                if resized.mode != 'RGBA':
                    resized = resized.convert('RGBA')
                canvas.paste(resized, (offset_x, offset_y), resized)
                ext = 'png'
            else:
                canvas = Image.new('RGB', size, (255, 255, 255))
                if resized.mode == 'RGBA':
                    canvas.paste(resized, (offset_x, offset_y), resized.split()[-1])
                else:
                    canvas.paste(resized, (offset_x, offset_y))
                ext = 'jpg'

            filename = Path(input_path).stem + f'_thumbnail.{ext}'
            output_path = os.path.join(output_dir, filename)

            if is_png:
                canvas.save(output_path, 'PNG', optimize=True)
            else:
                canvas.save(output_path, 'JPEG', quality=quality, optimize=True)
            elapsed = time.perf_counter() - t0
            print(f"[OK] 변환 완료: {Path(input_path).name} -> {filename} ({elapsed:.2f}초)")
            return True

    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(f"[ERROR] 오류 발생 ({Path(input_path).name}, {elapsed:.2f}초 경과): {str(e)}")
        return False


def process_images(
    input_dir,
    output_dir=None,
    size=TARGET_SIZE,
    quality=95,
    padding=DEFAULT_PADDING,
    remove_bg: bool = False,
    output_format: str = "jpeg",
    model_name: str = "u2net",
):
    """디렉토리 내의 모든 이미지를 처리합니다."""
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"오류: 입력 디렉토리를 찾을 수 없습니다: {input_dir}")
        return

    if output_dir is None:
        output_path = input_path / 'thumbnails'
    else:
        output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.tif'}

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
    print(f"배경 제거: {'ON (' + model_name + ')' if remove_bg else 'OFF'}")
    print(f"출력 형식: {output_format.upper()}")
    print(f"발견된 이미지: {len(image_files)}개")
    print(f"{'='*60}\n")

    success_count = 0
    batch_t0 = time.perf_counter()
    for image_file in image_files:
        if convert_to_thumbnail(
            str(image_file),
            str(output_path),
            size=size,
            quality=quality,
            padding=padding,
            remove_bg=remove_bg,
            output_format=output_format,
            model_name=model_name,
        ):
            success_count += 1
    batch_elapsed = time.perf_counter() - batch_t0

    print(f"\n{'='*60}")
    print(f"변환 완료: {success_count}/{len(image_files)}개 성공 · 전체 소요 {batch_elapsed:.2f}초")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='이미지를 1024x1024 썸네일로 변환합니다. (기본 여백 130px, 선택적 배경 제거)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python image_thumbnail_converter.py                          # 현재 디렉토리의 이미지 변환
  python image_thumbnail_converter.py -i ./images              # 특정 디렉토리의 이미지 변환
  python image_thumbnail_converter.py -i ./images -o ./output  # 출력 디렉토리 지정
  python image_thumbnail_converter.py -s 512 512               # 크기 변경 (512x512)
  python image_thumbnail_converter.py -p 130                   # 패딩 변경 (130px)
  python image_thumbnail_converter.py -q 85                    # 품질 조정 (85%)
  python image_thumbnail_converter.py --remove-bg              # 누끼 후 흰 캔버스 JPEG
  python image_thumbnail_converter.py --remove-bg -f png       # 누끼 후 투명 PNG로 저장
        """
    )

    parser.add_argument('-i', '--input', type=str, default='.',
                        help='입력 이미지 디렉토리 (기본: 현재 디렉토리)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='출력 디렉토리 (기본: 입력_디렉토리/thumbnails)')
    parser.add_argument('-s', '--size', type=int, nargs=2, default=list(TARGET_SIZE),
                        metavar=('WIDTH', 'HEIGHT'),
                        help='썸네일 크기 (기본: 1024 1024)')
    parser.add_argument('-q', '--quality', type=int, default=95,
                        choices=range(1, 101), metavar='QUALITY',
                        help='JPEG 품질 1-100 (기본: 95)')
    parser.add_argument('-p', '--padding', type=int, default=DEFAULT_PADDING,
                        metavar='PADDING',
                        help='이미지와 캔버스 가장자리 사이 최소 여백(px, 기본: 130)')
    parser.add_argument('--remove-bg', action='store_true',
                        help='rembg로 배경 제거(누끼)를 수행합니다.')
    parser.add_argument('-f', '--format', type=str, default='jpeg',
                        choices=['jpeg', 'png'],
                        help='출력 형식: jpeg(흰 캔버스) 또는 png(투명 배경). 기본: jpeg')
    parser.add_argument('--model', type=str, default='u2net',
                        help='rembg 모델 이름 (예: u2net, isnet-general-use). 기본: u2net')

    args = parser.parse_args()

    process_images(
        input_dir=args.input,
        output_dir=args.output,
        size=tuple(args.size),
        quality=args.quality,
        padding=args.padding,
        remove_bg=args.remove_bg,
        output_format=args.format,
        model_name=args.model,
    )


if __name__ == '__main__':
    main()
