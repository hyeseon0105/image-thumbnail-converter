"""
Streamlit detail page generator.

Sidebar inputs are reflected immediately in the right-side preview.
"""

import base64
import hashlib
import html
import json
import re
import tempfile
import uuid
from datetime import datetime, timezone
from textwrap import dedent
from pathlib import Path

import streamlit as st

try:
    from streamlit_sortables import sort_items
except ImportError:
    sort_items = None


SECTION_NAMES = {
    "points": "제품포인트",
    "features": "기능설명",
    "examples": "사용예시",
    "trust": "신뢰성",
    "specs": "규격정보",
}

CHECKPOINT_SECTION_OPTIONS = {
    "제품포인트": "points",
    "기능설명": "features",
    "사용예시": "examples",
    "신뢰성": "trust",
}

CHECK_ICON_OPTIONS: dict[str, tuple[str, str]] = {
    "check": ("체크", "✓"),
    "circle_filled": ("동그라미", "●"),
    "circle_empty": ("빈 동그라미", "○"),
    "circle_double": ("이중 동그라미", "◎"),
    "triangle_filled": ("세모", "▲"),
    "triangle_empty": ("빈 세모", "△"),
    "square_filled": ("네모", "■"),
    "square_empty": ("빈 네모", "□"),
    "diamond": ("마름모", "◆"),
    "star": ("별", "★"),
    "heart": ("하트", "♥"),
    "arrow": ("화살표", "▶"),
}

FIXED_SECTION_KEYS = ("points", "features", "examples", "trust", "specs")

PROJECT_SCHEMA_VERSION = 1
PROJECTS_DIR = Path(__file__).resolve().parent.parent / "detail_projects"

DETAIL_PROJECT_UI_PREFIX = "detail_project_"

FIXED_SECTION_STATE_SUFFIXES = (
    "title",
    "text",
    "padding",
    "color",
    "title_color",
    "body_color_overridden",
    "title_color_overridden",
    "show_section",
    "show_image",
)

EXTRA_SECTION_STATE_SUFFIXES = (
    "title",
    "body",
    "layout",
    "padding",
    "show",
    "title_color",
    "body_color",
    "title_color_overridden",
    "body_color_overridden",
    "show_image",
)

DEFAULT_CONTENT = {
    "points": "가벼운 무게와 높은 내구성\n어떤 공간에도 어울리는 깔끔한 디자인\n초보자도 바로 사용할 수 있는 쉬운 구성",
    "features": "제품의 핵심 기능을 한눈에 이해할 수 있도록 설명해 주세요.\n특장점, 사용 방법, 차별화 포인트를 구체적으로 작성하면 좋습니다.",
    "examples": "집, 사무실, 매장 등 다양한 환경에서 활용할 수 있습니다.\n선물용, 업무용, 일상용 예시를 함께 보여 주세요.",
    "trust": "꼼꼼한 품질 검수\n안전한 포장 및 빠른 배송\n구매 후에도 안심할 수 있는 고객 지원",
    "specs": "크기: 120 x 80 x 35 mm\n무게: 240 g\n색상: 화이트 / 블랙\n구성품: 본품, 설명서, 패키지",
}

KOREAN_SANS_FALLBACK = "Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif"
KOREAN_SERIF_FALLBACK = "Batang, 'Noto Serif CJK KR', 'Nanum Myeongjo', serif"

DETAIL_FONT_PRESETS: list[tuple[str, str, str | None]] = [
    ("맑은 고딕 · 시스템", KOREAN_SANS_FALLBACK, None),
    (
        "Noto Sans KR",
        f"'Noto Sans KR', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap",
    ),
    (
        "나눔고딕",
        f"'Nanum Gothic', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap",
    ),
    (
        "나눔명조",
        f"'Nanum Myeongjo', {KOREAN_SERIF_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700;800&display=swap",
    ),
    (
        "Pretendard",
        f"'Pretendard', -apple-system, {KOREAN_SANS_FALLBACK}",
        "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css",
    ),
    (
        "IBM Plex Sans KR",
        f"'IBM Plex Sans KR', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap",
    ),
    (
        "Gowun Dodum",
        f"'Gowun Dodum', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Gowun+Dodum&display=swap",
    ),
    (
        "Gowun Batang",
        f"'Gowun Batang', {KOREAN_SERIF_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&display=swap",
    ),
    (
        "Hahmlet",
        f"'Hahmlet', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Hahmlet:wght@400;500;600;700;800&display=swap",
    ),
    (
        "Do Hyeon",
        f"'Do Hyeon', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Do+Hyeon&display=swap",
    ),
    (
        "Jua",
        f"'Jua', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Jua&display=swap",
    ),
    (
        "Black Han Sans",
        f"'Black Han Sans', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Black+Han+Sans&display=swap",
    ),
    (
        "Song Myung",
        f"'Song Myung', {KOREAN_SERIF_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Song+Myung&display=swap",
    ),
    (
        "Gaegu",
        f"'Gaegu', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Gaegu:wght@400;700&display=swap",
    ),
    (
        "Dongle",
        f"'Dongle', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Dongle:wght@400;700&display=swap",
    ),
    (
        "Gugi",
        f"'Gugi', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Gugi&display=swap",
    ),
    (
        "Poor Story",
        f"'Poor Story', {KOREAN_SANS_FALLBACK}",
        "https://fonts.googleapis.com/css2?family=Poor+Story&display=swap",
    ),
    ("고정폭 · 코드 느낌", f"Consolas, 'D2Coding', {KOREAN_SANS_FALLBACK}, monospace", None),
]

FONT_PRESET_LABELS = [label for label, _, _ in DETAIL_FONT_PRESETS]

DETAIL_PAGE_DEFAULTS: dict[str, object] = {
    "detail_title": "프리미엄 라이프스타일 제품",
    "detail_subtitle": (
        "제품의 첫인상을 만드는 핵심 문구를 입력하세요. "
        "고객이 얻을 수 있는 가치와 장점을 짧고 선명하게 보여줍니다."
    ),
    "detail_show_hero_image": True,
    "detail_hero_image_fit": "원본 사이즈",
    "detail_hero_image_height": 520,
    "detail_show_main_title": True,
    "detail_show_subtitle": True,
    "detail_page_bg_color": "#ffffff",
    "detail_hero_bg_color": "#ffffff",
    "detail_title_font": FONT_PRESET_LABELS[0],
    "detail_body_font": FONT_PRESET_LABELS[0],
    "detail_title_color": "#0f172a",
    "detail_subtitle_color": "#475569",
    "detail_hero_padding": 46,
    "detail_use_global_section_title_color": False,
    "detail_global_section_title_color": "#1e293b",
    "detail_use_global_body_color": False,
    "detail_global_body_color": "#1e293b",
    "detail_main_title_px": 48,
    "detail_subtitle_px": 20,
    "detail_section_title_px": 30,
    "detail_body_px": 18,
    "detail_checkpoint_sections": ["제품포인트", "신뢰성"],
    "detail_show_check_icon": True,
    "detail_check_icon_shape": "check",
    "detail_check_icon_color": "#2563eb",
    "detail_check_icon_size": 18,
    "detail_check_icon_y_offset": -8,
}


def resolve_font_preset(label: str) -> tuple[str, str | None]:
    return next((stack, href) for lab, stack, href in DETAIL_FONT_PRESETS if lab == label)


