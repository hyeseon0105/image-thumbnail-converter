"""
이미지 썸네일 변환 도구 - Streamlit 웹 앱
- 흰색 여백 자동 제거 후 지정 패딩으로 중앙 배치
- 선택적으로 rembg를 이용한 배경 제거(누끼) 기능 지원
"""

import io
import time
import zipfile
import streamlit as st
from PIL import Image, ImageOps

TARGET_SIZE = (1024, 1024)
DEFAULT_PADDING = 130
MAX_FILES = 50
PREVIEW_LIMIT = 10

WEB_SIZE_PRESETS = {
    "1024 × 1024 기본 썸네일": (1024, 1024),
    "800 × 800 작은 웹 이미지": (800, 800),
    "1080 × 1080 SNS 정사각": (1080, 1080),
    "1200 × 1200 쇼핑몰 대표": (1200, 1200),
    "1920 × 1080 와이드": (1920, 1080),
}

PRINT_SIZE_PRESETS = {
    "100 × 100 mm / 300 DPI": (100.0, 100.0, "mm", 300),
    "10 × 10 cm / 300 DPI": (10.0, 10.0, "cm", 300),
    "명함 90 × 50 mm / 300 DPI": (90.0, 50.0, "mm", 300),
    "엽서 100 × 148 mm / 300 DPI": (100.0, 148.0, "mm", 300),
    "A4 210 × 297 mm / 300 DPI": (210.0, 297.0, "mm", 300),
}


def format_elapsed(seconds: float) -> str:
    """사람이 읽기 쉬운 소요 시간 문자열."""
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    return f"{seconds:.2f}초"


def print_size_to_pixels(width: float, height: float, unit: str, dpi: int) -> tuple[int, int]:
    """인쇄 크기(mm/cm)와 DPI를 실제 픽셀 크기로 변환합니다."""
    unit_to_inches = 25.4 if unit == "mm" else 2.54
    pixel_width = max(1, round(width / unit_to_inches * dpi))
    pixel_height = max(1, round(height / unit_to_inches * dpi))
    return pixel_width, pixel_height


def apply_web_preset():
    """웹용 프리셋 선택 시 canvas 값을 session_state에 채워 넣습니다."""
    selected = st.session_state.get("web_preset_select")
    if selected and selected in WEB_SIZE_PRESETS:
        w, h = WEB_SIZE_PRESETS[selected]
        st.session_state.canvas_w = int(w)
        st.session_state.canvas_h = int(h)


def apply_print_preset():
    """인쇄용 프리셋 선택 시 print_w/print_h/단위/DPI를 session_state에 채워 넣습니다."""
    selected = st.session_state.get("print_preset_select")
    if selected and selected in PRINT_SIZE_PRESETS:
        w, h, unit, dpi = PRINT_SIZE_PRESETS[selected]
        st.session_state.print_w = float(w)
        st.session_state.print_h = float(h)
        st.session_state.print_unit = unit
        st.session_state.print_dpi = int(dpi)


@st.cache_resource(show_spinner="배경 제거 모델 로딩 중...")
def get_rembg_session(model_name: str = "u2net"):
    """rembg 세션을 한 번만 만들고 캐시합니다."""
    from rembg import new_session  # type: ignore
    return new_session(model_name)


