"""Top menubar for RepoSage AI."""

import streamlit as st

# Column weights shared by menubar + settings dropdown row (must match).
_MENU_COLS = [2.2, 0.85, 1.0, 1.0, 1.05, 3.8]

NAVBAR_CSS = """
<style>
[data-testid="stHorizontalBlock"]:has(.reposage-menubar-anchor) {
    align-items: center !important;
    border-bottom: 1px solid #31333F;
    padding-bottom: 0.65rem;
    margin-bottom: 0 !important;
}
.reposage-menubar-brand {
    font-size: 1.25rem;
    font-weight: 700;
    color: #FAFAFA;
    padding: 0.35rem 0;
    white-space: nowrap;
}
.reposage-menubar-brand span {
    color: #7C9EFF;
}
/* Top-level menubar links */
.reposage-menubar-anchor ~ div [data-testid="column"] .stButton > button,
.reposage-settings-dropdown-row [data-testid="column"] .stButton > button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #c9d1d9 !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
    padding: 0.4rem 0.65rem !important;
}
.reposage-menubar-anchor ~ div [data-testid="column"] .stButton > button:hover,
.reposage-settings-dropdown-row [data-testid="column"] .stButton > button:hover {
    color: #7C9EFF !important;
    background: rgba(124, 158, 255, 0.1) !important;
}
/* Settings open — highlight like active menu */
div[data-testid="column"]:has(.reposage-settings-open) .stButton > button {
    color: #7C9EFF !important;
    background: rgba(124, 158, 255, 0.12) !important;
}
/* Dropdown panel */
.reposage-settings-dropdown-panel {
    display: none;
    background: #161b22;
    border: 1px solid #31333F;
    border-radius: 8px;
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.45);
    padding: 0.35rem 0;
    margin-top: -0.15rem;
    margin-bottom: 0.5rem;
    min-width: 11rem;
}
.reposage-settings-dropdown-panel .reposage-dropdown-label {
    color: #8b949e;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 0.35rem 0.75rem 0.2rem;
    margin: 0;
}
.reposage-settings-dropdown-row [data-testid="column"] .stButton > button {
    font-size: 0.9rem !important;
    padding: 0.45rem 0.75rem !important;
    width: 100% !important;
    text-align: left !important;
    justify-content: flex-start !important;
}
</style>
"""

SETTINGS_ITEMS = [
    {"id": "profile", "label": "User Profile", "icon": "👤"},
    {"id": "logout", "label": "Logout", "icon": "🚪"},
]


def _close_settings_menu() -> None:
    st.session_state["settings_menu_open"] = False


def navigate_home() -> None:
    _close_settings_menu()
    st.session_state["repo_loaded"] = False
    st.session_state.pop("coming_soon_menu", None)


def request_coming_soon(menu_label: str) -> None:
    st.session_state["coming_soon_menu"] = menu_label


def _coming_soon_dialog_body() -> None:
    menu = st.session_state.get("coming_soon_menu", "This feature")
    st.markdown(f"### {menu}")
    st.markdown(
        "This section is under development and will be available in a future release."
    )
    st.caption("RepoSage AI · Coming soon")
    if st.button("Got it", type="primary", use_container_width=True, key="coming_soon_close"):
        st.session_state.pop("coming_soon_menu", None)
        st.rerun()


if hasattr(st, "dialog"):

    @st.dialog("Coming Soon")
    def _coming_soon_popup():
        _coming_soon_dialog_body()


def show_coming_soon_if_needed() -> None:
    menu = st.session_state.get("coming_soon_menu")
    if not menu:
        return

    if hasattr(st, "dialog"):
        _coming_soon_popup()
    else:
        st.warning(f"🚧 **{menu}** — Coming soon!")
        if st.button("Dismiss", key="coming_soon_dismiss_fallback"):
            st.session_state.pop("coming_soon_menu", None)
            st.rerun()


def _tertiary_button(label: str, key: str) -> bool:
    try:
        return st.button(label, key=key, type="tertiary")
    except TypeError:
        return st.button(label, key=key)


def _menubar_click(display_label: str, coming_soon_label: str, *, key: str) -> None:
    if _tertiary_button(display_label, key):
        _close_settings_menu()
        request_coming_soon(coming_soon_label)
        st.rerun()


def _render_settings_dropdown() -> None:
    """Aligned dropdown under Settings — same link style as top-level menus."""
    if not st.session_state.get("settings_menu_open"):
        return

    st.markdown('<div class="reposage-settings-dropdown-row"></div>', unsafe_allow_html=True)
    _pad1, _pad2, _pad3, _pad4, drop_col, _spacer = st.columns(_MENU_COLS, gap="small")

    with drop_col:
        st.markdown('<div class="reposage-settings-dropdown-panel">', unsafe_allow_html=True)
        st.markdown('<p class="reposage-dropdown-label">Account</p>', unsafe_allow_html=True)

        for item in SETTINGS_ITEMS:
            label = f"{item['icon']} {item['label']}"
            if _tertiary_button(label, key=f"settings_{item['id']}"):
                _close_settings_menu()
                request_coming_soon(item["label"])
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


def render_navbar() -> None:
    if "settings_menu_open" not in st.session_state:
        st.session_state["settings_menu_open"] = False

    st.markdown(NAVBAR_CSS, unsafe_allow_html=True)
    st.markdown('<div class="reposage-menubar-anchor"></div>', unsafe_allow_html=True)

    brand_col, home_col, analyze_col, insights_col, settings_col, _spacer = st.columns(
        _MENU_COLS, gap="small"
    )

    with brand_col:
        st.markdown(
            '<p class="reposage-menubar-brand"> <span>RepoSage</span> AI</p>',
            unsafe_allow_html=True,
        )

    with home_col:
        if _tertiary_button(" Home", "nav_home"):
            navigate_home()
            st.rerun()

    with analyze_col:
        _menubar_click(" Analyze", "Analyze", key="nav_analyze")

    with insights_col:
        _menubar_click(" Insights", "Insights", key="nav_insights")

    with settings_col:
        settings_open = st.session_state.get("settings_menu_open", False)
        if settings_open:
            st.markdown('<div class="reposage-settings-open"></div>', unsafe_allow_html=True)
        settings_label = " Settings ▾"
        if _tertiary_button(settings_label, "nav_settings"):
            st.session_state["settings_menu_open"] = not settings_open
            st.rerun()

    _render_settings_dropdown()