def unique_font_stylesheets(*hrefs: str | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for href in hrefs:
        if href and href not in seen:
            seen.add(href)
            out.append(href)
    return out


def get_valid_section_order_ids() -> list[str]:
    fixed_ids = [f"fixed:{key}" for key in FIXED_SECTION_KEYS]
    extra_ids = [f"extra:{sid}" for sid in st.session_state.get("extra_section_ids", [])]
    return fixed_ids + extra_ids


def sync_section_order() -> list[str]:
    st.session_state.setdefault("section_order_version", 0)
    valid_ids = get_valid_section_order_ids()
    previous = st.session_state.get("section_order", [])
    ordered = [item for item in previous if item in valid_ids]
    ordered.extend(item for item in valid_ids if item not in ordered)
    st.session_state.section_order = ordered
    return ordered


def apply_global_colors_to_all_sections(
    body_color: str | None = None,
    title_color: str | None = None,
) -> None:
    """공통 색상을 고정·추가 구역의 개별 색상 위젯 값에 반영합니다."""
    if body_color is not None:
        for key in FIXED_SECTION_KEYS:
            st.session_state[f"{key}_color"] = body_color
            st.session_state[f"{key}_body_color_overridden"] = False
        for sec_id in st.session_state.get("extra_section_ids", []):
            st.session_state[f"xt_{sec_id}_body_color"] = body_color
            st.session_state[f"xt_{sec_id}_body_color_overridden"] = False
    if title_color is not None:
        for key in FIXED_SECTION_KEYS:
            st.session_state[f"{key}_title_color"] = title_color
            st.session_state[f"{key}_title_color_overridden"] = False
        for sec_id in st.session_state.get("extra_section_ids", []):
            st.session_state[f"xt_{sec_id}_title_color"] = title_color
            st.session_state[f"xt_{sec_id}_title_color_overridden"] = False


def mark_fixed_section_color_override(section_key: str, color_kind: str) -> None:
    st.session_state[f"{section_key}_{color_kind}_color_overridden"] = True


def mark_extra_section_color_override(sec_id: str, color_kind: str) -> None:
    st.session_state[f"xt_{sec_id}_{color_kind}_color_overridden"] = True


def section_order_label(item_id: str, section_settings: dict[str, dict]) -> str:
    kind, value = item_id.split(":", 1)
    if kind == "fixed":
        title = section_settings[value].get("title") or SECTION_NAMES[value]
        return f"{title} · 기본 · {value}"

    title = st.session_state.get(f"xt_{value}_title") or "추가 구역"
    return f"{title} · 추가 {value[:4]}"


def safe_text(value: str) -> str:
    """Escape text and preserve line breaks for HTML preview."""
    return html.escape(value).replace("\n", "<br>")


def css_string_attr(value: str) -> str:
    return html.escape(json.dumps(value, ensure_ascii=False), quote=True)


def render_list_items(value: str) -> str:
    items = [line.strip() for line in value.splitlines() if line.strip()]
    if not items:
        return '<p class="empty-text">내용을 입력하면 여기에 표시됩니다.</p>'
    return "".join(f"<li>{html.escape(item)}</li>" for item in items)


def render_spec_rows(value: str) -> str:
    rows = []
    for line in value.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue

        if ":" in cleaned:
            key, val = cleaned.split(":", 1)
        elif "：" in cleaned:
            key, val = cleaned.split("：", 1)
        else:
            key, val = "항목", cleaned

        rows.append(
            "<tr>"
            f"<th>{html.escape(key.strip())}</th>"
            f"<td>{html.escape(val.strip())}</td>"
            "</tr>"
        )

    if not rows:
        return '<tr><td colspan="2" class="empty-text">규격 정보를 입력하면 여기에 표시됩니다.</td></tr>'
    return "".join(rows)


def ensure_session_default(key: str, value: object) -> None:
    if key not in st.session_state:
        st.session_state[key] = value


def init_detail_page_defaults() -> None:
    for key, value in DETAIL_PAGE_DEFAULTS.items():
        ensure_session_default(key, value)


def init_fixed_section_defaults(section_key: str, default_color: str) -> None:
    section_name = SECTION_NAMES[section_key]
    ensure_session_default(f"{section_key}_title", section_name)
    ensure_session_default(f"{section_key}_text", DEFAULT_CONTENT[section_key])
    ensure_session_default(f"{section_key}_padding", 34)
    ensure_session_default(f"{section_key}_color", default_color)
    ensure_session_default(f"{section_key}_title_color", default_color)
    ensure_session_default(f"{section_key}_body_color_overridden", False)
    ensure_session_default(f"{section_key}_title_color_overridden", False)
    ensure_session_default(f"{section_key}_show_section", True)
    ensure_session_default(f"{section_key}_show_image", False)


def uploaded_image_to_data_uri(uploaded_file) -> str | None:
    if uploaded_file is None:
        return None
    encoded = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
    return f"data:{uploaded_file.type};base64,{encoded}"


def serialize_uploaded_image(uploaded_file) -> dict:
    return {
        "name": uploaded_file.name,
        "type": uploaded_file.type or "application/octet-stream",
        "data_b64": base64.b64encode(uploaded_file.getvalue()).decode("ascii"),
    }


def resolve_image_data_uri(file_key: str) -> str | None:
    """업로드 위젯 또는 저장된 이미지(blob)에서 data URI를 만듭니다."""
    uploaded = st.session_state.get(file_key)
    if uploaded is not None:
        return uploaded_image_to_data_uri(uploaded)
    stored = st.session_state.get(f"{file_key}_stored")
    if not stored:
        return None
    mime = stored.get("type") or "application/octet-stream"
    data_b64 = stored.get("data_b64")
    if not data_b64:
        return None
    return f"data:{mime};base64,{data_b64}"


def image_file_keys_for_extra_ids(extra_ids: list[str]) -> list[str]:
    return [f"xt_{sec_id}_image" for sec_id in extra_ids]


def all_image_file_keys(extra_ids: list[str] | None = None) -> list[str]:
    keys = ["detail_hero_image", *[f"{section_key}_image" for section_key in FIXED_SECTION_KEYS]]
    if extra_ids is not None:
        keys.extend(image_file_keys_for_extra_ids(extra_ids))
    else:
        keys.extend(image_file_keys_for_extra_ids(st.session_state.get("extra_section_ids", [])))
    return keys


def slug_project_filename(name: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name.strip())
    safe = re.sub(r"\s+", " ", safe).strip(". ")
    return (safe or "project")[:80]


def is_detail_state_key(key: str) -> bool:
    if key.startswith(DETAIL_PROJECT_UI_PREFIX):
        return False
    if key in {"detail_page_png", "detail_page_png_digest"}:
        return True
    if key in {"extra_section_ids", "section_order", "section_order_version"}:
        return True
    if key.startswith("detail_"):
        return True
    if key.startswith("xt_"):
        return True
    for section_key in FIXED_SECTION_KEYS:
        if key.startswith(f"{section_key}_"):
            return True
    if key.endswith("_stored"):
        return True
    return False


def purge_detail_state() -> None:
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and is_detail_state_key(key):
            del st.session_state[key]


def collect_image_blob(file_key: str) -> dict | None:
    uploaded = st.session_state.get(file_key)
    if uploaded is not None:
        return serialize_uploaded_image(uploaded)
    stored = st.session_state.get(f"{file_key}_stored")
    return stored if isinstance(stored, dict) and stored.get("data_b64") else None


def collect_project_state() -> dict:
    extra_ids = list(st.session_state.get("extra_section_ids", []))
    state: dict = {}

    for key in (
        "detail_title",
        "detail_subtitle",
        "detail_show_hero_image",
        "detail_hero_image_fit",
        "detail_hero_image_height",
        "detail_show_main_title",
        "detail_show_subtitle",
        "detail_page_bg_color",
        "detail_hero_bg_color",
        "detail_title_font",
        "detail_body_font",
        "detail_title_color",
        "detail_subtitle_color",
        "detail_hero_padding",
        "detail_use_global_section_title_color",
        "detail_global_section_title_color",
        "detail_use_global_body_color",
        "detail_global_body_color",
        "detail_main_title_px",
        "detail_subtitle_px",
        "detail_section_title_px",
        "detail_body_px",
        "detail_checkpoint_sections",
        "detail_show_check_icon",
        "detail_check_icon_shape",
        "detail_check_icon_color",
        "detail_check_icon_size",
        "detail_check_icon_y_offset",
        "extra_section_ids",
        "section_order",
        "section_order_version",
    ):
        if key in st.session_state:
            state[key] = st.session_state[key]

    for section_key in FIXED_SECTION_KEYS:
        for suffix in FIXED_SECTION_STATE_SUFFIXES:
            widget_key = f"{section_key}_{suffix}"
            if widget_key in st.session_state:
                state[widget_key] = st.session_state[widget_key]

    for sec_id in extra_ids:
        for suffix in EXTRA_SECTION_STATE_SUFFIXES:
            widget_key = f"xt_{sec_id}_{suffix}"
            if widget_key in st.session_state:
                state[widget_key] = st.session_state[widget_key]

    for file_key in all_image_file_keys(extra_ids):
        blob = collect_image_blob(file_key)
        if blob:
            state[f"{file_key}_stored"] = blob

    return state


def apply_project_state(state: dict) -> None:
    purge_detail_state()
    image_keys = all_image_file_keys(state.get("extra_section_ids", []))

    for key, value in state.items():
        if key.endswith("_stored"):
            st.session_state[key] = value
            continue
        if key in image_keys:
            continue
        st.session_state[key] = value

    for file_key in image_keys:
        st.session_state.pop(file_key, None)

    st.session_state.setdefault("extra_section_ids", [])
    st.session_state.setdefault("section_order", [])
    st.session_state["section_order_version"] = int(
        st.session_state.get("section_order_version", 0)
    ) + 1


def ensure_projects_dir() -> Path:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECTS_DIR


def list_detail_projects() -> list[str]:
    ensure_projects_dir()
    entries: list[tuple[float, str]] = []
    for path in PROJECTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            name = str(data.get("name") or path.stem)
        except (json.JSONDecodeError, OSError):
            name = path.stem
        entries.append((path.stat().st_mtime, name))
    entries.sort(key=lambda item: item[0], reverse=True)
    seen: set[str] = set()
    ordered: list[str] = []
    for _, name in entries:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def find_project_path(name: str) -> Path | None:
    ensure_projects_dir()
    slug = slug_project_filename(name)
    direct = PROJECTS_DIR / f"{slug}.json"
    if direct.exists():
        return direct
    for path in PROJECTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("name") == name:
            return path
    return None


def save_detail_project(name: str) -> Path:
    ensure_projects_dir()
    slug = slug_project_filename(name)
    payload = {
        "version": PROJECT_SCHEMA_VERSION,
        "name": name.strip(),
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "state": collect_project_state(),
    }
    path = PROJECTS_DIR / f"{slug}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_detail_project(name: str) -> None:
    path = find_project_path(name)
    if path is None:
        raise FileNotFoundError(f"프로젝트를 찾을 수 없습니다: {name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    state = data.get("state")
    if not isinstance(state, dict):
        raise ValueError("프로젝트 파일 형식이 올바르지 않습니다.")
    apply_project_state(state)
    display_name = str(data.get("name") or name)
    queue_project_ui_update(name=display_name)
    if find_project_path(display_name) is not None:
        queue_project_ui_update(pick=display_name)


def delete_detail_project(name: str) -> None:
    path = find_project_path(name)
    if path is None:
        raise FileNotFoundError(f"프로젝트를 찾을 수 없습니다: {name}")
    path.unlink()


def queue_project_ui_update(*, pick: str | None = None, name: str | None = None) -> None:
    """위젯 생성 전 다음 rerun에서 반영할 프로젝트 UI 값을 예약합니다."""
    if pick is not None:
        st.session_state["_pending_detail_project_pick"] = pick
    if name is not None:
        st.session_state["_pending_detail_project_name_input"] = name


def apply_pending_project_ui_updates(project_options: list[str]) -> None:
    """예약된 프로젝트 선택/이름을 selectbox·text_input 생성 전에 반영합니다."""
    if "_pending_detail_project_pick" in st.session_state:
        pick = st.session_state.pop("_pending_detail_project_pick")
        st.session_state.detail_project_pick = pick if pick in project_options else ""
    if "_pending_detail_project_name_input" in st.session_state:
        st.session_state.detail_project_name_input = st.session_state.pop(
            "_pending_detail_project_name_input"
        )
    if st.session_state.get("detail_project_pick") not in project_options:
        st.session_state.detail_project_pick = ""


def section_controls(section_key: str, default_color: str) -> dict:
    init_fixed_section_defaults(section_key, default_color)
    section_name = SECTION_NAMES[section_key]
    with st.expander(section_name, expanded=section_key in {"points", "features"}):
        title = st.text_input(
            f"{section_name} 제목",
            key=f"{section_key}_title",
        )
        text = st.text_area(
            f"{section_name} 내용",
            height=150 if section_key != "specs" else 130,
            key=f"{section_key}_text",
        )
        padding = st.slider(
            f"{section_name} 패딩",
            min_value=16,
            max_value=96,
            step=2,
            key=f"{section_key}_padding",
        )
        title_color_col, body_color_col = st.columns(2)
        with title_color_col:
            title_color = st.color_picker(
                f"{section_name} 제목 색상",
                key=f"{section_key}_title_color",
                on_change=mark_fixed_section_color_override,
                args=(section_key, "title"),
            )
        with body_color_col:
            color = st.color_picker(
                f"{section_name} 본문 색상",
                key=f"{section_key}_color",
                on_change=mark_fixed_section_color_override,
                args=(section_key, "body"),
            )
        show_section = st.toggle(
            f"{section_name} 구역 표시",
            key=f"{section_key}_show_section",
            help="끄면 이 구역 전체(제목·본문)가 미리보기와 다운로드에서 제외됩니다.",
        )
        show_image = st.toggle(
            f"{section_name} 이미지 표시",
            key=f"{section_key}_show_image",
        )
        image_file = st.file_uploader(
            f"{section_name} 이미지",
            type=["jpg", "jpeg", "png", "webp"],
            key=f"{section_key}_image",
            disabled=not show_image,
        )
        image_data_uri = resolve_image_data_uri(f"{section_key}_image") if show_image else None

    return {
        "title": title,
        "text": text,
        "padding": padding,
        "color": color,
        "title_color": title_color,
        "body_color_overridden": st.session_state.get(
            f"{section_key}_body_color_overridden", False
        ),
        "title_color_overridden": st.session_state.get(
            f"{section_key}_title_color_overridden", False
        ),
        "show_section": show_section,
        "show_image": show_image,
        "image_data_uri": image_data_uri,
    }


def render_section(
    section_key: str,
    settings: dict,
    use_checkpoints: bool = False,
    horizontal_padding: int | None = None,
    body_color_override: str | None = None,
    title_color_override: str | None = None,
) -> str:
    if not settings.get("show_section", True):
        return ""

    title = settings.get("title") or SECTION_NAMES[section_key]
    content_class = "spec-table" if section_key == "specs" else "section-body"
    body_color = (
        settings["color"]
        if settings.get("body_color_overridden")
        else body_color_override or settings["color"]
    )
    title_color = (
        settings["title_color"]
        if settings.get("title_color_overridden")
        else title_color_override or settings["title_color"]
    )

    if use_checkpoints and section_key != "specs":
        content = f"<ul>{render_list_items(settings['text'])}</ul>"
    elif section_key == "specs":
        content = f"<table>{render_spec_rows(settings['text'])}</table>"
    else:
        content = f"<p>{safe_text(settings['text'])}</p>"

    section_image = ""
    if settings.get("show_image") and settings.get("image_data_uri"):
        section_image = (
            '<div class="section-image-wrap">'
            f'<img src="{settings["image_data_uri"]}" alt="{html.escape(title)} 이미지">'
            "</div>"
        )

    title_block = (
        f'<div class="section-kicker">{html.escape(title)}</div>'
        f'<h2 style="color:{title_color};">{html.escape(title)}</h2>'
    )

    vertical_padding = int(settings["padding"])
    side_padding = horizontal_padding if horizontal_padding is not None else vertical_padding

    return (
        f'<section class="detail-section" style="padding:{vertical_padding}px {side_padding}px;'
        f'color:{body_color};">'
        f"{title_block}"
        f'<div class="{content_class}">{content}</div>'
        f"{section_image}"
        f"</section>"
    )


def render_plain_list(value: str) -> str:
    """체크 아이콘 없는 단순 리스트 마크업(li만 생성)."""
    items = [line.strip() for line in value.splitlines() if line.strip()]
    if not items:
        return ""
    return "".join(f"<li>{html.escape(item)}</li>" for item in items)


def render_plain_ul(value: str) -> str:
    inner = render_plain_list(value)
    if not inner:
        return '<p class="empty-text">내용을 입력하면 여기에 표시됩니다.</p>'
    return f'<ul class="detail-plain-ul">{inner}</ul>'


def render_extra_section_html(
    sec_id: str,
    checkpoint_active: bool,
    horizontal_padding: int | None = None,
    body_color_override: str | None = None,
    title_color_override: str | None = None,
) -> str:
    """사이드바에서 설정된 추가 구역을 HTML 조각으로 만듭니다."""
    if not st.session_state.get(f"xt_{sec_id}_show", True):
        return ""

    title = (st.session_state.get(f"xt_{sec_id}_title") or "추가 구역").strip()
    body = st.session_state.get(f"xt_{sec_id}_body") or ""
    layout = st.session_state.get(f"xt_{sec_id}_layout", "문단")
    padding = int(st.session_state.get(f"xt_{sec_id}_padding", 34))
    side_padding = horizontal_padding if horizontal_padding is not None else padding
    title_color = (
        st.session_state.get(f"xt_{sec_id}_title_color", "#1e293b")
        if st.session_state.get(f"xt_{sec_id}_title_color_overridden", False)
        else title_color_override or st.session_state.get(f"xt_{sec_id}_title_color", "#1e293b")
    )
    body_color = (
        st.session_state.get(f"xt_{sec_id}_body_color", "#1e293b")
        if st.session_state.get(f"xt_{sec_id}_body_color_overridden", False)
        else body_color_override or st.session_state.get(f"xt_{sec_id}_body_color", "#1e293b")
    )
    show_image = st.session_state.get(f"xt_{sec_id}_show_image", False)
    image_data_uri = resolve_image_data_uri(f"xt_{sec_id}_image") if show_image else None

    content_class = "section-body"
    if layout == "문단":
        content = f"<p>{safe_text(body)}</p>"
    elif layout == "표(항목:값)":
        content_class = "spec-table"
        content = f"<table>{render_spec_rows(body)}</table>"
    elif layout == "줄별 리스트" and checkpoint_active:
        content = f'<ul>{render_list_items(body)}</ul>'
    elif layout == "줄별 리스트":
        content = render_plain_ul(body)
    else:
        content = f"<p>{safe_text(body)}</p>"

    title_block = (
        f'<div class="section-kicker">{html.escape(title)}</div>'
        f'<h2 style="color:{html.escape(title_color, quote=False)};">{html.escape(title)}</h2>'
    )
    section_image = ""
    if image_data_uri:
        section_image = (
            '<div class="section-image-wrap">'
            f'<img src="{image_data_uri}" alt="{html.escape(title)} 이미지">'
            "</div>"
        )

    return (
        f'<section class="detail-section detail-section-dynamic" '
        f'style="padding:{padding}px {side_padding}px;color:{html.escape(body_color, quote=False)};">'
        f"{title_block}"
        f'<div class="{content_class}">{content}</div>'
        f"{section_image}"
        f"</section>"
    )


def markdown_html(html_fragment: str) -> None:
    """Streamlit Markdown은 들여쓴 줄을 코드 블록으로 처리하므로 dedent 후 렌더링합니다."""
    st.markdown(dedent(html_fragment).strip(), unsafe_allow_html=True)


DOWNLOAD_CSS = """
html,
body {
    margin: 0;
    padding: 0;
    background: #ffffff;
    font-family: var(--detail-font, Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif);
}
#detail-preview-root {
    box-sizing: border-box;
    -webkit-font-smoothing: antialiased;
    font-family: var(--detail-font, Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif);
}
#detail-preview-root *,
#detail-preview-root *::before,
#detail-preview-root *::after {
    box-sizing: inherit;
}
#detail-preview-root.preview-shell {
    width: 100%;
    min-height: 100vh;
    padding: 0;
    border-radius: 0;
    box-shadow: none;
}
#detail-preview-root .detail-page {
    max-width: 960px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 0;
    background: #ffffff;
    font-family: inherit;
}
#detail-preview-root .hero-card,
#detail-preview-root .detail-section {
    width: 100%;
    border: 0;
    border-bottom: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 0;
    box-shadow: none;
    overflow: hidden;
}
#detail-preview-root .detail-section:last-child {
    border-bottom: 0;
}
#detail-preview-root .hero-eyebrow,
#detail-preview-root .section-kicker {
    display: none;
    margin-bottom: 14px;
    padding: 6px 12px;
    border-radius: 999px;
    background: rgba(37, 99, 235, 0.1);
    color: #2563eb;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.05em;
}
#detail-preview-root .hero-title {
    margin: 0;
    font-size: var(--fs-main-title, 48px);
    line-height: 1.08;
    letter-spacing: -0.06em;
    font-weight: 900;
    font-family: var(--title-font, var(--detail-font, Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif));
}
#detail-preview-root .hero-subtitle {
    margin: 18px 0 30px;
    max-width: 680px;
    font-size: var(--fs-subtitle, 20px);
    line-height: 1.7;
    font-family: var(--title-font, var(--detail-font, Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif));
}
#detail-preview-root .hero-image-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    height: var(--hero-image-height, 520px);
    border-radius: 6px;
    background:
        radial-gradient(circle at 30% 20%, rgba(59, 130, 246, 0.14), transparent 32%),
        linear-gradient(135deg, #f8fafc, #e2e8f0);
    border: 1px dashed rgba(100, 116, 139, 0.38);
    overflow: hidden;
}
#detail-preview-root .hero-image-wrap img {
    width: 100%;
    height: 100%;
    object-fit: var(--hero-image-fit, cover);
    display: block;
}
#detail-preview-root .hero-image-wrap.original-size {
    height: auto;
    min-height: 0;
    padding: 0;
}
#detail-preview-root .hero-image-wrap.original-size img {
    width: auto;
    height: auto;
    max-width: 100%;
    object-fit: contain;
}
#detail-preview-root .image-placeholder {
    padding: 38px;
    text-align: center;
    color: #64748b;
    font-weight: 700;
}
#detail-preview-root .section-image-wrap {
    display: flex;
    justify-content: center;
    margin-top: 28px;
}
#detail-preview-root .section-image-wrap img {
    display: block;
    max-width: 100%;
    height: auto;
}
#detail-preview-root .detail-section h2 {
    margin: 0 0 18px;
    font-size: var(--fs-section-title, 30px);
    line-height: 1.25;
    letter-spacing: -0.035em;
    font-family: var(--title-font, var(--detail-font, Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif));
}
#detail-preview-root .section-body,
#detail-preview-root .spec-table {
    font-size: var(--fs-body, 18px);
    line-height: 1.85;
}
#detail-preview-root .section-body p {
    margin: 0;
}
#detail-preview-root .section-body ul {
    display: grid;
    gap: 13px;
    margin: 0;
    padding: 0;
    list-style: none;
}
#detail-preview-root .section-body li {
    position: relative;
    padding: 16px 18px 16px 48px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.58);
    border: 1px solid rgba(15, 23, 42, 0.06);
    font-weight: 700;
}
#detail-preview-root .section-body li::before {
    content: var(--check-icon-content, "✓");
    position: absolute;
    left: 18px;
    top: calc(16px + (var(--fs-body, 18px) * 1.85 / 2) + var(--check-icon-y-offset, -8px));
    transform: translateY(-50%);
    width: var(--check-icon-size, 18px);
    height: var(--check-icon-size, 18px);
    display: grid;
    place-items: center;
    color: var(--check-icon-color, #2563eb);
    font-size: var(--check-icon-size, 18px);
    font-weight: 900;
}
#detail-preview-root.hide-check-icon .section-body li {
    padding-left: 18px;
}
#detail-preview-root.hide-check-icon .section-body li::before {
    display: none;
}
#detail-preview-root ul.detail-plain-ul {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin: 0;
    padding: 0 0 0 1.35rem;
    list-style: disc;
}
#detail-preview-root ul.detail-plain-ul li {
    position: static;
    padding: 4px 0;
    margin: 0;
    border-radius: 0;
    background: transparent;
    border: 0;
    font-weight: 600;
}
#detail-preview-root ul.detail-plain-ul li::before {
    display: none !important;
    content: none !important;
}
#detail-preview-root .spec-table table {
    width: 100%;
    border-collapse: collapse;
    overflow: hidden;
    border-radius: 0;
    background: rgba(255, 255, 255, 0.72);
}
#detail-preview-root .spec-table th,
#detail-preview-root .spec-table td {
    padding: 17px 18px;
    border-bottom: 1px solid rgba(15, 23, 42, 0.08);
    text-align: left;
    vertical-align: top;
}
#detail-preview-root .spec-table th {
    width: 32%;
    color: #334155;
    background: rgba(248, 250, 252, 0.88);
    font-weight: 900;
    font-family: var(--title-font, var(--detail-font, Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif));
}
#detail-preview-root .empty-text {
    color: #94a3b8;
    font-style: italic;
}
"""


def build_standalone_html(
    page_title: str,
    preview_body: str,
    font_stack: str,
    font_stylesheet_href: str | None,
    title_font_stack: str,
    title_font_stylesheet_href: str | None,
) -> str:
    """CSS와 미리보기 본문을 포함한 독립 실행형 HTML 문서를 만듭니다."""
    link_lines: list[str] = []
    hrefs = unique_font_stylesheets(font_stylesheet_href, title_font_stylesheet_href)
    if any("fonts.googleapis.com" in h for h in hrefs):
        link_lines.extend(
            [
                '<link rel="preconnect" href="https://fonts.googleapis.com">',
                '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
            ]
        )
    for href in hrefs:
        link_lines.append(f'<link rel="stylesheet" href="{html.escape(href)}">')
    link_block = "\n            ".join(link_lines)
    escaped_body = html.escape(font_stack, quote=False)
    escaped_title = html.escape(title_font_stack, quote=False)
    return dedent(
        f"""\
        <!doctype html>
        <html lang="ko" style="--detail-font: {escaped_body}; --title-font: {escaped_title}">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{html.escape(page_title) or "상세페이지"}</title>
            {link_block}
            <style>{DOWNLOAD_CSS}</style>
        </head>
        <body>
        {preview_body}
        </body>
        </html>
        """
    ).strip()


_CHROMIUM_READY = False


def _chromium_launch_probe() -> bool:
    """설치된 Chromium으로 짧은 실행 테스트를 합니다."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


def _mark_chromium_ready() -> None:
    global _CHROMIUM_READY
    _CHROMIUM_READY = True
    try:
        st.session_state["_playwright_chromium_ready"] = True
    except Exception:
        pass


def ensure_playwright_chromium_installed() -> None:
    """배포 환경(Streamlit Cloud 등)에서 Chromium 바이너리가 없으면 자동 설치합니다."""
    global _CHROMIUM_READY
    if _CHROMIUM_READY or st.session_state.get("_playwright_chromium_ready"):
        _CHROMIUM_READY = True
        return
    if _chromium_launch_probe():
        _mark_chromium_ready()
        return

    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            "Chromium 자동 설치에 실패했습니다. "
            f"서버에서 `python -m playwright install chromium` 실행이 필요합니다. {detail}"
        )
    if not _chromium_launch_probe():
        raise RuntimeError(
            "Chromium 설치 후에도 브라우저를 시작할 수 없습니다. "
            "배포 환경에 `packages.txt`가 포함되어 있는지 확인해 주세요."
        )
    _mark_chromium_ready()


def _capture_full_page_png_impl(html_document: str, viewport_width: int, scale_factor: int) -> bytes:
    """Playwright 동기 API로 HTML을 PNG로 캡처합니다. (asyncio 루프 밖에서 호출)"""
    from playwright.sync_api import sync_playwright

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(html_document)
            temp_path = Path(temp_file.name)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(
                viewport={"width": viewport_width, "height": 900},
                device_scale_factor=scale_factor,
            )
            page.goto(temp_path.as_uri(), wait_until="load", timeout=60_000)
            png_bytes = page.screenshot(type="png", full_page=True)
            browser.close()
            return png_bytes
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def capture_full_page_png(html_document: str, viewport_width: int, scale_factor: int) -> bytes:
    """임시 HTML 파일을 Playwright로 열고 전체 페이지 PNG를 캡처합니다."""
    try:
        import playwright  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "playwright가 설치되어 있지 않습니다. `pip install playwright` 후 "
            "`python -m playwright install chromium`을 실행하세요."
        ) from exc

    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def _run_capture() -> bytes:
        try:
            return _capture_full_page_png_impl(html_document, viewport_width, scale_factor)
        except Exception as exc:
            raise RuntimeError(
                f"PNG 생성에 실패했습니다. ({type(exc).__name__}: {exc}) "
                "Chromium이 없다면 `python -m playwright install chromium`을 실행하세요."
            ) from exc

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _run_capture()

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_run_capture).result(timeout=900)


if __name__ == "__main__":
    st.set_page_config(
        page_title="상세페이지 생성기",
        page_icon="🧾",
        layout="wide",
    )

markdown_html(
    """
    <style>
    #detail-preview-root {
        box-sizing: border-box;
        -webkit-font-smoothing: antialiased;
        font-family: var(--detail-font, Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif);
    }
    #detail-preview-root *,
    #detail-preview-root *::before,
    #detail-preview-root *::after {
        box-sizing: inherit;
    }
    .block-container {
        padding-top: 2rem;
        max-width: 1440px;
    }
    [data-testid="stSidebar"] {
        min-width: 360px;
    }
    #detail-preview-root.preview-shell {
        width: 100%;
        min-height: 70vh;
        padding: 0;
        border-radius: 0;
        box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.06);
    }
    #detail-preview-root .detail-page {
        max-width: 960px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        gap: 0;
        background: #ffffff;
        font-family: inherit;
    }
    #detail-preview-root .hero-card,
    #detail-preview-root .detail-section {
        width: 100%;
        border: 0;
        border-bottom: 1px solid rgba(15, 23, 42, 0.08);
        border-radius: 0;
        box-shadow: none;
        overflow: hidden;
    }
    #detail-preview-root .detail-section:last-child {
        border-bottom: 0;
    }
    #detail-preview-root .hero-card {
        padding: 46px;
    }
    #detail-preview-root .hero-eyebrow,
    #detail-preview-root .section-kicker {
        display: none;
        margin-bottom: 14px;
        padding: 6px 12px;
        border-radius: 999px;
        background: rgba(37, 99, 235, 0.1);
        color: #2563eb;
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 0.05em;
    }
    #detail-preview-root .hero-title {
        margin: 0;
        font-size: var(--fs-main-title, 48px);
        line-height: 1.08;
        letter-spacing: -0.06em;
        font-weight: 900;
        font-family: var(--title-font, var(--detail-font, Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif));
    }
    #detail-preview-root .hero-subtitle {
        margin: 18px 0 30px;
        max-width: 680px;
        font-size: var(--fs-subtitle, 20px);
        line-height: 1.7;
        color: rgba(15, 23, 42, 0.72);
        font-family: var(--title-font, var(--detail-font, Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif));
    }
    #detail-preview-root .hero-image-wrap {
        display: flex;
        align-items: center;
        justify-content: center;
        height: var(--hero-image-height, 520px);
        border-radius: 6px;
        background:
            radial-gradient(circle at 30% 20%, rgba(59, 130, 246, 0.14), transparent 32%),
            linear-gradient(135deg, #f8fafc, #e2e8f0);
        border: 1px dashed rgba(100, 116, 139, 0.38);
        overflow: hidden;
    }
    #detail-preview-root .hero-image-wrap img {
        width: 100%;
        height: 100%;
        object-fit: var(--hero-image-fit, cover);
        display: block;
    }
    #detail-preview-root .hero-image-wrap.original-size {
        height: auto;
        min-height: 0;
        padding: 0;
    }
    #detail-preview-root .hero-image-wrap.original-size img {
        width: auto;
        height: auto;
        max-width: 100%;
        object-fit: contain;
    }
    #detail-preview-root .image-placeholder {
        padding: 38px;
        text-align: center;
        color: #64748b;
        font-weight: 700;
    }
    #detail-preview-root .section-image-wrap {
        display: flex;
        justify-content: center;
        margin-top: 28px;
    }
    #detail-preview-root .section-image-wrap img {
        display: block;
        max-width: 100%;
        height: auto;
    }
    #detail-preview-root .detail-section h2 {
        margin: 0 0 18px;
        font-size: var(--fs-section-title, 30px);
        line-height: 1.25;
        letter-spacing: -0.035em;
        font-family: var(--title-font, var(--detail-font, Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif));
    }
    #detail-preview-root .section-body,
    #detail-preview-root .spec-table {
        font-size: var(--fs-body, 18px);
        line-height: 1.85;
    }
    #detail-preview-root .section-body p {
        margin: 0;
    }
    #detail-preview-root .section-body ul {
        display: grid;
        gap: 13px;
        margin: 0;
        padding: 0;
        list-style: none;
    }
    #detail-preview-root .section-body li {
        position: relative;
        padding: 16px 18px 16px 48px;
        border-radius: 6px;
        background: rgba(255, 255, 255, 0.58);
        border: 1px solid rgba(15, 23, 42, 0.06);
        font-weight: 700;
    }
    #detail-preview-root .section-body li::before {
        content: var(--check-icon-content, "✓");
        position: absolute;
        left: 18px;
        top: calc(16px + (var(--fs-body, 18px) * 1.85 / 2) + var(--check-icon-y-offset, -8px));
        transform: translateY(-50%);
        width: var(--check-icon-size, 18px);
        height: var(--check-icon-size, 18px);
        display: grid;
        place-items: center;
        color: var(--check-icon-color, #2563eb);
        font-size: var(--check-icon-size, 18px);
        font-weight: 900;
    }
    #detail-preview-root.hide-check-icon .section-body li {
        padding-left: 18px;
    }
    #detail-preview-root.hide-check-icon .section-body li::before {
        display: none;
    }
    #detail-preview-root ul.detail-plain-ul {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin: 0;
        padding: 0 0 0 1.35rem;
        list-style: disc;
    }
    #detail-preview-root ul.detail-plain-ul li {
        position: static;
        padding: 4px 0;
        margin: 0;
        border-radius: 0;
        background: transparent;
        border: 0;
        font-weight: 600;
    }
    #detail-preview-root ul.detail-plain-ul li::before {
        display: none !important;
        content: none !important;
    }
    #detail-preview-root .spec-table table {
        width: 100%;
        border-collapse: collapse;
        overflow: hidden;
        border-radius: 0;
        background: rgba(255, 255, 255, 0.72);
    }
    #detail-preview-root .spec-table th,
    #detail-preview-root .spec-table td {
        padding: 17px 18px;
        border-bottom: 1px solid rgba(15, 23, 42, 0.08);
        text-align: left;
        vertical-align: top;
    }
    #detail-preview-root .spec-table th {
        width: 32%;
        color: #334155;
        background: rgba(248, 250, 252, 0.88);
        font-weight: 900;
        font-family: var(--title-font, var(--detail-font, Malgun Gothic, Apple SD Gothic Neo, 'Noto Sans CJK KR', 'Nanum Gothic', sans-serif));
    }
    #detail-preview-root .empty-text {
        color: #94a3b8;
        font-style: italic;
    }
    @media (max-width: 900px) {
        #detail-preview-root.preview-shell {
            padding: 18px;
        }
        #detail-preview-root .hero-card {
            padding: 28px;
        }
    }
    </style>
    """
)

with st.sidebar:
    st.markdown("[🖼️ 이미지 썸네일 변환기로 돌아가기](/)")
    st.divider()

    st.header("상세페이지 정보 입력")
    st.caption("입력값은 우측 미리보기에 바로 반영됩니다.")

    st.subheader("프로젝트")
    saved_projects = list_detail_projects()
    project_options = [""] + saved_projects
    apply_pending_project_ui_updates(project_options)
    picked_project = st.selectbox(
        "저장된 프로젝트",
        options=project_options,
        format_func=lambda value: "— 선택 —" if not value else value,
        key="detail_project_pick",
    )
    project_name_input = st.text_input(
        "프로젝트 이름",
        placeholder="저장할 이름을 입력하세요",
        key="detail_project_name_input",
    )
    proj_load, proj_save, proj_delete = st.columns(3)
    with proj_load:
        load_clicked = st.button("불러오기", use_container_width=True, disabled=not picked_project)
    with proj_save:
        save_clicked = st.button("저장", use_container_width=True)
    with proj_delete:
        delete_clicked = st.button("삭제", use_container_width=True, disabled=not picked_project)

    if load_clicked and picked_project:
        try:
            load_detail_project(picked_project)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            st.error(str(exc))
        else:
            st.rerun()

    if save_clicked:
        save_name = (project_name_input or picked_project or "").strip()
        if not save_name:
            st.warning("프로젝트 이름을 입력하거나 목록에서 선택하세요.")
        else:
            save_detail_project(save_name)
            queue_project_ui_update(pick=save_name, name=save_name)
            st.success(f"저장했습니다: {save_name}")
            st.rerun()

    if delete_clicked and picked_project:
        try:
            delete_detail_project(picked_project)
        except FileNotFoundError as exc:
            st.error(str(exc))
        else:
            queue_project_ui_update(pick="", name="")
            st.success(f"삭제했습니다: {picked_project}")
            st.rerun()

    st.divider()
    init_detail_page_defaults()
    st.subheader("기본 정보")
    title = st.text_input("타이틀", key="detail_title")
    subtitle = st.text_area(
        "서브타이틀",
        height=110,
        key="detail_subtitle",
    )
    image_file = st.file_uploader(
        "대표상품이미지",
        type=["jpg", "jpeg", "png", "webp"],
        key="detail_hero_image",
    )
    show_hero_image = st.toggle("대표상품이미지 표시", key="detail_show_hero_image")
    hero_image_fit_label = st.selectbox(
        "대표이미지 맞춤",
        options=["원본 사이즈", "영역 꽉 채우기", "전체 보이기", "비율 무시하고 채우기"],
        disabled=not show_hero_image,
        help="원본 사이즈는 업로드 이미지 크기를 유지하되, 상세페이지 폭보다 크면 폭에 맞춰 줄입니다.",
        key="detail_hero_image_fit",
    )
    hero_image_height = st.slider(
        "대표이미지 영역 높이 (px)",
        min_value=260,
        max_value=900,
        step=20,
        disabled=not show_hero_image or hero_image_fit_label == "원본 사이즈",
        key="detail_hero_image_height",
    )
    show_main_title = st.toggle("메인 타이틀 표시", key="detail_show_main_title")
    show_subtitle = st.toggle("서브타이틀 표시", key="detail_show_subtitle")

    st.divider()
    st.subheader("전체 스타일")
    page_bg_col, hero_bg_col = st.columns(2)
    with page_bg_col:
        page_bg_color = st.color_picker("전체 배경색", key="detail_page_bg_color")
    with hero_bg_col:
        hero_bg_color = st.color_picker("상세페이지 배경색", key="detail_hero_bg_color")
    title_font_choice = st.selectbox(
        "타이틀 글꼴",
        options=FONT_PRESET_LABELS,
        help="메인 타이틀, 서브타이틀, 각 섹션 제목(h2)에 적용됩니다.",
        key="detail_title_font",
    )
    font_choice = st.selectbox(
        "본문 글꼴",
        options=FONT_PRESET_LABELS,
        key="detail_body_font",
    )
    title_color_col, subtitle_color_col = st.columns(2)
    with title_color_col:
        title_color = st.color_picker("타이틀 글씨 색상", key="detail_title_color")
    with subtitle_color_col:
        subtitle_color = st.color_picker("서브타이틀 글씨 색상", key="detail_subtitle_color")
    hero_padding = st.slider(
        "대표 카드 패딩",
        min_value=24,
        max_value=96,
        step=2,
        key="detail_hero_padding",
    )
    st.subheader("공통 색상")
    st.caption("스위치를 켜면 미리보기와 다운로드에 공통 색상이 바로 적용됩니다.")
    use_global_section_title_color = st.toggle(
        "전체 구역 제목 글씨 색상 적용",
        key="detail_use_global_section_title_color",
    )
    global_section_title_color = st.color_picker(
        "전체 구역 제목 글씨 색상",
        key="detail_global_section_title_color",
        disabled=not use_global_section_title_color,
    )
    if st.button("모든 구역 제목색에 적용", key="btn_apply_all_title_colors", use_container_width=True):
        apply_global_colors_to_all_sections(title_color=global_section_title_color)
        st.rerun()
    use_global_body_color = st.toggle(
        "전체 본문 글씨 색상 적용",
        key="detail_use_global_body_color",
    )
    global_body_color = st.color_picker(
        "전체 본문 글씨 색상",
        key="detail_global_body_color",
        disabled=not use_global_body_color,
    )
    if st.button("모든 구역 본문색에 적용", key="btn_apply_all_body_colors", use_container_width=True):
        apply_global_colors_to_all_sections(body_color=global_body_color)
        st.rerun()
    st.subheader("글자 크기")
    main_title_px = st.slider(
        "메인 타이틀 글씨 크기 (px)",
        min_value=24,
        max_value=80,
        step=2,
        key="detail_main_title_px",
    )
    subtitle_px = st.slider(
        "서브타이틀 글씨 크기 (px)",
        min_value=12,
        max_value=36,
        step=1,
        key="detail_subtitle_px",
    )
    section_title_px = st.slider(
        "구역 제목 글씨 크기 (px)",
        min_value=16,
        max_value=52,
        step=1,
        key="detail_section_title_px",
    )
    body_px = st.slider(
        "구역 본문 글씨 크기 (px)",
        min_value=12,
        max_value=30,
        step=1,
        key="detail_body_px",
    )
    checkpoint_section_labels = st.multiselect(
        "아이콘 적용 구역",
        options=list(CHECKPOINT_SECTION_OPTIONS.keys()),
        help="선택한 구역은 줄 단위 체크 리스트로 표시됩니다.",
        key="detail_checkpoint_sections",
    )
    show_check_icon = st.toggle("아이콘 표시", key="detail_show_check_icon")
    check_icon_shape = st.selectbox(
        "아이콘 모양",
        options=list(CHECK_ICON_OPTIONS.keys()),
        format_func=lambda key: f"{CHECK_ICON_OPTIONS[key][1]} {CHECK_ICON_OPTIONS[key][0]}",
        disabled=not show_check_icon,
        key="detail_check_icon_shape",
    )
    check_icon_color = st.color_picker(
        "아이콘 색상",
        disabled=not show_check_icon,
        key="detail_check_icon_color",
    )
    check_icon_size = st.slider(
        "아이콘 크기 (px)",
        min_value=10,
        max_value=36,
        step=1,
        disabled=not show_check_icon,
        key="detail_check_icon_size",
    )
    check_icon_y_offset = st.slider(
        "아이콘 위아래 위치 (px)",
        min_value=-20,
        max_value=20,
        step=1,
        help="음수는 위로, 양수는 아래로 이동합니다.",
        disabled=not show_check_icon,
        key="detail_check_icon_y_offset",
    )

    st.divider()
    st.subheader("항목별 내용/스타일")
    section_settings = {
        "points": section_controls("points", "#0f172a"),
        "features": section_controls("features", "#1e293b"),
        "examples": section_controls("examples", "#1e293b"),
        "trust": section_controls("trust", "#0f172a"),
        "specs": section_controls("specs", "#1e293b"),
    }

    st.divider()
    st.subheader("추가 구역")
    st.caption("고정 영역 아래에 임의 구역을 이어 붙입니다.")
    if "extra_section_ids" not in st.session_state:
        st.session_state.extra_section_ids = []

    if st.button("구역 추가", use_container_width=True, key="btn_extra_section_add"):
        new_id = uuid.uuid4().hex[:8]
        st.session_state.extra_section_ids.append(new_id)
        current_order = sync_section_order()
        if f"extra:{new_id}" not in current_order:
            current_order.append(f"extra:{new_id}")
        st.session_state.section_order = current_order
        st.session_state.section_order_version = st.session_state.get("section_order_version", 0) + 1
        seq = len(st.session_state.extra_section_ids)
        st.session_state[f"xt_{new_id}_title"] = f"추가 구역 {seq}"
        st.session_state[f"xt_{new_id}_body"] = "내용을 입력하세요."
        st.session_state[f"xt_{new_id}_layout"] = "문단"
        st.session_state[f"xt_{new_id}_padding"] = 34
        st.session_state[f"xt_{new_id}_title_color"] = "#1e293b"
        st.session_state[f"xt_{new_id}_body_color"] = "#1e293b"
        st.session_state[f"xt_{new_id}_title_color_overridden"] = False
        st.session_state[f"xt_{new_id}_body_color_overridden"] = False
        st.session_state[f"xt_{new_id}_show"] = True
        st.session_state[f"xt_{new_id}_show_image"] = False
        st.rerun()

    for pos, sec_id in enumerate(list(st.session_state.extra_section_ids), start=1):
        with st.expander(f"추가 구역 {pos}", expanded=False):
            st.text_input("제목", key=f"xt_{sec_id}_title")
            st.text_area("내용", height=120, key=f"xt_{sec_id}_body")
            st.radio(
                "본문 형식",
                options=["문단", "줄별 리스트", "표(항목:값)"],
                key=f"xt_{sec_id}_layout",
                horizontal=True,
            )
            r1, r2 = st.columns(2)
            with r1:
                st.slider("패딩", min_value=16, max_value=96, step=2, key=f"xt_{sec_id}_padding")
            with r2:
                st.toggle("구역 표시", key=f"xt_{sec_id}_show")
            tcol, bcol = st.columns(2)
            with tcol:
                st.color_picker(
                    "제목 색상",
                    key=f"xt_{sec_id}_title_color",
                    on_change=mark_extra_section_color_override,
                    args=(sec_id, "title"),
                )
            with bcol:
                st.color_picker(
                    "본문 색상",
                    key=f"xt_{sec_id}_body_color",
                    on_change=mark_extra_section_color_override,
                    args=(sec_id, "body"),
                )
            st.toggle("이미지 표시", key=f"xt_{sec_id}_show_image")
            st.file_uploader(
                "구역 이미지",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"xt_{sec_id}_image",
                disabled=not st.session_state.get(f"xt_{sec_id}_show_image", False),
            )
            if st.button("이 구역 삭제", key=f"xt_{sec_id}_remove"):
                st.session_state.extra_section_ids = [
                    x for x in st.session_state.extra_section_ids if x != sec_id
                ]
                if "section_order" in st.session_state:
                    st.session_state.section_order = [
                        item for item in st.session_state.section_order if item != f"extra:{sec_id}"
                    ]
                    st.session_state.section_order_version = st.session_state.get("section_order_version", 0) + 1
                prefix = f"xt_{sec_id}_"
                for k in list(st.session_state.keys()):
                    if isinstance(k, str) and k.startswith(prefix):
                        del st.session_state[k]
                st.rerun()

    st.divider()
    st.subheader("구역 순서 변경")
    section_order = sync_section_order()
    if sort_items is None:
        st.warning("드래그 정렬을 사용하려면 `streamlit-sortables` 설치가 필요합니다.")
    else:
        label_to_id = {
            section_order_label(item_id, section_settings): item_id
            for item_id in section_order
        }
        sorted_labels = sort_items(
            list(label_to_id.keys()),
            direction="vertical",
            key=f"section_order_sortable_{st.session_state.get('section_order_version', 0)}",
        )
        current_labels = set(label_to_id.keys())
        sorted_label_set = set(sorted_labels)
        sorted_order = [label_to_id[label] for label in sorted_labels if label in label_to_id]
        if sorted_label_set == current_labels and sorted_order and sorted_order != section_order:
            st.session_state.section_order = sorted_order
            section_order = sorted_order

font_stack, font_link = resolve_font_preset(font_choice)
title_font_stack, title_font_link = resolve_font_preset(title_font_choice)
font_stack_attr = html.escape(font_stack, quote=False)
title_font_stack_attr = html.escape(title_font_stack, quote=False)
hero_image_fit = {
    "원본 사이즈": "contain",
    "영역 꽉 채우기": "cover",
    "전체 보이기": "contain",
    "비율 무시하고 채우기": "fill",
}[hero_image_fit_label]
hero_image_wrap_class = "hero-image-wrap original-size" if hero_image_fit_label == "원본 사이즈" else "hero-image-wrap"

font_hrefs = unique_font_stylesheets(font_link, title_font_link)
if any("fonts.googleapis.com" in h for h in font_hrefs):
    markdown_html(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        """
    )
