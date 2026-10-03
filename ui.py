"""
MARTIQ - Shared UI Helpers
----------------------------
Small, reusable pieces of UI so every page in views/ looks
consistent without copy-pasting the same CSS/HTML everywhere.

Nothing in this file imports from app.py or from views/, so it
cannot create a circular import.
"""

import streamlit as st
import config


def apply_global_css():
    """Inject the MARTIQ green theme once. Safe to call every rerun."""
    theme = config.THEME
    st.markdown(
        f"""
        <style>
            /* overall background */
            .stApp {{
                background-color: {theme['background']};
            }}

            /* page header banner used on every page */
            .martiq-header {{
                background: linear-gradient(90deg, {theme['primary']}, {theme['primary_light']});
                padding: 26px 32px;
                border-radius: 14px;
                color: white;
                margin-bottom: 22px;
            }}
            .martiq-header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            .martiq-header p {{
                margin: 4px 0 0 0;
                opacity: 0.9;
                font-size: 14px;
            }}

            /* generic card */
            .martiq-card {{
                background: {theme['card_bg']};
                border: 1px solid #E3ECE6;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 1px 4px rgba(0,0,0,0.05);
            }}

            /* buttons */
            .stButton > button {{
                border-radius: 8px;
                border: 1px solid {theme['primary']};
                color: {theme['primary']};
                font-weight: 600;
            }}
            .stButton > button:hover {{
                background-color: {theme['primary']};
                color: white;
                border: 1px solid {theme['primary']};
            }}

            /* sidebar */
            section[data-testid="stSidebar"] {{
                background-color: #F1F8F4;
            }}

            /* status pill */
            .martiq-online-pill {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                background-color: #E8F8EE;
                color: {theme['success']};
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 10px;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(icon: str, title: str, subtitle: str = ""):
    """Render the standard green MARTIQ header banner used on every page."""
    st.markdown(
        f"""
        <div class="martiq-header">
            <h1>{icon} {title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def placeholder_notice(module_name: str, phase_number: int):
    """Standard 'coming soon' body used by pages not yet built."""
    st.info(
        f"The **{module_name}** module will be built in **Phase {phase_number}**. "
        f"Navigation is fully working right now — this content is intentionally "
        f"a placeholder for this phase."
    )


def metric_card(icon: str, label: str, value: str, sub: str = ""):
    """
    Render one KPI stat card (used on the Dashboard, and reusable by
    Analytics/Reports in later phases). Returns nothing - it renders
    directly via st.markdown so callers just call it inside a column.
    """
    theme = config.THEME
    sub_html = f'<div style="font-size:12px; color:{theme["text_muted"]}; margin-top:2px;">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="martiq-card" style="text-align:left;">
            <div style="font-size:22px;">{icon}</div>
            <div style="font-size:13px; color:{theme['text_muted']};
                        text-transform:uppercase; letter-spacing:0.5px; margin-top:6px;">
                {label}
            </div>
            <div style="font-size:24px; font-weight:700; color:{theme['primary']}; margin-top:2px;">
                {value}
            </div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def alert_pill(text: str, level: str = "warning"):
    """Small colored pill used for stock/credit alert rows. level: warning|danger|success"""
    theme = config.THEME
    colors = {
        "warning": (theme["warning"], "#FEF6E7"),
        "danger": (theme["danger"], "#FCEBEA"),
        "success": (theme["success"], "#E8F8EE"),
    }
    fg, bg = colors.get(level, colors["warning"])
    st.markdown(
        f"""
        <div style="background:{bg}; color:{fg}; padding:8px 12px; border-radius:8px;
                    font-size:13px; margin-bottom:6px; font-weight:600;">
            {text}
        </div>
        """,
        unsafe_allow_html=True,
    )