def remove_background(img: Image.Image, model_name: str = "u2net") -> Image.Image:
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
    """RGBA 이미지에서 불투명 영역의 bbox로 잘라냅니다."""
    if img.mode != "RGBA":
        return img
    alpha = img.split()[-1]
    binary = alpha.point(lambda v: 255 if v > alpha_threshold else 0)
    bbox = binary.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def convert_image(
    img: Image.Image,
    size=TARGET_SIZE,
    quality=95,
    padding=DEFAULT_PADDING,
    remove_bg: bool = False,
    output_format: str = "jpeg",
    model_name: str = "u2net",
):
    """
    PIL Image를 받아 썸네일로 변환합니다.

    Returns:
        (bytes, canvas_image, mime, extension)
    """
    output_format = output_format.lower()
    is_png = output_format == "png"

    if remove_bg:
        rgba = remove_background(img, model_name=model_name)
        content = crop_alpha_bbox(rgba)
    else:
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        content = crop_margins(img)

    max_width = size[0] - padding * 2
    max_height = size[1] - padding * 2
    if max_width <= 0 or max_height <= 0:
        raise ValueError(f"패딩 값이 너무 큽니다. (캔버스: {size}, 패딩: {padding})")

    ratio = min(max_width / content.width, max_height / content.height)
    new_width = max(1, round(content.width * ratio))
    new_height = max(1, round(content.height * ratio))
    resized = content.resize((new_width, new_height), Image.Resampling.LANCZOS)

    offset_x = (size[0] - new_width) // 2
    offset_y = (size[1] - new_height) // 2

    buf = io.BytesIO()
    if is_png:
        canvas = Image.new('RGBA', size, (0, 0, 0, 0))
        if resized.mode != 'RGBA':
            resized = resized.convert('RGBA')
        canvas.paste(resized, (offset_x, offset_y), resized)
        canvas.save(buf, format='PNG', optimize=True)
        return buf.getvalue(), canvas, "image/png", "png"
    else:
        canvas = Image.new('RGB', size, (255, 255, 255))
        if resized.mode == 'RGBA':
            canvas.paste(resized, (offset_x, offset_y), resized.split()[-1])
        else:
            canvas.paste(resized, (offset_x, offset_y))
        canvas.save(buf, format='JPEG', quality=quality, optimize=True)
        return buf.getvalue(), canvas, "image/jpeg", "jpg"


# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="이미지 썸네일 변환기",
    page_icon="🖼️",
    layout="wide",
)

st.title("🖼️ 이미지 썸네일 변환기")
st.caption("이미지를 1024×1024 썸네일로 변환합니다. 흰색 여백 자동 제거 또는 누끼(배경 제거)를 선택할 수 있습니다.")

