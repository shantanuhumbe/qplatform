"""
TI BA II Plus Financial Calculator — Faithful replica for CFA exam prep.
Matches the exact physical layout, button arrangement, and LCD styling
of the real Texas Instruments BA II Plus calculator.
"""

import math
import datetime
import streamlit as st
import numpy_financial as npf
import pandas as pd
import plotly.graph_objects as go


# ══════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ══════════════════════════════════════════════════════════════

def render_calculator_drawer():
    """Renders the collapsible BA II Plus calculator drawer above the quiz."""
    with st.expander("🧮 **BA II Plus Financial Calculator**", expanded=False):
        _inject_ba_ii_css()

        tab_calc, tab_ws = st.tabs(["🖩 Calculator", "📊 Worksheets"])

        with tab_calc:
            _render_ba_ii_plus()
        with tab_ws:
            _render_worksheets()


# ══════════════════════════════════════════════════════════════
# CSS — EXACT BA II PLUS PHYSICAL APPEARANCE
# ══════════════════════════════════════════════════════════════

def _inject_ba_ii_css():
    st.markdown("""
    <style>
    /* ─── Calculator Body ─── */
    .ba-body {
        background: #1a1a1a;
        border-radius: 18px;
        padding: 20px 16px 16px 16px;
        max-width: 460px;
        margin: 0 auto;
        box-shadow:
            0 12px 40px rgba(0,0,0,0.7),
            0 0 0 2px #2a2a2a,
            inset 0 1px 0 rgba(255,255,255,0.04);
        position: relative;
    }

    /* ─── TI Branding ─── */
    .ba-brand {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 0.55rem;
        font-weight: 700;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: #777;
        text-align: center;
        margin-bottom: 2px;
    }
    .ba-model {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 0.95rem;
        font-weight: 800;
        color: #ccc;
        text-align: center;
        margin-bottom: 10px;
        letter-spacing: 0.08em;
    }

    /* ─── Green LCD Display ─── */
    .ba-lcd {
        background: linear-gradient(180deg, #9aab8c 0%, #b4c4a4 40%, #a8b898 100%);
        border-radius: 6px;
        padding: 8px 14px;
        margin-bottom: 14px;
        text-align: right;
        border: 2px solid #555;
        box-shadow:
            inset 0 2px 8px rgba(0,0,0,0.35),
            0 1px 0 rgba(255,255,255,0.03);
        min-height: 56px;
    }
    .ba-lcd-ind {
        font-family: 'Courier New', monospace;
        font-size: 0.55rem;
        font-weight: 700;
        color: #3d4a33;
        text-align: left;
        min-height: 13px;
        letter-spacing: 0.08em;
    }
    .ba-lcd-val {
        font-family: 'Courier New', 'Lucida Console', monospace;
        font-size: 1.7rem;
        font-weight: 700;
        color: #1a2412;
        letter-spacing: 2px;
    }

    /* ─── Keypad Grid ─── */
    .ba-row {
        display: flex;
        gap: 4px;
        margin-bottom: 3px;
        justify-content: center;
    }
    .ba-row-sep {
        margin-top: 6px;
    }

    /* ─── Key Wrapper (2nd label + button) ─── */
    .ba-kw {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
        max-width: 88px;
        min-width: 60px;
    }
    .ba-kw-wide {
        flex: 1;
        max-width: 110px;
    }

    /* ─── 2nd-function label (gold, printed on face) ─── */
    .ba-2nd {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 0.5rem;
        font-weight: 700;
        color: #D4940A;
        text-align: center;
        min-height: 12px;
        line-height: 12px;
        letter-spacing: 0.02em;
        margin-bottom: 1px;
    }

    /* ─── All buttons: same dark charcoal (matches real BA II Plus) ─── */
    .ba-btn {
        width: 100%;
        padding: 9px 2px;
        border-radius: 4px;
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        text-align: center;
        cursor: pointer;
        border: 1px solid #222;
        background: linear-gradient(180deg, #3a3a3a, #2a2a2a);
        color: #f0f0f0;
        box-shadow:
            0 2px 4px rgba(0,0,0,0.5),
            inset 0 1px 0 rgba(255,255,255,0.06);
        transition: all 0.08s ease;
        user-select: none;
        line-height: 1.1;
        letter-spacing: 0.02em;
    }
    .ba-btn:hover {
        background: linear-gradient(180deg, #484848, #363636);
    }
    .ba-btn:active {
        transform: translateY(1px);
        box-shadow: 0 0 2px rgba(0,0,0,0.5);
        background: linear-gradient(180deg, #2a2a2a, #1e1e1e);
    }

    /* ─── ON/OFF button: slightly darker ─── */
    .ba-btn-onoff {
        background: linear-gradient(180deg, #2d2d2d, #1a1a1a);
        font-size: 0.55rem;
        letter-spacing: 0.05em;
    }
    .ba-btn-onoff:hover {
        background: linear-gradient(180deg, #3a3a3a, #2a2a2a);
    }

    /* ─── Spacer for empty cells ─── */
    .ba-spacer {
        flex: 1;
        max-width: 88px;
        min-width: 60px;
    }
    .ba-spacer-wide {
        flex: 1;
        max-width: 110px;
    }

    /* ─── Mode indicator below calc ─── */
    .ba-mode {
        text-align: center;
        font-size: 0.6rem;
        color: #666;
        margin-top: 6px;
        font-family: 'Helvetica Neue', Arial, sans-serif;
    }

    /* ─── Worksheet result card ─── */
    .ws-result {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(16, 185, 129, 0.08));
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-left: 4px solid #3B82F6;
        border-radius: 0 10px 10px 0;
        padding: 14px 18px;
        margin-top: 10px;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 1rem;
        color: #93C5FD;
    }

    /* ══════════════════════════════════════════════════════════
       OVERRIDE Streamlit default button styling INSIDE the
       calculator expander to match the real BA II Plus.
       All buttons: uniform dark charcoal, white text.
       ══════════════════════════════════════════════════════════ */

    /* Target ALL buttons inside the expander with Calculator tab */
    [data-testid="stExpander"] div.stButton > button {
        background: linear-gradient(180deg, #3a3a3a, #2a2a2a) !important;
        color: #f0f0f0 !important;
        border: 1px solid #222 !important;
        border-radius: 5px !important;
        box-shadow: 0 3px 6px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06) !important;
        font-family: 'Helvetica Neue', Arial, sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.78rem !important;
        padding: 10px 4px !important;
        letter-spacing: 0.02em !important;
        transition: all 0.08s ease !important;
        min-height: 38px !important;
    }

    [data-testid="stExpander"] div.stButton > button:hover {
        background: linear-gradient(180deg, #505050, #3e3e3e) !important;
        color: #ffffff !important;
        border-color: #444 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.1) !important;
        transform: none !important;
    }

    [data-testid="stExpander"] div.stButton > button:active {
        background: linear-gradient(180deg, #2a2a2a, #1e1e1e) !important;
        transform: translateY(1px) !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.5) !important;
    }

    [data-testid="stExpander"] div.stButton > button:focus {
        box-shadow: 0 3px 6px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06) !important;
        outline: none !important;
    }

    /* ─── 2nd Key (Yellow/Gold) ─── */
    [data-testid="stExpander"] div[class*="st-key-k_2ND"] button {
        background: linear-gradient(180deg, #EAA619, #C4870D) !important;
        color: #1a1a1a !important;
        border: 1px solid #9A6603 !important;
        box-shadow: 0 3px 6px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.25) !important;
    }
    [data-testid="stExpander"] div[class*="st-key-k_2ND"] button:hover {
        background: linear-gradient(180deg, #FFBD33, #DA9812) !important;
        color: #000000 !important;
    }
    [data-testid="stExpander"] div[class*="st-key-k_2ND"] button:active {
        background: linear-gradient(180deg, #C4870D, #9A6603) !important;
    }

    /* ─── TVM Keys (White) ─── */
    [data-testid="stExpander"] div[class*="st-key-k_N"] button,
    [data-testid="stExpander"] div[class*="st-key-k_IY"] button,
    [data-testid="stExpander"] div[class*="st-key-k_PV"] button,
    [data-testid="stExpander"] div[class*="st-key-k_PMT"] button,
    [data-testid="stExpander"] div[class*="st-key-k_FV"] button {
        background: linear-gradient(180deg, #ffffff, #dedede) !important;
        color: #1c1c1c !important;
        border: 1px solid #b5b5b5 !important;
        box-shadow: 0 3px 6px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.8) !important;
    }
    [data-testid="stExpander"] div[class*="st-key-k_N"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_IY"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_PV"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_PMT"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_FV"] button:hover {
        background: linear-gradient(180deg, #ffffff, #eeeeee) !important;
        color: #000000 !important;
    }
    [data-testid="stExpander"] div[class*="st-key-k_N"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_IY"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_PV"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_PMT"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_FV"] button:active {
        background: linear-gradient(180deg, #dedede, #c5c5c5) !important;
    }

    /* ─── Digit / Number Keys (Light Gray) ─── */
    [data-testid="stExpander"] div[class*="st-key-k_D0"] button,
    [data-testid="stExpander"] div[class*="st-key-k_D1"] button,
    [data-testid="stExpander"] div[class*="st-key-k_D2"] button,
    [data-testid="stExpander"] div[class*="st-key-k_D3"] button,
    [data-testid="stExpander"] div[class*="st-key-k_D4"] button,
    [data-testid="stExpander"] div[class*="st-key-k_D5"] button,
    [data-testid="stExpander"] div[class*="st-key-k_D6"] button,
    [data-testid="stExpander"] div[class*="st-key-k_D7"] button,
    [data-testid="stExpander"] div[class*="st-key-k_D8"] button,
    [data-testid="stExpander"] div[class*="st-key-k_D9"] button,
    [data-testid="stExpander"] div[class*="st-key-k_DOT"] button,
    [data-testid="stExpander"] div[class*="st-key-k_NEG"] button {
        background: linear-gradient(180deg, #7c7c7c, #606060) !important;
        color: #ffffff !important;
        border: 1px solid #484848 !important;
        box-shadow: 0 3px 6px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.12) !important;
    }
    [data-testid="stExpander"] div[class*="st-key-k_D0"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_D1"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_D2"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_D3"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_D4"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_D5"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_D6"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_D7"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_D8"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_D9"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_DOT"] button:hover,
    [data-testid="stExpander"] div[class*="st-key-k_NEG"] button:hover {
        background: linear-gradient(180deg, #8c8c8c, #707070) !important;
        color: #ffffff !important;
    }
    [data-testid="stExpander"] div[class*="st-key-k_D0"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_D1"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_D2"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_D3"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_D4"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_D5"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_D6"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_D7"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_D8"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_D9"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_DOT"] button:active,
    [data-testid="stExpander"] div[class*="st-key-k_NEG"] button:active {
        background: linear-gradient(180deg, #606060, #4c4c4c) !important;
    }

    /* Keep worksheet buttons (Calculate, Generate) with primary blue style */
    [data-testid="stExpander"] div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3B82F6, #1D4ED8) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4) !important;
    }
    [data-testid="stExpander"] div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #2563EB, #1E40AF) !important;
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6) !important;
    }

    </style>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# CALCULATOR RENDERING
# ══════════════════════════════════════════════════════════════

def _render_ba_ii_plus():
    """Render the full BA II Plus calculator."""
    _init_state()

    # Create placeholder for LCD at the top
    lcd_placeholder = st.empty()

    # ── Row 1: CPT  ENTER  ↑  ↓  ON/OFF ──
    c = st.columns(5)
    _key(c[0], "CPT", "CPT", sec="QUIT")
    _key(c[1], "ENTER", "ENT", sec="SET")
    _key(c[2], "↑", "UP", sec="DEL")
    _key(c[3], "↓", "DOWN", sec="INS")
    _key(c[4], "ON/OFF", "ONOFF", sec="")

    # ── Row 2: 2nd  CF  NPV  IRR  → ──
    c = st.columns(5)
    _key(c[0], "2nd", "2ND", sec="")
    _key(c[1], "CF", "CF", sec="")
    _key(c[2], "NPV", "NPV_K", sec="")
    _key(c[3], "IRR", "IRR_K", sec="")
    _key(c[4], "→", "BACK", sec="")

    # ── Row 3: N  I/Y  PV  PMT  FV (TVM) ──
    c = st.columns(5)
    _key(c[0], "N", "N", sec="xP/Y")
    _key(c[1], "I/Y", "IY", sec="P/Y")
    _key(c[2], "PV", "PV", sec="AMORT")
    _key(c[3], "PMT", "PMT", sec="BGN")
    _key(c[4], "FV", "FV", sec="CLR TVM")

    # ── Row 4: %  √x  x²  1/x  ÷ ──
    c = st.columns(5)
    _key(c[0], "%", "PCT", sec="K")
    _key(c[1], "√x", "SQRT", sec="")
    _key(c[2], "x²", "SQR", sec="")
    _key(c[3], "1/x", "INV_REC", sec="")
    _key(c[4], "÷", "DIV", sec="RAND")

    # ── Row 5: INV  (  )  yˣ  × ──
    c = st.columns(5)
    _key(c[0], "INV", "INV", sec="HYP")
    _key(c[1], "(", "LP", sec="SIN")
    _key(c[2], ")", "RP", sec="COS")
    _key(c[3], "yˣ", "POW", sec="TAN")
    _key(c[4], "×", "MUL", sec="x!")

    # ── Row 6: LN  7  8  9  − ──
    c = st.columns(5)
    _key(c[0], "LN", "LN", sec="eˣ")
    _key(c[1], "7", "D7", sec="DATA")
    _key(c[2], "8", "D8", sec="STAT")
    _key(c[3], "9", "D9", sec="BOND")
    _key(c[4], "−", "SUB", sec="nPr")

    # ── Row 7: STO  4  5  6  + ──
    c = st.columns(5)
    _key(c[0], "STO", "STO", sec="ROUND")
    _key(c[1], "4", "D4", sec="DEPR")
    _key(c[2], "5", "D5", sec="Δ%")
    _key(c[3], "6", "D6", sec="BRKEVN")
    _key(c[4], "+", "ADD", sec="nCr")

    # ── Row 8: RCL  1  2  3  ＝ ──
    c = st.columns(5)
    _key(c[0], "RCL", "RCL", sec="")
    _key(c[1], "1", "D1", sec="DATE")
    _key(c[2], "2", "D2", sec="ICONV")
    _key(c[3], "3", "D3", sec="PROFIT")
    _key(c[4], "＝", "EQ", sec="ANS")

    # ── Row 9: CE/C  0  .  +/− ──
    c = st.columns(5)
    _key(c[0], "CE/C", "CEC", sec="CLR WORK")
    _key(c[1], "0", "D0", sec="MEM")
    _key(c[2], ".", "DOT", sec="FORMAT")
    _key(c[3], "+/−", "NEG", sec="RESET")
    c[4].write("")

    # Mode line
    mode_parts = []
    if st.session_state.get("calc_2nd"):
        mode_parts.append("🟡 2nd")
    m = st.session_state.get("calc_mode", "CALC")
    if m == "TVM":
        mode_parts.append("TVM")
    elif m == "CF":
        mode_parts.append("CF Worksheet")
    if st.session_state.get("_cpt"):
        mode_parts.append("CPT →")

    if mode_parts:
        st.markdown(f'<div class="ba-mode">{" │ ".join(mode_parts)}</div>', unsafe_allow_html=True)

    # Render updated LCD into placeholder
    ind = st.session_state.get("calc_ind", "")
    val = st.session_state.get("calc_disp", "0")
    lcd_placeholder.markdown(f"""
    <div class="ba-body">
        <div class="ba-brand">Texas Instruments</div>
        <div class="ba-model">BA II PLUS™</div>
        <div class="ba-lcd">
            <div class="ba-lcd-ind">{ind}</div>
            <div class="ba-lcd-val">{val}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _key(col, label, action, sec=""):
    """Render a single key in a column with optional 2nd-function label."""
    with col:
        # 2nd function label (gold text above button)
        if sec:
            st.markdown(f'<div style="text-align:center;font-size:0.5rem;font-weight:700;color:#D4940A;min-height:14px;line-height:14px;">{sec}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="min-height:14px;"></div>', unsafe_allow_html=True)
        if st.button(label, key=f"k_{action}", use_container_width=True):
            _handle(action)


# ══════════════════════════════════════════════════════════════
# CALCULATOR STATE
# ══════════════════════════════════════════════════════════════

def _init_state():
    defaults = {
        "calc_disp": "0",
        "calc_ind": "",
        "calc_cur": "",
        "calc_op": None,
        "calc_prev": None,
        "calc_new": True,
        "calc_2nd": False,
        "calc_mem": {},
        "calc_mode": "CALC",
        "tvm_n": 0.0, "tvm_iy": 0.0, "tvm_pv": 0.0,
        "tvm_pmt": 0.0, "tvm_fv": 0.0,
        "tvm_py": 1.0, "tvm_cy": 1.0,
        "tvm_bgn": False,
        "cf_flows": [0.0],
        "cf_idx": 0,
        "cf_rate": 0.0,
        "_cpt": False,
        "calc_sto_pending": False,
        "calc_rcl_pending": False,
        "calc_decimals": 2,
        "calc_decimals_pending": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _fmt(value):
    """Format number for LCD display."""
    if isinstance(value, str):
        return value
    if value == float("inf") or value == float("-inf") or math.isnan(value):
        return "Error"
    if abs(value) < 1e-12 and value != 0:
        return f"{value:.4e}"
        
    decimals = st.session_state.get("calc_decimals", 2)
    if decimals == 9:
        # Floating point format
        if value == int(value) and abs(value) < 1e12:
            return f"{int(value):,}"
        if abs(value) >= 1e12:
            return f"{value:.4e}"
        return f"{value:,.9f}".rstrip("0").rstrip(".")
    else:
        # Fixed point format
        if abs(value) >= 1e12:
            return f"{value:.4e}"
        return f"{value:,.{decimals}f}"


def _val():
    """Get current numeric value from display."""
    try:
        return float(st.session_state.calc_disp.replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def _exec_op(a, op, b):
    """Execute binary operation."""
    try:
        if op == "+": return a + b
        if op == "-": return a - b
        if op == "×": return a * b
        if op == "÷": return a / b if b != 0 else float("inf")
        if op == "yˣ": return a ** b
        if op == "x√y": return a ** (1.0 / b) if b != 0 else float("inf")
        if op == "nPr":
            n, r = int(a), int(b)
            if n >= r >= 0:
                return float(math.perm(n, r))
            return float("nan")
        if op == "nCr":
            n, r = int(a), int(b)
            if n >= r >= 0:
                return float(math.comb(n, r))
            return float("nan")
    except Exception:
        return float("nan")
    return b


# ══════════════════════════════════════════════════════════════
# KEY HANDLER
# ══════════════════════════════════════════════════════════════

def _handle(action):
    """Handle a BA II Plus key press."""
    s = st.session_state
    is2 = s.get("calc_2nd", False)

    def _off2():
        s.calc_2nd = False
        s.calc_ind = ""

    # ── 2nd ──
    if action == "2ND":
        s.calc_2nd = not is2
        s.calc_ind = "2ND" if not is2 else ""
        return

    # ── ON/OFF ──
    if action == "ONOFF":
        for k in ("calc_disp", "calc_cur", "calc_op", "calc_prev", "calc_ind", "calc_inv"):
            s[k] = {"calc_disp": "0", "calc_cur": "", "calc_op": None, "calc_prev": None, "calc_ind": "", "calc_inv": False}[k]
        s.calc_new = True
        s.calc_2nd = False
        s.calc_mode = "CALC"
        s._cpt = False
        return

    # ── Backspace (→) ──
    if action == "BACK":
        if not s.calc_new and s.calc_cur:
            s.calc_cur = s.calc_cur[:-1]
            if not s.calc_cur or s.calc_cur == "-":
                s.calc_cur = "0"
                s.calc_new = True
            s.calc_disp = s.calc_cur
        if is2: _off2()
        return

    # ── CE/C ──
    if action == "CEC":
        s.calc_sto_pending = False
        s.calc_rcl_pending = False
        s.calc_decimals_pending = False
        if is2:
            # CLR WORK
            if s.calc_mode == "CF":
                s.cf_flows = [0.0]
                s.cf_idx = 0
                s.cf_rate = 0.0
            s.calc_disp = "0"
            s.calc_ind = "CLR WORK"
            _off2()
        else:
            s.calc_disp = "0"
            s.calc_cur = ""
            s.calc_op = None
            s.calc_prev = None
            s.calc_new = True
            s.calc_ind = ""
        s.calc_inv = False
        return

    # ── Digits ──
    if action.startswith("D") and action[1:].isdigit():
        d = action[1:]
        
        # Check if decimals setting is pending
        if s.get("calc_decimals_pending"):
            reg = int(d)
            s.calc_decimals = reg
            s.calc_ind = f"DEC = {reg}"
            s.calc_decimals_pending = False
            s.calc_new = True
            if is2: _off2()
            return
            
        # Check if STO or RCL is pending
        if s.get("calc_sto_pending"):
            reg = int(d)
            v = _val()
            s.calc_mem[reg] = v
            s.calc_ind = f"STO {reg}"
            s.calc_sto_pending = False
            s.calc_new = True
            if is2: _off2()
            return
            
        if s.get("calc_rcl_pending"):
            reg = int(d)
            v = s.calc_mem.get(reg, 0.0)
            s.calc_disp = _fmt(v)
            s.calc_cur = str(v)
            s.calc_ind = f"RCL {reg}"
            s.calc_rcl_pending = False
            s.calc_new = True
            if is2: _off2()
            return

        if is2 and action == "D0":
            # MEM worksheet
            mem_summary = ", ".join(f"M{k}:{_fmt(v)}" for k, v in sorted(s.calc_mem.items()) if v != 0)
            if not mem_summary:
                mem_summary = "All registers empty"
            s.calc_disp = "MEM"
            s.calc_ind = mem_summary[:30]
            s.calc_new = True
            _off2()
            return

        if s.calc_new:
            s.calc_cur = d
            s.calc_new = False
        else:
            s.calc_cur = (s.calc_cur or "") + d if not (s.calc_cur == "0" and d != "0") else d
        s.calc_disp = s.calc_cur
        if is2: _off2()
        s.calc_inv = False
        return

    # ── Decimal ──
    if action == "DOT":
        if is2:
            s.calc_decimals_pending = True
            s.calc_ind = f"DEC = {s.calc_decimals}"
            _off2()
            return
            
        if s.calc_new:
            s.calc_cur = "0."
            s.calc_new = False
        elif "." not in (s.calc_cur or ""):
            s.calc_cur = (s.calc_cur or "0") + "."
        s.calc_disp = s.calc_cur
        if is2: _off2()
        s.calc_inv = False
        return

    # ── +/− ──
    if action == "NEG":
        if is2:
            # RESET
            for k in list(s.keys()):
                if k.startswith("calc_") or k.startswith("tvm_") or k.startswith("cf_") or k == "_cpt":
                    del s[k]
            _init_state()
            s.calc_disp = "0"
            s.calc_ind = "RESET"
            _off2()
            return
            
        v = _val()
        v = -v
        s.calc_cur = str(v)
        s.calc_disp = _fmt(v)
        if is2: _off2()
        s.calc_inv = False
        return

    # ── Percent (%) ──
    if action == "PCT":
        v = _val()
        v = v / 100.0
        s.calc_cur = str(v)
        s.calc_disp = _fmt(v)
        s.calc_new = True
        if is2: _off2()
        s.calc_inv = False
        return

    # ── Operators ──
    if action in ("ADD", "SUB", "MUL", "DIV"):
        if is2:
            if action == "MUL":
                # x!
                v = _val()
                try:
                    if v < 0 or v != int(v):
                        r = float("nan")
                    else:
                        r = float(math.factorial(int(v)))
                except Exception:
                    r = float("nan")
                s.calc_disp = _fmt(r); s.calc_cur = str(r); s.calc_new = True
                s.calc_ind = f"{int(v)}!"
                _off2()
                return
                
            if action == "DIV":
                # RAND
                import random
                r = random.random()
                s.calc_disp = _fmt(r); s.calc_cur = str(r); s.calc_new = True
                s.calc_ind = "RAND"
                _off2()
                return
                
            if action == "SUB":
                # nPr
                s.calc_prev = _val()
                s.calc_op = "nPr"
                s.calc_ind = "nPr"
                s.calc_new = True
                _off2()
                return
                
            if action == "ADD":
                # nCr
                s.calc_prev = _val()
                s.calc_op = "nCr"
                s.calc_ind = "nCr"
                s.calc_new = True
                _off2()
                return
                
        op = {"+": "+", "-": "-", "×": "×", "÷": "÷", "ADD": "+", "SUB": "-", "MUL": "×", "DIV": "÷"}[action]
        cv = _val()
        if s.calc_op and not s.calc_new:
            res = _exec_op(s.calc_prev, s.calc_op, cv)
            s.calc_prev = res
            s.calc_disp = _fmt(res)
        else:
            s.calc_prev = cv
        s.calc_op = op
        s.calc_new = True
        s.calc_ind = op
        if is2: _off2()
        s.calc_inv = False
        return

    # ── = / ENTER ──
    if action in ("EQ", "ENT"):
        if is2 and action == "EQ":
            # ANS — recall last answer
            ans = s.get("calc_ans", 0.0)
            s.calc_disp = _fmt(ans)
            s.calc_cur = str(ans)
            s.calc_new = True
            s.calc_ind = "ANS"
            _off2()
            return
        cv = _val()
        if s.calc_op and s.calc_prev is not None:
            res = _exec_op(s.calc_prev, s.calc_op, cv)
            s.calc_disp = _fmt(res)
            s.calc_cur = str(res)
            s.calc_ans = res # Save last calculated answer
            s.calc_prev = None
            s.calc_op = None
            s.calc_new = True
            s.calc_ind = ""
        if is2: _off2()
        s.calc_inv = False
        return

    # ── Scientific ──
    if action == "SQRT":
        v = _val()
        r = math.sqrt(v) if v >= 0 else float("nan")
        s.calc_disp = _fmt(r); s.calc_cur = str(r); s.calc_new = True
        if is2: _off2()
        s.calc_inv = False
        return

    if action == "SQR":
        v = _val()
        r = v ** 2
        s.calc_disp = _fmt(r); s.calc_cur = str(r); s.calc_new = True
        if is2: _off2()
        s.calc_inv = False
        return

    if action == "LN":
        v = _val()
        if is2 or s.get("calc_inv"):
            try: r = math.exp(v)
            except OverflowError: r = float("inf")
            s.calc_ind = "eˣ"
            s.calc_inv = False
            _off2()
        else:
            r = math.log(v) if v > 0 else float("nan")
        s.calc_disp = _fmt(r); s.calc_cur = str(r); s.calc_new = True
        return

    if action == "POW":
        cv = _val()
        if is2:
            # TAN
            try:
                if math.cos(math.radians(cv)) == 0:
                    r = float("inf")
                else:
                    r = math.tan(math.radians(cv))
            except Exception:
                r = float("nan")
            s.calc_disp = _fmt(r); s.calc_cur = str(r); s.calc_new = True
            s.calc_ind = f"TAN({cv})"
            _off2()
        else:
            s.calc_prev = cv
            s.calc_op = "yˣ"
            s.calc_ind = "yˣ"
            s.calc_new = True
            s.calc_inv = False
        return

    if action == "INV_REC":
        v = _val()
        r = 1.0 / v if v != 0 else float("inf")
        s.calc_disp = _fmt(r); s.calc_cur = str(r); s.calc_new = True
        if is2: _off2()
        s.calc_inv = False
        return

    if action == "INV":
        s.calc_inv = not s.get("calc_inv", False)
        s.calc_ind = "INV" if s.calc_inv else ""
        if is2: _off2()
        return

    # ── CPT ──
    if action == "CPT":
        if is2:
            s.calc_mode = "CALC"
            s.calc_ind = ""
            _off2()
        else:
            s._cpt = True
            s.calc_ind = "CPT"
        return

    # ── TVM: N, I/Y, PV, PMT, FV ──
    if action in ("N", "IY", "PV", "PMT", "FV"):
        reg = {"N": "tvm_n", "IY": "tvm_iy", "PV": "tvm_pv", "PMT": "tvm_pmt", "FV": "tvm_fv"}[action]
        nice = action.replace("IY", "I/Y")
        s.calc_mode = "TVM"

        # Check if RCL is pending
        if s.get("calc_rcl_pending"):
            v = s.get(reg, 0.0)
            s.calc_disp = _fmt(v)
            s.calc_cur = str(v)
            s.calc_ind = f"RCL {nice}"
            s.calc_rcl_pending = False
            s.calc_new = True
            if is2: _off2()
            return

        # Check if STO is pending
        if s.get("calc_sto_pending"):
            v = _val()
            s[reg] = v
            s.calc_ind = f"STO {nice}"
            s.calc_sto_pending = False
            s.calc_new = True
            if is2: _off2()
            return

        if is2:
            if action == "N":
                v = _val()
                r = v * s.tvm_py
                s.tvm_n = r
                s.calc_disp = _fmt(r)
                s.calc_ind = f"N={_fmt(r)}"
            elif action == "IY":
                v = _val()
                if v > 0:
                    s.tvm_py = v; s.tvm_cy = v
                    s.calc_ind = f"P/Y={_fmt(v)}"
            elif action == "PV":
                s.calc_ind = "AMORT"
            elif action == "PMT":
                s.tvm_bgn = not s.tvm_bgn
                s.calc_ind = "BGN" if s.tvm_bgn else "END"
            elif action == "FV":
                s.tvm_n = 0; s.tvm_iy = 0; s.tvm_pv = 0; s.tvm_pmt = 0; s.tvm_fv = 0
                s.calc_disp = "0"
                s.calc_ind = "CLR TVM"
            _off2()
            s.calc_new = True
            return

        if s.get("_cpt"):
            s._cpt = False
            _compute_tvm(action)
            return

        v = _val()
        s[reg] = v
        s.calc_ind = f"{nice}={_fmt(v)}"
        s.calc_new = True
        return

    # ── CF ──
    if action == "CF":
        s.calc_mode = "CF"
        s.cf_idx = 0
        v = s.cf_flows[0] if s.cf_flows else 0.0
        s.calc_disp = _fmt(v)
        s.calc_ind = "CF0"
        s.calc_new = True
        if is2: _off2()
        return

    # ── NPV ──
    if action == "NPV_K":
        if not s.calc_new:
            s.cf_rate = _val()
        try:
            r = s.cf_rate / 100.0
            res = npf.npv(r, s.cf_flows)
            s.calc_disp = _fmt(res)
            s.calc_ind = f"NPV I={s.cf_rate}%"
        except Exception as e:
            s.calc_disp = "Error"
            s.calc_ind = str(e)[:20]
        s.calc_new = True
        if is2: _off2()
        return

    # ── IRR ──
    if action == "IRR_K":
        try:
            res = npf.irr(s.cf_flows)
            if math.isnan(res):
                s.calc_disp = "Error"
                s.calc_ind = "No IRR"
            else:
                s.calc_disp = _fmt(res * 100)
                s.calc_ind = "IRR%"
        except Exception:
            s.calc_disp = "Error"
            s.calc_ind = "IRR Error"
        s.calc_new = True
        if is2: _off2()
        return

    # ── STO ──
    if action == "STO":
        if s.calc_mode == "CF":
            v = _val()
            idx = s.cf_idx
            if idx < len(s.cf_flows):
                s.cf_flows[idx] = v
            else:
                s.cf_flows.append(v)
            s.calc_ind = f"CF{idx}={_fmt(v)}"
            s.calc_new = True
        else:
            s.calc_sto_pending = True
            s.calc_rcl_pending = False
            s.calc_ind = "STO"
        if is2: _off2()
        return

    # ── RCL ──
    if action == "RCL":
        s.calc_rcl_pending = True
        s.calc_sto_pending = False
        s.calc_ind = "RCL"
        if is2: _off2()
        return

    # ── ↑ / ↓ (CF navigation) ──
    if action in ("UP", "DOWN"):
        if is2:
            if action == "UP":
                s.calc_ind = "FORMAT"
            elif action == "DOWN":
                s.calc_ind = "RESET"
            _off2()
            return

        if s.calc_mode == "CF":
            if not s.calc_new:
                v = _val()
                idx = s.cf_idx
                if idx < len(s.cf_flows):
                    s.cf_flows[idx] = v
                else:
                    s.cf_flows.append(v)

            if action == "UP" and s.cf_idx > 0:
                s.cf_idx -= 1
            elif action == "DOWN":
                s.cf_idx += 1
                if s.cf_idx >= len(s.cf_flows):
                    s.cf_flows.append(0.0)

            idx = s.cf_idx
            v = s.cf_flows[idx] if idx < len(s.cf_flows) else 0.0
            s.calc_disp = _fmt(v)
            s.calc_ind = f"CF{idx}"
            s.calc_new = True
        return

    # ── Parentheses (simplified) ──
    if action in ("LP", "RP"):
        if is2:
            if action == "LP":
                # SIN
                v = _val()
                r = math.sin(math.radians(v))
                s.calc_disp = _fmt(r); s.calc_cur = str(r); s.calc_new = True
                s.calc_ind = f"SIN({v})"
            elif action == "RP":
                # COS
                v = _val()
                r = math.cos(math.radians(v))
                s.calc_disp = _fmt(r); s.calc_cur = str(r); s.calc_new = True
                s.calc_ind = f"COS({v})"
            _off2()
            return
        return

    if is2: _off2()


def _compute_tvm(solve_for):
    """Solve TVM equation for the specified variable."""
    s = st.session_state
    n = s.tvm_n; iy = s.tvm_iy; pv = s.tvm_pv; pmt = s.tvm_pmt; fv = s.tvm_fv
    py = s.tvm_py; cy = s.tvm_cy

    try:
        pr = (iy / 100.0) / cy
        ar = (1 + pr) ** (cy / py) - 1

        if solve_for == "N":
            r = npf.nper(ar, pmt, pv, fv)
            s.tvm_n = r; label = "N"
        elif solve_for == "IY":
            rp = npf.rate(n, pmt, pv, fv)
            r = ((1 + rp) ** (py / cy) - 1) * cy * 100
            s.tvm_iy = r; label = "I/Y"
        elif solve_for == "PV":
            r = npf.pv(ar, n, pmt, fv)
            s.tvm_pv = r; label = "PV"
        elif solve_for == "PMT":
            r = npf.pmt(ar, n, pv, fv)
            s.tvm_pmt = r; label = "PMT"
        elif solve_for == "FV":
            r = npf.fv(ar, n, pmt, pv)
            s.tvm_fv = r; label = "FV"
        else:
            return

        s.calc_disp = _fmt(r)
        s.calc_ind = f"CPT {label}={_fmt(r)}"
        s.calc_new = True
    except Exception as e:
        s.calc_disp = "Error"
        s.calc_ind = str(e)[:30]


# ══════════════════════════════════════════════════════════════
# WORKSHEETS TAB
# ══════════════════════════════════════════════════════════════

def _render_worksheets():
    bond_t, amort_t, iconv_t, profit_t, date_t, depr_t, brk_t = st.tabs([
        "📜 Bond Pricing", 
        "📋 Loan Amortization",
        "🔄 Interest Conversion",
        "💰 Profit Margin",
        "📅 Date Calculations",
        "📉 Depreciation",
        "📊 Break-Even"
    ])
    with bond_t:
        _render_bond()
    with amort_t:
        _render_amort()
    with iconv_t:
        _render_iconv()
    with profit_t:
        _render_profit()
    with date_t:
        _render_date()
    with depr_t:
        _render_depr()
    with brk_t:
        _render_brkevn()


def _render_bond():
    st.markdown('<p style="font-size:0.85em;color:#94A3B8;">💡 Compute bond clean price, Macaulay & Modified Duration.</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        face = st.number_input("Face Value", value=1000.0, step=100.0, format="%.2f", key="b_face")
        cpn = st.number_input("Coupon Rate (%)", value=5.0, step=0.25, format="%.4f", key="b_cpn")
        yrs = st.number_input("Years to Maturity", value=10.0, step=1.0, format="%.1f", min_value=0.5, key="b_yrs")
    with c2:
        ytm = st.number_input("YTM (%)", value=5.0, step=0.25, format="%.4f", key="b_ytm")
        frq = st.selectbox("Frequency", [1,2,4,12], format_func=lambda x:{1:"Annual",2:"Semi-Annual",4:"Quarterly",12:"Monthly"}[x], index=1, key="b_frq")

    if st.button("Calculate", type="primary", use_container_width=True, key="b_go"):
        try:
            np_ = int(yrs * frq)
            cp = (cpn / 100) * face / frq
            py_ = (ytm / 100) / frq
            if py_ == 0:
                price = cp * np_ + face
                md = sum((t+1)*cp for t in range(np_)) + np_*face
                md /= price if price else 1
            else:
                pvc = cp * (1 - (1+py_)**(-np_)) / py_
                pvf = face / (1+py_)**np_
                price = pvc + pvf
                wc = sum(t * (cp if t < np_ else cp+face) / (1+py_)**t for t in range(1, np_+1))
                md = wc / price if price else 0
            modd = md / (1+py_) if py_ else md
            r1, r2, r3 = st.columns(3)
            with r1: st.metric("Clean Price", f"${price:,.2f}")
            with r2: st.metric("Mac Duration", f"{md/frq:,.4f} yrs")
            with r3: st.metric("Mod Duration", f"{modd/frq:,.4f} yrs")
            if abs(price - face) < 0.01:
                st.info("📌 Trading at **Par**")
            elif price > face:
                st.success(f"📈 **Premium** (+${price-face:,.2f})")
            else:
                st.warning(f"📉 **Discount** (−${face-price:,.2f})")
        except Exception as e:
            st.error(f"Error: {e}")


def _render_amort():
    st.markdown('<p style="font-size:0.85em;color:#94A3B8;">💡 Generate full amortization schedule.</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        loan = st.number_input("Loan Amount ($)", value=100000.0, step=10000.0, format="%.2f", key="a_loan")
        rate = st.number_input("Annual Rate (%)", value=6.0, step=0.25, format="%.4f", key="a_rate")
    with c2:
        term = st.number_input("Term (Years)", value=30.0, step=1.0, format="%.1f", min_value=0.5, key="a_term")
        freq = st.selectbox("Frequency", [1,2,4,12], format_func=lambda x:{1:"Annual",2:"Semi-Annual",4:"Quarterly",12:"Monthly"}[x], index=3, key="a_freq")

    if st.button("Generate Schedule", type="primary", use_container_width=True, key="a_go"):
        try:
            np_ = int(term * freq)
            pr_ = (rate / 100) / freq
            pmt_ = -npf.pmt(pr_, np_, loan)
            bal = loan
            rows = []
            for t in range(1, np_+1):
                intr = bal * pr_
                prin = pmt_ - intr
                bal -= prin
                if bal < 0.01: bal = 0.0
                rows.append({"Period": t, "Payment": round(pmt_,2), "Interest": round(intr,2), "Principal": round(prin,2), "Balance": round(bal,2)})
            df = pd.DataFrame(rows)
            tp = pmt_ * np_
            ti = tp - loan
            m1, m2, m3 = st.columns(3)
            with m1: st.metric("Payment", f"${pmt_:,.2f}")
            with m2: st.metric("Total Interest", f"${ti:,.2f}")
            with m3: st.metric("Total Cost", f"${tp:,.2f}")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Period"], y=df["Principal"], name="Principal", fill="tozeroy", line=dict(color="#3B82F6", width=1), fillcolor="rgba(59,130,246,0.3)"))
            fig.add_trace(go.Scatter(x=df["Period"], y=df["Interest"], name="Interest", fill="tozeroy", line=dict(color="#EF4444", width=1), fillcolor="rgba(239,68,68,0.2)"))
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=10,t=30,b=10), height=250, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), xaxis_title="Period", yaxis_title="$")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with st.expander("📋 Full Table", expanded=False):
                st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error: {e}")


def _render_iconv():
    st.markdown('<p style="font-size:0.85em;color:#94A3B8;">💡 Interest rate conversions between Nominal (NOM) and Effective (EFF) rates.</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        nom_in = st.number_input("Nominal Rate (NOM %)", value=8.0, step=0.25, format="%.4f", key="ic_nom")
        cy_in_nom = st.number_input("Compounding Periods (C/Y)", value=4.0, step=1.0, format="%.0f", min_value=1.0, key="ic_cy_nom")
        if st.button("Compute EFF", type="primary", use_container_width=True, key="ic_eff_go"):
            try:
                eff = ((1 + (nom_in / 100.0) / cy_in_nom) ** cy_in_nom - 1) * 100.0
                st.markdown(f'<div class="ws-result">Effective Rate (EFF) = {eff:,.6f}%</div>', unsafe_allow_html=True)
                
                # Comparative compounding
                freqs = [1, 2, 4, 12, 365]
                labels = ["Annual", "Semi-Annual", "Quarterly", "Monthly", "Daily"]
                rows = []
                for f, l in zip(freqs, labels):
                    e = ((1 + (nom_in / 100.0) / f) ** f - 1) * 100.0
                    rows.append({"Frequency": l, "Compounding per Year": f, "Effective Rate (EFF %)": f"{e:,.4f}%"})
                st.markdown("##### EFF with other compounding frequencies:")
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Error: {e}")
    with c2:
        eff_in = st.number_input("Effective Rate (EFF %)", value=8.2432, step=0.25, format="%.4f", key="ic_eff")
        cy_in_eff = st.number_input("Compounding Periods (C/Y)", value=4.0, step=1.0, format="%.0f", min_value=1.0, key="ic_cy_eff")
        if st.button("Compute NOM", type="primary", use_container_width=True, key="ic_nom_go"):
            try:
                nom = cy_in_eff * (((1 + eff_in / 100.0) ** (1.0 / cy_in_eff)) - 1) * 100.0
                st.markdown(f'<div class="ws-result">Nominal Rate (NOM) = {nom:,.6f}%</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {e}")


def _render_profit():
    st.markdown('<p style="font-size:0.85em;color:#94A3B8;">💡 Compute Profit Margin, Cost (CST) or Selling Price (SEL).</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        cost = st.number_input("Cost (CST)", value=100.0, step=5.0, format="%.2f", key="pr_cost")
    with c2:
        sell = st.number_input("Selling Price (SEL)", value=125.0, step=5.0, format="%.2f", key="pr_sell")
    with c3:
        margin = st.number_input("Gross Margin (MAR %)", value=20.0, step=1.0, format="%.4f", key="pr_margin")

    st.markdown("Solve for unknown variable (uses the other two):")
    btn_c1, btn_c2, btn_c3 = st.columns(3)
    
    with btn_c1:
        if st.button("Solve Cost (CST)", use_container_width=True, key="pr_solve_cst"):
            resolved_cst = sell * (1.0 - margin / 100.0)
            gp = sell - resolved_cst
            st.markdown(f"""
            <div class="ws-result">
            <b>Solved Cost:</b><br/>
            CST = ${resolved_cst:,.2f}<br/>
            Gross Profit = ${gp:,.2f}
            </div>
            """, unsafe_allow_html=True)
    with btn_c2:
        if st.button("Solve Selling Price (SEL)", use_container_width=True, key="pr_solve_sell"):
            if margin >= 100.0:
                st.error("Margin cannot be 100% or greater when solving for Selling Price.")
            else:
                resolved_sel = cost / (1.0 - margin / 100.0)
                gp = resolved_sel - cost
                st.markdown(f"""
                <div class="ws-result">
                <b>Solved Selling Price:</b><br/>
                SEL = ${resolved_sel:,.2f}<br/>
                Gross Profit = ${gp:,.2f}
                </div>
                """, unsafe_allow_html=True)
    with btn_c3:
        if st.button("Solve Margin (MAR)", use_container_width=True, key="pr_solve_mar"):
            if sell == 0.0:
                st.error("Selling Price cannot be zero when solving for Margin.")
            else:
                resolved_mar = ((sell - cost) / sell) * 100.0
                gp = sell - cost
                st.markdown(f"""
                <div class="ws-result">
                <b>Solved Gross Margin:</b><br/>
                MAR = {resolved_mar:,.4f}%<br/>
                Gross Profit = ${gp:,.2f}
                </div>
                """, unsafe_allow_html=True)


def _render_date():
    st.markdown('<p style="font-size:0.85em;color:#94A3B8;">💡 Compute the number of days between two dates using actual calendar (ACT) or standard 30/360 rules.</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        dt1 = st.date_input("Start Date (DT1)", value=datetime.date.today(), key="d_dt1")
    with c2:
        dt2 = st.date_input("End Date (DT2)", value=datetime.date.today() + datetime.timedelta(days=30), key="d_dt2")
        
    if st.button("Compute Days Between Dates", type="primary", use_container_width=True, key="d_go"):
        try:
            act_days = (dt2 - dt1).days
            
            y1, m1, d1 = dt1.year, dt1.month, dt1.day
            y2, m2, d2 = dt2.year, dt2.month, dt2.day
            
            if d1 == 31:
                d1 = 30
            if d2 == 31 and d1 >= 30:
                d2 = 30
                
            days_360 = 360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)
            
            r1, r2 = st.columns(2)
            with r1:
                st.metric("Actual Days (ACT)", f"{act_days} days")
            with r2:
                st.metric("30/360 Calendar Days", f"{days_360} days")
            st.info(f"📅 DT1 is a **{dt1.strftime('%A')}** and DT2 is a **{dt2.strftime('%A')}**.")
                
        except Exception as e:
            st.error(f"Error: {e}")


def _render_depr():
    st.markdown('<p style="font-size:0.85em;color:#94A3B8;">💡 Compute asset depreciation schedules for Straight Line (SL), Double Declining Balance (DB), or Sum-of-the-Years\' Digits (SYD).</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        cost = st.number_input("Asset Cost (CST)", value=10000.0, step=1000.0, format="%.2f", key="dep_cost")
        salvage = st.number_input("Salvage Value (SAL)", value=1000.0, step=500.0, format="%.2f", key="dep_salvage")
    with c2:
        life = st.number_input("Estimated Life (LIF, years)", value=5.0, step=1.0, min_value=1.0, format="%.0f", key="dep_life")
        method = st.selectbox("Depreciation Method", ["Straight Line (SL)", "Double Declining Balance (DB)", "Sum-of-the-Years' Digits (SYD)"], key="dep_method")
        
    if st.button("Generate Depreciation Schedule", type="primary", use_container_width=True, key="dep_go"):
        try:
            if cost < salvage:
                st.error("Asset Cost cannot be less than Salvage Value.")
                return
            
            rows = []
            life_int = int(life)
            
            if method == "Straight Line (SL)":
                base = cost - salvage
                annual = base / life_int
                cum = 0.0
                val = cost
                for t in range(1, life_int + 1):
                    dep = annual
                    cum += dep
                    end_val = cost - cum
                    rows.append({
                        "Year": t,
                        "Start Book Value": round(val, 2),
                        "Depreciation": round(dep, 2),
                        "Cumulative Dep.": round(cum, 2),
                        "End Book Value": round(end_val, 2)
                    })
                    val = end_val
            elif method == "Double Declining Balance (DB)":
                rate = 2.0 / life_int
                val = cost
                cum = 0.0
                for t in range(1, life_int + 1):
                    dep = val * rate
                    max_allowed = val - salvage
                    if dep > max_allowed:
                        dep = max_allowed
                    if dep < 0:
                        dep = 0.0
                    cum += dep
                    end_val = val - dep
                    rows.append({
                        "Year": t,
                        "Start Book Value": round(val, 2),
                        "Depreciation": round(dep, 2),
                        "Cumulative Dep.": round(cum, 2),
                        "End Book Value": round(end_val, 2)
                    })
                    val = end_val
            elif method == "Sum-of-the-Years' Digits (SYD)":
                base = cost - salvage
                syd_sum = life_int * (life_int + 1) / 2
                cum = 0.0
                val = cost
                for t in range(1, life_int + 1):
                    fraction = (life_int - t + 1) / syd_sum
                    cum += dep
                    end_val = cost - cum
                    rows.append({
                        "Year": t,
                        "Start Book Value": round(val, 2),
                        "Depreciation": round(dep, 2),
                        "Cumulative Dep.": round(cum, 2),
                        "End Book Value": round(end_val, 2)
                    })
                    val = end_val
                    
            df = pd.DataFrame(rows)
            st.subheader(f"Depreciation Schedule ({method})")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Plotly Chart
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["Year"],
                y=df["Depreciation"],
                name="Annual Depreciation",
                marker_color="#EF4444"
            ))
            fig.add_trace(go.Scatter(
                x=df["Year"],
                y=df["End Book Value"],
                name="Remaining Book Value",
                line=dict(color="#3B82F6", width=3, shape="spline"),
                yaxis="y2"
            ))
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=30, b=10),
                height=280,
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
                xaxis=dict(title="Year", tickmode="linear"),
                yaxis=dict(title="Annual Dep. ($)", side="left"),
                yaxis2=dict(title="Book Value ($)", side="right", overlaying="y", showgrid=False)
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            
        except Exception as e:
            st.error(f"Error: {e}")


def _render_brkevn():
    st.markdown('<p style="font-size:0.85em;color:#94A3B8;">💡 Cost-Volume-Profit (CVP) and Break-Even Analysis.</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fc = st.number_input("Fixed Cost (FC)", value=5000.0, step=500.0, format="%.2f", key="be_fc")
        vc = st.number_input("Variable Cost per unit (VC)", value=15.0, step=1.0, format="%.2f", key="be_vc")
        price = st.number_input("Price per unit (P)", value=25.0, step=1.0, format="%.2f", key="be_price")
    with c2:
        profit = st.number_input("Target Profit (PRO)", value=0.0, step=100.0, format="%.2f", key="be_profit")
        quantity = st.number_input("Quantity (Q)", value=500.0, step=50.0, format="%.1f", key="be_quantity")
        
    st.markdown("Solve for unknown variable (uses the other variables):")
    cols = st.columns(5)
    
    with cols[0]:
        if st.button("Solve FC", use_container_width=True, key="be_solve_fc"):
            solved = quantity * (price - vc) - profit
            st.markdown(f'<div class="ws-result">FC = ${solved:,.2f}</div>', unsafe_allow_html=True)
            
    with cols[1]:
        if st.button("Solve VC", use_container_width=True, key="be_solve_vc"):
            if quantity == 0:
                st.error("Quantity cannot be 0 when solving VC.")
            else:
                solved = price - (fc + profit) / quantity
                st.markdown(f'<div class="ws-result">VC = ${solved:,.2f}</div>', unsafe_allow_html=True)
                
    with cols[2]:
        if st.button("Solve Price", use_container_width=True, key="be_solve_price"):
            if quantity == 0:
                st.error("Quantity cannot be 0 when solving Price.")
            else:
                solved = (fc + profit) / quantity + vc
                st.markdown(f'<div class="ws-result">P = ${solved:,.2f}</div>', unsafe_allow_html=True)
                
    with cols[3]:
        if st.button("Solve Profit", use_container_width=True, key="be_solve_profit"):
            solved = quantity * (price - vc) - fc
            st.markdown(f'<div class="ws-result">PRO = ${solved:,.2f}</div>', unsafe_allow_html=True)
            
    with cols[4]:
        if st.button("Solve Q", use_container_width=True, key="be_solve_q"):
            if price <= vc:
                st.error("Price must be greater than Variable Cost to break even.")
            else:
                solved = (fc + profit) / (price - vc)
                st.markdown(f'<div class="ws-result">Q = {solved:,.1f} units</div>', unsafe_allow_html=True)