for href in font_hrefs:
    markdown_html(f'<link rel="stylesheet" href="{html.escape(href)}">')

image_data_uri = resolve_image_data_uri("detail_hero_image")
hero_image = (
    f'<img src="{image_data_uri}" alt="대표상품이미지">'
    if image_data_uri
    else '<div class="image-placeholder">대표상품이미지를 업로드하면 이 영역에 표시됩니다.</div>'
)

st.title("상세페이지 생성기")
st.caption("좌측 사이드바에서 내용을 입력하고, 우측에서 실제 상세페이지처럼 구성된 미리보기를 확인하세요.")

checkpoint_keys = {
    CHECKPOINT_SECTION_OPTIONS[label] for label in checkpoint_section_labels
}
section_title_color_override = (
    global_section_title_color if use_global_section_title_color else None
)
body_color_override = global_body_color if use_global_body_color else None

ordered_section_html_parts = []
for item_id in section_order:
    kind, value = item_id.split(":", 1)
    if kind == "fixed":
        ordered_section_html_parts.append(
            render_section(
                value,
                section_settings[value],
                use_checkpoints=value in checkpoint_keys,
                horizontal_padding=hero_padding,
                body_color_override=body_color_override,
                title_color_override=section_title_color_override,
            )
        )
    elif kind == "extra":
        ordered_section_html_parts.append(
            render_extra_section_html(
                value,
                show_check_icon,
                horizontal_padding=hero_padding,
                body_color_override=body_color_override,
                title_color_override=section_title_color_override,
            )
        )