# ── 사이드바 설정 ─────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 변환 설정")

    st.subheader("📏 해상도")
    resolution_mode = st.radio(
        "해상도 용도",
        options=["웹용(px)", "인쇄용(mm/cm + DPI)"],
        horizontal=True,
    )

    st.session_state.setdefault("canvas_w", 1024)
    st.session_state.setdefault("canvas_h", 1024)
    st.session_state.setdefault("print_w", 100.0)
    st.session_state.setdefault("print_h", 100.0)
    st.session_state.setdefault("print_unit", "mm")
    st.session_state.setdefault("print_dpi", 300)

    print_info = None
    if resolution_mode == "웹용(px)":
        web_preset = st.selectbox(
            "웹용 프리셋",
            options=[*WEB_SIZE_PRESETS.keys(), "직접 입력"],
            key="web_preset_select",
            on_change=apply_web_preset,
            help="프리셋을 고르면 그 크기가 우선 적용됩니다. 원하는 숫자를 쓰려면 직접 입력을 선택하세요.",
        )
        if web_preset == "직접 입력":
            canvas_w = st.number_input("캔버스 너비 (px)", min_value=64, max_value=8192, step=64, key="canvas_w")
            canvas_h = st.number_input("캔버스 높이 (px)", min_value=64, max_value=8192, step=64, key="canvas_h")
        else:
            canvas_w, canvas_h = WEB_SIZE_PRESETS[web_preset]
            st.number_input("캔버스 너비 (px)", min_value=64, max_value=8192, value=canvas_w, step=64, disabled=True)
            st.number_input("캔버스 높이 (px)", min_value=64, max_value=8192, value=canvas_h, step=64, disabled=True)
    else:
        print_preset = st.selectbox(
            "인쇄용 프리셋",
            options=[*PRINT_SIZE_PRESETS.keys(), "직접 입력"],
            key="print_preset_select",
            on_change=apply_print_preset,
            help="프리셋을 고르면 그 크기와 DPI가 우선 적용됩니다. 원하는 숫자를 쓰려면 직접 입력을 선택하세요.",
        )
        if print_preset == "직접 입력":
            print_unit = st.radio("단위", options=["mm", "cm"], horizontal=True, key="print_unit")
            print_w = st.number_input(f"인쇄 너비 ({print_unit})", min_value=1.0, max_value=1000.0, step=1.0, key="print_w")
            print_h = st.number_input(f"인쇄 높이 ({print_unit})", min_value=1.0, max_value=1000.0, step=1.0, key="print_h")
            dpi = st.selectbox("DPI", options=[72, 150, 300, 600], key="print_dpi")
        else:
            print_w, print_h, print_unit, dpi = PRINT_SIZE_PRESETS[print_preset]
            st.radio(
                "단위",
                options=["mm", "cm"],
                index=["mm", "cm"].index(print_unit),
                horizontal=True,
                disabled=True,
            )
            st.number_input(f"인쇄 너비 ({print_unit})", min_value=1.0, max_value=1000.0, value=print_w, step=1.0, disabled=True)
            st.number_input(f"인쇄 높이 ({print_unit})", min_value=1.0, max_value=1000.0, value=print_h, step=1.0, disabled=True)
            st.selectbox("DPI", options=[72, 150, 300, 600], index=[72, 150, 300, 600].index(dpi), disabled=True)

        canvas_w, canvas_h = print_size_to_pixels(print_w, print_h, print_unit, int(dpi))
        print_info = f"{print_w:g} × {print_h:g} {print_unit} / {dpi} DPI"
        st.caption(f"계산된 캔버스: `{canvas_w} × {canvas_h}` px")
        if canvas_w * canvas_h > 16_000_000:
            st.warning("계산된 해상도가 큽니다. 누끼/변환 시간이 길어질 수 있습니다.")

    padding = st.slider("패딩 (px)", min_value=0, max_value=400, value=DEFAULT_PADDING, step=10,
                        help="이미지 콘텐츠와 캔버스 가장자리 사이 최소 여백")

    st.divider()
    st.subheader("✂️ 배경 제거(누끼)")
    remove_bg = st.toggle(
        "배경 제거 사용",
        value=False,
        help="rembg(U²-Net 등)로 자동 누끼를 수행합니다. 첫 실행 시 모델 다운로드가 발생할 수 있습니다.",
    )
    model_name = st.selectbox(
        "rembg 모델",
        options=["u2net", "u2netp", "isnet-general-use", "silueta"],
        index=0,
        disabled=not remove_bg,
        help="u2net: 표준 / u2netp: 경량·빠름 / isnet-general-use: 고품질 / silueta: 인물 등",
    )

    output_format = st.radio(
        "출력 형식",
        options=["JPEG (흰 배경)", "PNG (투명 배경)"],
        index=1 if remove_bg else 0,
        help="투명 배경을 유지하려면 PNG를 선택하세요. JPEG는 흰 캔버스 위에 합성됩니다.",
    )
    out_fmt = "png" if output_format.startswith("PNG") else "jpeg"

    quality = st.slider(
        "JPEG 품질",
        min_value=1, max_value=100, value=95,
        disabled=(out_fmt == "png"),
        help="JPEG에만 적용됩니다. 숫자가 높을수록 화질이 좋고 파일 크기가 커집니다.",
    )

    st.divider()
    st.markdown(f"""
    **현재 설정 요약**
    - 해상도 용도: `{resolution_mode}`
    {f"- 인쇄 크기: `{print_info}`" if print_info else ""}
    - 캔버스: `{canvas_w} × {canvas_h}` px
    - 패딩: `{padding}` px
    - 콘텐츠 최대 영역: `{canvas_w - padding*2} × {canvas_h - padding*2}` px
    - 배경 제거: `{'ON (' + model_name + ')' if remove_bg else 'OFF'}`
    - 출력: `{out_fmt.upper()}`{' / 품질 ' + str(quality) if out_fmt == 'jpeg' else ''}
    """)

