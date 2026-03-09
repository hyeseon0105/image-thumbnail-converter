"""
이미지 썸네일 변환 도구 - Streamlit 웹 앱
"""

import io
import zipfile
import streamlit as st
from PIL import Image, ImageOps

TARGET_SIZE = (1024, 1024)
DEFAULT_PADDING = 130


def crop_margins(img, threshold=30):
    """원본 이미지에서 흰색 배경 여백을 제거하고 실제 콘텐츠만 남깁니다."""
    gray = img.convert('L')
    inverted = ImageOps.invert(gray)
    binary = inverted.point(lambda v: 255 if v > threshold else 0)
    bbox = binary.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def convert_image(img: Image.Image, size=TARGET_SIZE, quality=95, padding=DEFAULT_PADDING) -> bytes:
    """
    PIL Image를 받아 썸네일로 변환하고 JPEG bytes를 반환합니다.
    """
    # 모드 변환
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # 흰색 여백 제거
    img = crop_margins(img)

    # 패딩을 고려한 최대 영역
    max_width = size[0] - padding * 2
    max_height = size[1] - padding * 2
    if max_width <= 0 or max_height <= 0:
        raise ValueError(f"패딩 값이 너무 큽니다. (캔버스: {size}, 패딩: {padding})")

    # 비율 유지 리사이즈
    ratio = min(max_width / img.width, max_height / img.height)
    new_width = max(1, round(img.width * ratio))
    new_height = max(1, round(img.height * ratio))
    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 캔버스에 중앙 배치
    canvas = Image.new('RGB', size, (255, 255, 255))
    offset_x = (size[0] - new_width) // 2
    offset_y = (size[1] - new_height) // 2
    canvas.paste(resized, (offset_x, offset_y))

    buf = io.BytesIO()
    canvas.save(buf, format='JPEG', quality=quality, optimize=True)
    return buf.getvalue(), canvas


# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="이미지 썸네일 변환기",
    page_icon="🖼️",
    layout="wide",
)

st.title("🖼️ 이미지 썸네일 변환기")
st.caption("이미지를 1024×1024 썸네일로 변환합니다. 흰색 여백 자동 제거 후 지정 패딩 적용.")

# ── 사이드바 설정 ─────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 변환 설정")

    canvas_w = st.number_input("캔버스 너비 (px)", min_value=64, max_value=4096, value=1024, step=64)
    canvas_h = st.number_input("캔버스 높이 (px)", min_value=64, max_value=4096, value=1024, step=64)
    padding = st.slider("패딩 (px)", min_value=0, max_value=400, value=DEFAULT_PADDING, step=10,
                        help="이미지 콘텐츠와 캔버스 가장자리 사이 최소 여백")
    quality = st.slider("JPEG 품질", min_value=1, max_value=100, value=95,
                        help="숫자가 높을수록 화질이 좋고 파일 크기가 커집니다.")

    st.divider()
    st.markdown(f"""
    **현재 설정 요약**
    - 캔버스: `{canvas_w} × {canvas_h}` px
    - 패딩: `{padding}` px
    - 콘텐츠 최대 영역: `{canvas_w - padding*2} × {canvas_h - padding*2}` px
    - JPEG 품질: `{quality}`
    """)

size = (int(canvas_w), int(canvas_h))

# ── 파일 업로드 ───────────────────────────────────────────
uploaded_files = st.file_uploader(
    "이미지 파일을 업로드하세요 (여러 장 가능)",
    type=["jpg", "jpeg", "png", "bmp", "gif", "webp", "tiff", "tif"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("이미지를 업로드하면 변환 결과를 바로 미리볼 수 있습니다.")
    st.stop()

# ── 변환 및 미리보기 ──────────────────────────────────────
st.divider()
st.subheader(f"변환 결과 — 총 {len(uploaded_files)}장")

results = []  # (파일명, jpeg_bytes, canvas)

for uploaded_file in uploaded_files:
    try:
        original = Image.open(uploaded_file)
        jpeg_bytes, canvas = convert_image(original.copy(), size=size, quality=quality, padding=padding)
        results.append((uploaded_file.name, jpeg_bytes, canvas, original))
    except Exception as e:
        st.error(f"❌ {uploaded_file.name} 변환 실패: {e}")

# 2열 그리드로 원본 / 변환 결과 나란히 표시
for i, (name, jpeg_bytes, canvas, original) in enumerate(results):
    with st.container(border=True):
        col_orig, col_thumb = st.columns(2)

        with col_orig:
            st.caption("원본")
            st.image(original, use_container_width=True)
            st.markdown(f"`{original.width} × {original.height}` px")

        with col_thumb:
            st.caption(f"변환 결과 ({size[0]}×{size[1]}, 패딩 {padding}px)")
            st.image(canvas, use_container_width=True)
            stem = name.rsplit('.', 1)[0]
            out_name = stem + '_thumbnail.jpg'
            st.download_button(
                label="⬇️ 다운로드",
                data=jpeg_bytes,
                file_name=out_name,
                mime="image/jpeg",
                key=f"dl_{i}_{name}",
            )

# ── 전체 ZIP 다운로드 ────────────────────────────────────
if len(results) > 1:
    st.divider()
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, jpeg_bytes, _, _ in results:
            stem = name.rsplit('.', 1)[0]
            zf.writestr(stem + '_thumbnail.jpg', jpeg_bytes)
    st.download_button(
        label=f"⬇️ 전체 {len(results)}장 ZIP으로 다운로드",
        data=zip_buf.getvalue(),
        file_name="thumbnails.zip",
        mime="application/zip",
    )