sections_html = "".join(ordered_section_html_parts)

hero_card_parts = [
    f'<section class="hero-card" style="padding:{hero_padding}px;">',
    '<div class="hero-eyebrow">PRODUCT DETAIL</div>',
]
if show_main_title:
    hero_card_parts.append(
        f'<h1 class="hero-title" style="color:{title_color};">{safe_text(title)}</h1>'
    )
if show_subtitle:
    hero_card_parts.append(
        f'<p class="hero-subtitle" style="color:{subtitle_color};">{safe_text(subtitle)}</p>'
    )
if show_hero_image:
    hero_card_parts.extend(
        [
            f'<div class="{hero_image_wrap_class}">',
            hero_image,
            "</div>",
        ]
    )
hero_card_parts.append("</section>")

font_size_style = (
    f"--fs-main-title:{main_title_px}px;"
    f"--fs-subtitle:{subtitle_px}px;"
    f"--fs-section-title:{section_title_px}px;"
    f"--fs-body:{body_px}px;"
    f"--hero-image-height:{hero_image_height}px;"
    f"--hero-image-fit:{hero_image_fit};"
)
check_icon_symbol = CHECK_ICON_OPTIONS.get(
    check_icon_shape,
    CHECK_ICON_OPTIONS["check"],
)[1]
check_icon_content = css_string_attr(check_icon_symbol)