size = (int(canvas_w), int(canvas_h))

# ── 파일 업로드 ───────────────────────────────────────────
uploaded_files = st.file_uploader(
    f"이미지 파일을 업로드하세요 (최대 {MAX_FILES}개)",
    type=["jpg", "jpeg", "png", "bmp", "gif", "webp", "tiff", "tif"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("이미지를 업로드하면 변환 결과를 바로 미리볼 수 있습니다.")
    st.stop()

if len(uploaded_files) > MAX_FILES:
    st.error(f"이미지는 최대 {MAX_FILES}개까지 업로드 가능합니다.")
    st.stop()

# ── 변환 및 미리보기 ──────────────────────────────────────
st.divider()
st.subheader(f"변환 결과 — 총 {len(uploaded_files)}장")
if remove_bg:
    st.caption("⏳ 배경 제거는 이미지당 수 초가 걸릴 수 있습니다. (CPU 기준)")

results = []  # (파일명, bytes, canvas, original, mime, ext, elapsed_sec)

progress = st.progress(0.0, text="변환 준비 중...")
for idx, uploaded_file in enumerate(uploaded_files, start=1):
    progress.progress((idx - 1) / len(uploaded_files), text=f"변환 중... {uploaded_file.name}")
    try:
        t0 = time.perf_counter()
        original = Image.open(uploaded_file)
        original.load()
        data, canvas, mime, ext = convert_image(
            original.copy(),
            size=size,
            quality=quality,
            padding=padding,
            remove_bg=remove_bg,
            output_format=out_fmt,
            model_name=model_name,
        )
        elapsed = time.perf_counter() - t0
        results.append((uploaded_file.name, data, canvas, original, mime, ext, elapsed))
    except Exception as e:
        st.error(f"❌ {uploaded_file.name} 변환 실패: {e}")
progress.progress(1.0, text="완료")
progress.empty()

if results:
    total_sec = sum(r[6] for r in results)
    avg_sec = total_sec / len(results)
    st.success(
        f"변환 완료 — **{len(results)}**장 · 합계 **{format_elapsed(total_sec)}** "
        f"(평균 **{format_elapsed(avg_sec)}**/장)"
    )

# 2열 그리드로 원본 / 변환 결과 나란히 표시 (최대 PREVIEW_LIMIT개)
for i, (name, data, canvas, original, mime, ext, elapsed) in enumerate(results):
    if i >= PREVIEW_LIMIT:
        st.info(f"미리보기는 처음 {PREVIEW_LIMIT}개까지만 표시됩니다. 아래 ZIP 다운로드를 이용하세요.")
        break
    with st.container(border=True):
        col_orig, col_thumb = st.columns(2)

        with col_orig:
            st.caption("원본")
            st.image(original, width="stretch")
            st.markdown(f"`{original.width} × {original.height}` px")

        with col_thumb:
            label = f"변환 결과 ({size[0]}×{size[1]}, 패딩 {padding}px"
            if remove_bg:
                label += ", 누끼"
            label += f", {ext.upper()}) · ⏱ {format_elapsed(elapsed)}"
            st.caption(label)
            st.image(canvas, width="stretch")
            stem = name.rsplit('.', 1)[0]
            out_name = f"{stem}_thumbnail.{ext}"
            st.download_button(
                label="⬇️ 다운로드",
                data=data,
                file_name=out_name,
                mime=mime,
                key=f"dl_{i}_{name}",
            )

# ── 전체 ZIP 다운로드 ────────────────────────────────────
if len(results) > 1:
    st.divider()
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, data, _, _, _, ext, _ in results:
            stem = name.rsplit('.', 1)[0]
            zf.writestr(f"{stem}_thumbnail.{ext}", data)
    st.download_button(
        label=f"⬇️ 전체 {len(results)}장 ZIP으로 다운로드",
        data=zip_buf.getvalue(),
        file_name="thumbnails.zip",
        mime="application/zip",
    )
