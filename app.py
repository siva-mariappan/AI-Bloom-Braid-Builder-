import streamlit as st
from PIL import Image
import base64
import io
import os
import json
import tempfile
import threading
import http.server
from dotenv import load_dotenv

# -----------------------------------
# Background static file server (serves index.html on port 8502)
# -----------------------------------
_HTML_PORT = 8502

class _ReusableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True

def _start_static_server():
    handler = http.server.SimpleHTTPRequestHandler
    try:
        server = _ReusableHTTPServer(("", _HTML_PORT), handler)
        server.serve_forever()
    except OSError:
        pass  # port already in use, skip

if "static_server_started" not in st.session_state:
    t = threading.Thread(target=_start_static_server, daemon=True)
    t.start()
    st.session_state.static_server_started = True

# -----------------------------------
# Config
# -----------------------------------
MAX_FLOWERS = 5

GARLAND_SHAPES = {
    "U Shape": (
        "A traditional South Indian wedding garland made of fresh flowers, arranged in a thick alternating spiral pattern. "
        "The garland is symmetrical, dense, and elegant, with tightly packed flowers forming bold spiral sections. "
        "Small green buds are placed between layers for natural contrast. "
        "Bottom of the garland has a decorative tassel made of flowers. "
        "Centered composition, isolated on a clean white background, studio lighting, soft shadows, "
        "realistic fresh flowers, highly detailed texture, professional product photography style, "
        "ultra realistic, 4K quality."
    ),
    "Straight": (
        "a single straight horizontal garland arranged in a perfectly straight line from left to right. "
        "All flowers are aligned along one horizontal row with equal spacing."
    ),
    "Heart Shape": (
        "a single heart-shaped garland where flowers are arranged to form the outline of a heart shape. "
        "The two bumps of the heart are at the top and the point is at the bottom."
    ),
    "Oval Shape": (
        "a single oval-shaped garland where flowers are arranged to form the outline of a vertical oval. "
        "The flowers follow the smooth elliptical curve evenly."
    ),
}

BOUQUET_SHAPES = {
    "Round Bouquet": (
        "a single classic round dome-shaped bouquet viewed from the top/front. "
        "Flowers are tightly packed in a symmetrical circular dome arrangement."
    ),
    "Cascade Bouquet": (
        "a single cascade (waterfall) bouquet where flowers flow downward from a central cluster at the top, "
        "trailing elegantly in a teardrop shape. Longer stems and trailing blooms at the bottom."
    ),
    "Hand-tied Bouquet": (
        "a single natural hand-tied bouquet with a loose, organic arrangement. "
        "Flowers are gathered together with visible stems at the bottom tied with a ribbon or twine."
    ),
}

GREENLEAF_PROMPT = (
    "Add lush realistic green leaves (such as eucalyptus, fern, or ruscus) between and around the flowers "
    "to fill gaps and enhance the design. The leaves should look natural and complement the flowers."
)

NO_GREENLEAF_PROMPT = (
    "Do NOT add any green leaves or foliage. Only flowers and the connecting thread/stem should be visible."
)

st.set_page_config(
    page_title="Bloom Builder",
    page_icon="🌸",
    layout="wide",
)