hero_lines = [
    (
        f'<div id="detail-preview-root" class="preview-shell'
        f'{" hide-check-icon" if not show_check_icon else ""}" '
        f'style="background:{page_bg_color};--check-icon-color:{check_icon_color};'
        f"--check-icon-content:{check_icon_content};"
        f"--check-icon-size:{check_icon_size}px;"
        f"--check-icon-y-offset:{check_icon_y_offset}px;"
        f"--detail-font:{font_stack_attr};--title-font:{title_font_stack_attr};"
        f"{font_size_style}\">"
    ),
    f'<article class="detail-page" style="background:{hero_bg_color};">',
    *hero_card_parts,
]
preview_html = "\n".join(hero_lines) + sections_html + "\n</article>\n</div>"

st.markdown(preview_html, unsafe_allow_html=True)

standalone_html = build_standalone_html(
    title,
    preview_html,
    font_stack,
    font_link,
    title_font_stack,
    title_font_link,
)
html_bytes = standalone_html.encode("utf-8")
html_digest = hashlib.sha256(html_bytes).hexdigest()

st.divider()
with st.expander("상세페이지 다운로드", expanded=True):
    st.caption("현재 미리보기와 동일한 상세페이지를 HTML 또는 고해상도 PNG로 저장합니다.")

    st.download_button(
        label="HTML 다운로드",
        data=html_bytes,
        file_name="detail_page.html",
        mime="text/html",
        use_container_width=True,
    )

    st.subheader("PNG 다운로드")
    png_col1, png_col2 = st.columns(2)
    with png_col1:
        capture_width = st.number_input(
            "캡처 너비(px)",
            min_value=800,
            max_value=2400,
            value=1440,
            step=80,
        )
    with png_col2:
        capture_scale = st.selectbox(
            "고해상도 배율",
            options=[1, 2, 3],
            index=1,
            help="2배 이상은 더 선명하지만 생성 시간이 길어질 수 있습니다.",
        )

    if st.button("PNG 생성", type="primary", use_container_width=True):
        try:
            if not st.session_state.get("_playwright_chromium_ready"):
                with st.spinner("Chromium 브라우저 설치 중입니다. 최초 1회는 1~3분 걸릴 수 있습니다..."):
                    ensure_playwright_chromium_installed()
            with st.spinner("Playwright로 전체 상세페이지를 캡처하는 중입니다..."):
                png_bytes = capture_full_page_png(
                    standalone_html,
                    viewport_width=int(capture_width),
                    scale_factor=int(capture_scale),
                )
        except RuntimeError as exc:
            st.error(str(exc))
            if exc.__cause__:
                st.caption(f"상세: {exc.__cause__}")
        else:
            st.session_state.detail_page_png = png_bytes
            st.session_state.detail_page_png_digest = html_digest
            st.success("PNG 생성이 완료되었습니다.")

    png_bytes = st.session_state.get("detail_page_png")
    png_digest = st.session_state.get("detail_page_png_digest")
    if png_bytes and png_digest == html_digest:
        st.download_button(
            label="PNG 다운로드",
            data=png_bytes,
            file_name="detail_page.png",
            mime="image/png",
            use_container_width=True,
        )
    elif png_bytes:
        st.info("미리보기 내용이 변경되었습니다. 최신 내용으로 저장하려면 PNG를 다시 생성해 주세요.")