# -----------------------------------
# Orange Theme CSS
# -----------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

    /* ── Reset & Base ── */
    html, body, [class*="css"], .stMarkdown, .stRadio, .stSelectbox,
    .stCheckbox, .stButton, .stFileUploader, .stDownloadButton,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stRadio"] label,
    div[data-testid="stCheckbox"] label p {
        font-family: 'Poppins', sans-serif !important;
    }

    .stApp {
        background: linear-gradient(170deg, #fff8f0 0%, #fff4e8 40%, #fff9f2 100%);
    }

    [data-testid="stAppViewBlockContainer"] {
        padding-top: 0 !important;
        max-width: 1320px;
    }

    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    header[data-testid="stHeader"],
    .stDeployButton {
        display: none !important;
        height: 0 !important;
        visibility: hidden !important;
    }

    /* ── Header ── */
    .main-header {
        background: linear-gradient(135deg, #e65100 0%, #f57c00 40%, #ff9800 70%, #ffb74d 100%);
        padding: 2.2rem 2.5rem 2rem;
        margin: -1rem -4rem 2rem -4rem;
        border-radius: 0 0 24px 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        position: relative;
        box-shadow: 0 8px 32px rgba(230,81,0,0.22), 0 2px 8px rgba(245,124,0,0.15);
    }
    .header-left {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .header-icon {
        width: 52px;
        height: 52px;
        border-radius: 16px;
        background: rgba(255,255,255,0.22);
        backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.6rem;
        border: 1.5px solid rgba(255,255,255,0.3);
    }
    .header-text h1 {
        font-size: 1.6rem;
        font-weight: 700;
        color: #fff;
        margin: 0;
        letter-spacing: -0.3px;
        line-height: 1.2;
        text-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }
    .header-text p {
        font-size: 0.82rem;
        color: rgba(255,255,255,0.88);
        margin: 0.2rem 0 0 0;
        font-weight: 400;
        letter-spacing: 0.2px;
    }
    .bloom-shop-btn {
        background: rgba(255,255,255,0.2);
        backdrop-filter: blur(8px);
        color: #fff !important;
        text-decoration: none !important;
        padding: 0.85rem 2.2rem;
        border-radius: 14px;
        font-size: 1.05rem;
        font-weight: 600;
        letter-spacing: 0.3px;
        transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
        display: inline-flex;
        align-items: center;
        gap: 0.55rem;
        border: 1.5px solid rgba(255,255,255,0.35);
    }
    .bloom-shop-btn:hover {
        background: rgba(255,255,255,0.35);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }

    /* ── Section labels ── */
    .section-label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: #e65100;
        margin-bottom: 0.7rem;
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }
    .section-label .dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: linear-gradient(135deg, #ff9800, #e65100);
        display: inline-block;
    }

    /* ── Left column wrapper ── */
    .left-panel-wrap {
        background: #ffffff;
        border-radius: 20px;
        padding: 1.75rem;
        border: 1px solid #ffe0b2;
        box-shadow: 0 2px 12px rgba(245,124,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
    }

    /* ── Radio pills ── */
    div[data-testid="stRadio"] > div {
        gap: 0.55rem;
        flex-direction: row;
    }
    div[data-testid="stRadio"] > div > label {
        background: #fff8f0 !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.5rem !important;
        border: 2px solid #ffe0b2 !important;
        transition: all 0.25s cubic-bezier(0.4,0,0.2,1) !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        color: #bf360c !important;
        cursor: pointer;
    }
    div[data-testid="stRadio"] > div > label:hover {
        background: #fff3e0 !important;
        border-color: #ffb74d !important;
        color: #e65100 !important;
    }
    div[data-testid="stRadio"] > div > label[data-checked="true"],
    div[data-testid="stRadio"] > div > label[aria-checked="true"] {
        background: linear-gradient(135deg, #fff3e0, #ffe0b2) !important;
        border-color: #f57c00 !important;
        color: #e65100 !important;
        font-weight: 600 !important;
        box-shadow: 0 3px 12px rgba(245,124,0,0.18) !important;
    }

    /* ── Selectbox ── */
    div[data-testid="stSelectbox"] > div > div {
        border-radius: 12px !important;
        border-color: #ffe0b2 !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stSelectbox"] > div > div:hover {
        border-color: #ffb74d !important;
    }
    div[data-testid="stSelectbox"] > div > div:focus-within {
        border-color: #f57c00 !important;
        box-shadow: 0 0 0 3px rgba(245,124,0,0.12) !important;
    }

    /* ── Generate button ── */
    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #f57c00 0%, #e65100 100%) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.3px;
        padding: 0.8rem 1.5rem !important;
        box-shadow: 0 4px 18px rgba(245,124,0,0.32) !important;
        transition: all 0.3s cubic-bezier(0.4,0,0.2,1) !important;
        position: relative;
        overflow: hidden;
    }
    div[data-testid="stButton"] > button:hover {
        background: linear-gradient(135deg, #e65100 0%, #bf360c 100%) !important;
        box-shadow: 0 8px 28px rgba(230,81,0,0.4) !important;
        transform: translateY(-2px) !important;
    }
    div[data-testid="stButton"] > button:active {
        transform: translateY(0) !important;
        box-shadow: 0 3px 12px rgba(245,124,0,0.3) !important;
    }

    /* ── Download buttons ── */
    div[data-testid="stDownloadButton"] > button {
        border-radius: 12px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        border: 2px solid #ffe0b2 !important;
        transition: all 0.25s cubic-bezier(0.4,0,0.2,1) !important;
        background: #fff !important;
        color: #e65100 !important;
        padding: 0.6rem 1rem !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        border-color: #f57c00 !important;
        color: #fff !important;
        background: linear-gradient(135deg, #f57c00, #e65100) !important;
        box-shadow: 0 4px 16px rgba(245,124,0,0.25) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Result image ── */
    .generated-img img {
        border-radius: 16px;
        border: 2px solid #ffe0b2;
        box-shadow: 0 4px 24px rgba(245,124,0,0.1);
        transition: all 0.3s ease;
    }
    .generated-img img:hover {
        box-shadow: 0 8px 36px rgba(245,124,0,0.18);
        border-color: #ffb74d;
    }

    /* ── Placeholder ── */
    .output-placeholder {
        background: #fff;
        border: 2.5px dashed #ffcc80;
        border-radius: 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 480px;
        text-align: center;
        transition: all 0.3s ease;
    }
    .output-placeholder:hover {
        border-color: #ffb74d;
        background: #fffaf5;
    }
    @keyframes blink-rotate {
        0%   { transform: rotate(0deg);   opacity: 1;   }
        25%  { transform: rotate(90deg);  opacity: 0.4; }
        50%  { transform: rotate(180deg); opacity: 1;   }
        75%  { transform: rotate(270deg); opacity: 0.4; }
        100% { transform: rotate(360deg); opacity: 1;   }
    }
    .output-placeholder .ph-icon {
        width: 76px;
        height: 76px;
        border-radius: 20px;
        background: linear-gradient(135deg, #fff3e0, #ffe0b2);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.2rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 16px rgba(245,124,0,0.1);
    }
    .output-placeholder .ph-label {
        font-size: 0.95rem;
        font-weight: 600;
        color: #bf360c;
        margin-bottom: 0.4rem;
    }
    .output-placeholder .ph-hint {
        font-size: 0.78rem;
        color: #e65100;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .output-placeholder .ph-hint .step {
        background: linear-gradient(135deg, #fff3e0, #ffe0b2);
        padding: 0.25rem 0.7rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.72rem;
        color: #e65100;
        border: 1px solid #ffcc80;
    }
    .output-placeholder .ph-hint .arrow {
        color: #ffb74d;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* ── Flower count table ── */
    .flower-count-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin-top: 0.5rem;
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid #ffe0b2;
        box-shadow: 0 2px 12px rgba(245,124,0,0.06);
    }
    .flower-count-table th {
        text-align: left;
        padding: 0.85rem 1.1rem;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #fff;
        background: linear-gradient(135deg, #f57c00, #e65100);
    }
    .flower-count-table th:last-child { text-align: center; }
    .flower-count-table td {
        padding: 0.75rem 1.1rem;
        font-size: 0.88rem;
        border-bottom: 1px solid #fff3e0;
        color: #4e342e;
        font-weight: 450;
        transition: background 0.2s ease;
    }
    .flower-count-table tr:last-child td { border-bottom: none; }
    .flower-count-table tr:not(.total-row):hover td { background: #fff8f0; }
    .flower-count-table .count-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #ff9800, #e65100);
        color: #fff;
        font-weight: 700;
        font-size: 0.78rem;
        padding: 0.25rem 0.8rem;
        border-radius: 20px;
        min-width: 2rem;
        box-shadow: 0 2px 6px rgba(245,124,0,0.2);
    }
    .flower-count-table .total-row td {
        font-weight: 700;
        font-size: 0.95rem;
        background: #fff3e0;
        border-top: 2px solid #f57c00;
        color: #e65100;
    }

    /* ── Spinner ── */
    @keyframes orangePulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50%      { transform: scale(1.12); opacity: 0.75; }
    }
    @keyframes orangeDots {
        0%, 80%, 100% { opacity: 0.25; transform: scale(0.75); }
        40% { opacity: 1; transform: scale(1.1); }
    }
    @keyframes orangeGlow {
        0%, 100% { box-shadow: 0 4px 20px rgba(245,124,0,0.15); }
        50%      { box-shadow: 0 4px 30px rgba(245,124,0,0.3); }
    }
    .spinner-wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 480px;
        gap: 1rem;
    }
    .spinner-icon {
        width: 84px;
        height: 84px;
        border-radius: 24px;
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 50%, #ffcc80 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.5rem;
        animation: orangePulse 2s ease-in-out infinite, orangeGlow 2s ease-in-out infinite;
        border: 2px solid #ffcc80;
    }
    .spinner-icon span {
        display: inline-block;
        animation: blink-rotate 3s ease-in-out infinite;
    }
    .spinner-label {
        font-size: 1.05rem;
        font-weight: 600;
        color: #e65100;
        letter-spacing: -0.2px;
    }
    .spinner-dots {
        display: flex;
        gap: 8px;
        margin-top: -0.3rem;
    }
    .spinner-dots span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: linear-gradient(135deg, #ff9800, #e65100);
        animation: orangeDots 1.4s ease-in-out infinite;
    }
    .spinner-dots span:nth-child(2) { animation-delay: 0.2s; }
    .spinner-dots span:nth-child(3) { animation-delay: 0.4s; }
    .spinner-sub {
        font-size: 0.8rem;
        color: #bf360c;
        font-weight: 400;
        opacity: 0.7;
    }

    /* ── Success badge ── */
    .success-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: linear-gradient(135deg, #fff3e0, #ffe0b2);
        border: 1.5px solid #ffcc80;
        color: #e65100;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 0.55rem 1.1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 10px rgba(245,124,0,0.1);
    }
    .success-badge .check {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: linear-gradient(135deg, #ff9800, #e65100);
        color: #fff;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.68rem;
        font-weight: 700;
    }

    /* ── Divider ── */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #ffe0b2, transparent);
        margin: 1.1rem 0;
        border: none;
    }
    hr {
        border-color: #ffe0b2 !important;
        margin: 1rem 0 !important;
    }

    /* ── Alert ── */
    div[data-testid="stAlert"] {
        border-radius: 12px !important;
        font-size: 0.88rem !important;
    }

    /* ── Checkbox ── */
    div[data-testid="stCheckbox"] label {
        font-size: 0.88rem;
        font-weight: 500;
        color: #4e342e;
    }
    div[data-testid="stCheckbox"] label p {
        color: #4e342e !important;
    }

    /* ── File uploader ── */
    div[data-testid="stFileUploader"] > div {
        border-radius: 14px !important;
        border: 2px dashed #ffcc80 !important;
        transition: all 0.3s ease !important;
        background: #fffaf5 !important;
    }
    div[data-testid="stFileUploader"] > div:hover {
        border-color: #ffb74d !important;
        background: #fff3e0 !important;
    }

    /* ── Preview images ── */
    .preview-wrap img {
        border-radius: 12px;
        border: 2px solid #ffe0b2;
        box-shadow: 0 2px 10px rgba(245,124,0,0.08);
        transition: all 0.25s cubic-bezier(0.4,0,0.2,1);
    }
    .preview-wrap img:hover {
        transform: scale(1.04);
        box-shadow: 0 6px 20px rgba(245,124,0,0.16);
        border-color: #ffb74d;
    }

    /* ── Streamlit native overrides ── */
    [data-testid="stSidebar"] { display: none; }

    /* ── Download section ── */
    .download-section {
        background: linear-gradient(135deg, #fff8f0, #fff3e0);
        border-radius: 14px;
        padding: 1.25rem;
        border: 1px solid #ffe0b2;
        margin-top: 0.5rem;
    }

    /* ── Animations ── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(14px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-12px); }
        to   { opacity: 1; transform: translateX(0); }
    }
    .animate-in {
        animation: fadeInUp 0.5s cubic-bezier(0.4,0,0.2,1) forwards;
    }

    /* ── Step indicator ── */
    .step-indicator {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        margin-bottom: 0.65rem;
    }
    .step-num {
        width: 24px;
        height: 24px;
        border-radius: 8px;
        background: linear-gradient(135deg, #f57c00, #e65100);
        color: #fff;
        font-size: 0.7rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 8px rgba(245,124,0,0.2);
    }
    .step-text {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #e65100;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------
# Load API Key (cached — avoids re-init on every rerun)
# -----------------------------------
load_dotenv()

@st.cache_resource
def get_openai_client():
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

client = get_openai_client()


# -----------------------------------
# Helper: count flowers in generated image
# -----------------------------------
def count_flowers_in_image(image_bytes):
    """Use OpenAI Vision to count each flower type in the generated image."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise flower-counting assistant. "
                    "Your job is to count EVERY individual flower bloom in an image. "
                    "Be methodical: scan left-to-right, top-to-bottom. "
                    "Count each distinct flower head once. Do not skip partially visible flowers. "
                    "Do not count leaves, buds, or stems — only open flower blooms."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Count every individual flower bloom in this image carefully.\n\n"
                            "Step 1: Identify all flower types present (include color in name, e.g. 'Red Rose').\n"
                            "Step 2: For each type, count EVERY individual bloom one-by-one.\n"
                            "Step 3: Double-check your count.\n\n"
                            "Reply ONLY with valid JSON in this exact format, nothing else:\n"
                            '[{"name": "Flower Name", "count": 5}, {"name": "Another Flower", "count": 3}]'
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"},
                    },
                ],
            }
        ],
        max_tokens=300,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(raw)


# -----------------------------------
# Helper: build PDF with image + flower counts
# -----------------------------------
def build_pdf(image_bytes, flower_counts):
    """Generate a PDF containing the garland/bouquet image and flower count table."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "Bloom Builder", ln=True, align="C")
    pdf.ln(4)

    # Save image to temp file (fpdf needs a file path)
    # Convert to RGB JPEG since fpdf handles it reliably
    pil_img = Image.open(io.BytesIO(image_bytes))
    rgb_img = Image.new("RGB", pil_img.size, (255, 255, 255))
    rgb_img.paste(pil_img, mask=pil_img.split()[3] if pil_img.mode == "RGBA" else None)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        rgb_img.save(tmp, format="JPEG", quality=95)
        tmp_path = tmp.name

    # Center the image (page width 210, margins 10 each side => 190 usable)
    img_w = 140
    x = (210 - img_w) / 2
    pdf.image(tmp_path, x=x, w=img_w)
    os.unlink(tmp_path)

    pdf.ln(8)

    # Flower count table
    if flower_counts:
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Flower Count", ln=True)
        pdf.ln(2)

        # Table header
        col_w_name = 120
        col_w_count = 40
        table_x = (210 - col_w_name - col_w_count) / 2

        pdf.set_x(table_x)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(col_w_name, 9, "Flower", border="B", fill=True)
        pdf.cell(col_w_count, 9, "Count", border="B", align="C", fill=True)
        pdf.ln()

        # Table rows
        pdf.set_font("Helvetica", "", 11)
        total = 0
        for flower in flower_counts:
            name = flower.get("name", "Unknown")
            count = flower.get("count", 0)
            total += count
            pdf.set_x(table_x)
            pdf.cell(col_w_name, 8, name, border="B")
            pdf.cell(col_w_count, 8, str(count), border="B", align="C")
            pdf.ln()

        # Total row
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_x(table_x)
        pdf.cell(col_w_name, 10, "Total", border="T")
        pdf.cell(col_w_count, 10, str(total), border="T", align="C")
        pdf.ln()

    return bytes(pdf.output())


# -----------------------------------
# Header
# -----------------------------------
st.markdown(
    '<div class="main-header">'
    '  <div class="header-left">'
    '    <div class="header-icon">🌸</div>'
    '    <div class="header-text">'
    "      <h1>Bloom Builder</h1>"
    "      <p>AI-powered flower recognition & garland design</p>"
    "    </div>"
    "  </div>"
    '  <a href="http://localhost:8502/index.html" target="_blank" class="bloom-shop-btn">'
    "    🛍️ Bloom Shop"
    "  </a>"
    "</div>",
    unsafe_allow_html=True,
)

# -----------------------------------
# Two-column layout
# -----------------------------------
left_col, spacer, right_col = st.columns([4, 0.4, 5.6])

# ============ LEFT PANEL — Inputs ============
with left_col:
    st.markdown('<div class="left-panel-wrap">', unsafe_allow_html=True)

    # Step 1 — Type
    st.markdown(
        '<div class="step-indicator">'
        '<span class="step-num">1</span>'
        '<span class="step-text">Arrangement Type</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    arrangement_type = st.radio(
        "What do you want to create?",
        ["Garland", "Bouquet"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Step 2 — Shape
    st.markdown(
        '<div class="step-indicator">'
        '<span class="step-num">2</span>'
        '<span class="step-text">Shape</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    if arrangement_type == "Garland":
        shape = st.selectbox("Shape", list(GARLAND_SHAPES.keys()), label_visibility="collapsed")
    else:
        shape = st.selectbox("Shape", list(BOUQUET_SHAPES.keys()), label_visibility="collapsed")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Step 3 — Options
    st.markdown(
        '<div class="step-indicator">'
        '<span class="step-num">3</span>'
        '<span class="step-text">Options</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    add_greenleaf = st.checkbox("Add green leaves between flowers", value=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Step 4 — Upload
    st.markdown(
        '<div class="step-indicator">'
        '<span class="step-num">4</span>'
        '<span class="step-text">Flower Images</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-size:0.8rem; color:#bf360c; opacity:0.6; margin-top:-0.15rem; margin-bottom:0.6rem;">'
        'Upload up to 5 flower images (PNG, JPG)</p>',
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Upload Flower Images",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        if len(uploaded_files) > MAX_FLOWERS:
            st.error(f"Maximum {MAX_FLOWERS} flowers allowed.")
            st.stop()

        st.markdown(
            '<div class="section-label" style="margin-top:0.8rem;">'
            '<span class="dot"></span> Preview'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="preview-wrap">', unsafe_allow_html=True)
        preview_cols = st.columns(min(len(uploaded_files), MAX_FLOWERS))
        for i, file in enumerate(uploaded_files):
            preview_cols[i].image(file, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    generate_clicked = st.button(
        f"✨ Generate {arrangement_type}",
        use_container_width=True,
    )

    st.markdown('</div>', unsafe_allow_html=True)

# ============ RIGHT PANEL — Output ============
with right_col:
    st.markdown(
        '<div class="section-label">'
        '<span class="dot"></span> Result'
        '</div>',
        unsafe_allow_html=True,
    )

    if "result_image_bytes" not in st.session_state:
        st.session_state.result_image_bytes = None
    if "flower_counts" not in st.session_state:
        st.session_state.flower_counts = None

    top_slot = st.empty()

    if generate_clicked:
        if not uploaded_files:
            st.warning("Upload at least one flower image first.")
            st.stop()

        # Show modern spinner while generating
        top_slot.markdown(
            '<div class="spinner-wrap">'
            '  <div class="spinner-icon"><span>🌼</span></div>'
            '  <div class="spinner-label">Creating your arrangement</div>'
            '  <div class="spinner-dots"><span></span><span></span><span></span></div>'
            '  <div class="spinner-sub">This may take a few seconds</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        image_files = []
        for file in uploaded_files:
            file.seek(0)
            image_files.append(file)

        num_flowers = len(uploaded_files)
        leaf_instruction = GREENLEAF_PROMPT if add_greenleaf else NO_GREENLEAF_PROMPT

        if arrangement_type == "Garland":
            shape_desc = GARLAND_SHAPES[shape]
            prompt = f"""Generate exactly ONE realistic photographic flower garland.

Shape: {shape_desc}

Green leaves: {leaf_instruction}

CRITICAL — FLOWER RESTRICTION:
I have provided exactly {num_flowers} reference image(s). Each image shows ONE flower type.
You MUST use ONLY the EXACT flower type(s) visible in the provided reference images.
DO NOT add, invent, or substitute any other flower types, colors, or varieties.
If only 1 image is provided, the ENTIRE garland must use ONLY that one flower — every single flower must be an exact copy of the input flower in color, shape, and species.
If 2 images are provided, alternate ONLY those 2 types. No third type allowed.

Other rules:
1. There must be EXACTLY ONE garland — do NOT create multiple garlands or duplicate rows.
2. Alternate the flower types evenly along the garland in a repeating pattern.
3. Every flower must face forward, be evenly spaced, and be roughly the same size.
4. Connect flowers with a thin natural green thread or vine running behind them.
5. Photorealistic lighting, soft shadows, natural depth.
6. Transparent background (PNG). No other objects, no text, no extra decorations.
7. Center the garland in the frame with comfortable margins on all sides.
"""
        else:
            shape_desc = BOUQUET_SHAPES[shape]
            prompt = f"""Generate exactly ONE realistic photographic flower bouquet.

Style: {shape_desc}

Green leaves: {leaf_instruction}

CRITICAL — FLOWER RESTRICTION:
I have provided exactly {num_flowers} reference image(s). Each image shows ONE flower type.
You MUST use ONLY the EXACT flower type(s) visible in the provided reference images.
DO NOT add, invent, or substitute any other flower types, colors, or varieties.
If only 1 image is provided, the ENTIRE bouquet must use ONLY that one flower — every single flower must be an exact copy of the input flower in color, shape, and species.
If 2 images are provided, use ONLY those 2 types. No third type allowed.

Other rules:
1. There must be EXACTLY ONE bouquet — do NOT create multiple bouquets.
2. Mix the flower types evenly throughout the bouquet in a balanced arrangement.
3. Every flower must be clearly visible with natural orientation and sizing.
4. Photorealistic lighting, soft shadows, natural depth.
5. Transparent background (PNG). No other objects, no text, no extra decorations.
6. Center the bouquet in the frame with comfortable margins on all sides.
"""

        result = client.images.edit(
            model="gpt-image-1",
            image=image_files,
            prompt=prompt,
            size="1024x1024",
            background="transparent",
        )

        image_base64 = result.data[0].b64_json
        st.session_state.result_image_bytes = base64.b64decode(image_base64)

        # Update spinner for counting phase
        top_slot.markdown(
            '<div class="spinner-wrap">'
            '  <div class="spinner-icon"><span>🌸</span></div>'
            '  <div class="spinner-label">Counting flowers</div>'
            '  <div class="spinner-dots"><span></span><span></span><span></span></div>'
            '  <div class="spinner-sub">Analyzing your arrangement</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        try:
            st.session_state.flower_counts = count_flowers_in_image(
                st.session_state.result_image_bytes
            )
        except Exception:
            st.session_state.flower_counts = None

        top_slot.empty()

    # Display result
    if st.session_state.result_image_bytes:
        image = Image.open(io.BytesIO(st.session_state.result_image_bytes))

        st.markdown(
            '<div class="success-badge animate-in">'
            '<span class="check">&#10003;</span>'
            'Generated successfully'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="generated-img animate-in">', unsafe_allow_html=True)
        st.image(image, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Flower count table
        if st.session_state.flower_counts:
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="section-label animate-in">'
                '<span class="dot"></span> Flower Count'
                '</div>',
                unsafe_allow_html=True,
            )

            total = 0
            table_html = '<table class="flower-count-table animate-in">'
            table_html += "<tr><th>Flower</th><th style='text-align:center;'>Count</th></tr>"

            for flower in st.session_state.flower_counts:
                name = flower.get("name", "Unknown")
                count = flower.get("count", 0)
                total += count
                table_html += (
                    f"<tr><td>{name}</td>"
                    f'<td style="text-align:center;"><span class="count-badge">{count}</span></td></tr>'
                )

            table_html += (
                f'<tr class="total-row"><td>Total</td>'
                f'<td style="text-align:center;">{total}</td></tr>'
            )
            table_html += "</table>"

            st.markdown(table_html, unsafe_allow_html=True)

        # Download buttons
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-label">'
            '<span class="dot"></span> Download'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="download-section">', unsafe_allow_html=True)
        dl_col1, dl_col2 = st.columns(2)

        with dl_col1:
            st.download_button(
                "Download PNG",
                data=st.session_state.result_image_bytes,
                file_name="flower_arrangement.png",
                mime="image/png",
                use_container_width=True,
            )

        with dl_col2:
            pdf_bytes = build_pdf(
                st.session_state.result_image_bytes,
                st.session_state.flower_counts,
            )
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name="flower_arrangement.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        top_slot.markdown(
            '<div class="output-placeholder">'
            '  <div class="ph-icon">🌼</div>'
            '  <div class="ph-label">Your creation will appear here</div>'
            '  <div class="ph-hint">'
            '    <span class="step">Upload</span>'
            '    <span class="arrow">&#8594;</span>'
            '    <span class="step">Configure</span>'
            '    <span class="arrow">&#8594;</span>'
            '    <span class="step">Generate</span>'
            '  </div>'
            "</div>",
            unsafe_allow_html=True,
        )
