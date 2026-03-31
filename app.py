import streamlit as st
from openai import OpenAI
from PIL import Image
from fpdf import FPDF
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
        "a single U-shaped hanging garland that droops down in the center and curves up at both ends, "
        "like a traditional festive door toran. The garland hangs from two points at the top corners "
        "and sags naturally in the middle forming a smooth U curve."
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
    page_title="Bloom Braid Builder",
    page_icon="🌸",
    layout="wide",
)

# -----------------------------------
# Custom CSS
# -----------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], .stMarkdown, .stRadio, .stSelectbox,
    .stCheckbox, .stButton, .stFileUploader, .stDownloadButton {
        font-family: 'Poppins', sans-serif !important;
    }

    /* App background */
    .stApp {
        background: linear-gradient(160deg, #fff8f0 0%, #f0faf0 100%);
    }

    [data-testid="stAppViewBlockContainer"] {
        padding-top: 0 !important;
    }

    /* ── Header ── */
    .main-header {
        background: linear-gradient(135deg, #e65100 0%, #f57c00 45%, #43a047 100%);
        padding: 2.5rem 2rem 2rem;
        border-radius: 0 0 28px 28px;
        margin: -1rem -4rem 2rem -4rem;
        text-align: center;
        box-shadow: 0 6px 24px rgba(245,124,0,0.22);
        position: relative;
    }
    .bloom-shop-btn {
        position: absolute;
        top: 1rem;
        right: 1.5rem;
        background: rgba(255,255,255,0.18);
        color: #fff !important;
        text-decoration: none !important;
        padding: 0.4rem 1.1rem;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        border: 1.5px solid rgba(255,255,255,0.45);
        letter-spacing: 0.3px;
        transition: background 0.2s, transform 0.2s;
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
    }
    .bloom-shop-btn:hover {
        background: rgba(255,255,255,0.32);
        transform: translateY(-1px);
    }
    .main-header h1 {
        color: #fff;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0 0 0.4rem 0;
        letter-spacing: -0.5px;
        text-shadow: 0 2px 8px rgba(0,0,0,0.18);
    }
    .main-header p {
        color: rgba(255,255,255,0.92);
        font-size: 0.95rem;
        margin: 0;
        font-weight: 400;
        letter-spacing: 0.2px;
    }

    /* ── Section labels ── */
    .section-label {
        font-size: 0.95rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #f57c00;
        margin-bottom: 0.6rem;
    }

    /* ── Panel cards ── */
    .panel-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 1.25rem 1.4rem;
        box-shadow: 0 2px 14px rgba(0,0,0,0.07);
        margin-bottom: 1rem;
        border: 1px solid #fff3e0;
    }

    /* ── Radio pills ── */
    div[data-testid="stRadio"] > div {
        gap: 0.6rem;
    }
    div[data-testid="stRadio"] label {
        background: #f5f5f5;
        border-radius: 22px !important;
        padding: 0.45rem 1.3rem !important;
        border: 2px solid transparent !important;
        transition: all 0.2s ease;
        font-weight: 500;
    }
    div[data-testid="stRadio"] label:hover {
        background: #fff3e0;
        border-color: #ffb74d !important;
    }

    /* ── Selectbox ── */
    div[data-testid="stSelectbox"] > div > div {
        border-radius: 10px !important;
        border-color: #ffe0b2 !important;
    }

    /* ── Generate button ── */
    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #f57c00 0%, #e65100 100%) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        letter-spacing: 0.3px;
        padding: 0.65rem 1.5rem !important;
        box-shadow: 0 4px 16px rgba(245,124,0,0.35) !important;
        transition: all 0.25s ease !important;
    }
    div[data-testid="stButton"] > button:hover {
        box-shadow: 0 6px 22px rgba(245,124,0,0.48) !important;
        transform: translateY(-1px);
    }

    /* ── Download buttons ── */
    div[data-testid="stDownloadButton"] > button {
        border-radius: 10px !important;
        font-weight: 500 !important;
        border: 2px solid #e0e0e0 !important;
        transition: all 0.2s ease !important;
        background: #fff !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        border-color: #f57c00 !important;
        color: #f57c00 !important;
        background: #fff3e0 !important;
    }

    /* ── Result image ── */
    .generated-img img {
        border-radius: 14px;
        border: 1.5px solid #ffe0b2;
        box-shadow: 0 4px 18px rgba(0,0,0,0.09);
    }

    /* ── Placeholder ── */
    .output-placeholder {
        background: #fff;
        border: 2.5px dashed #ffe0b2;
        border-radius: 18px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 430px;
        text-align: center;
    }
    .output-placeholder .icon { font-size: 4rem; margin-bottom: 0.75rem; opacity: 0.55; }
    .output-placeholder .label { font-size: 1rem; font-weight: 600; color: #ccc; }
    .output-placeholder .hint  { font-size: 0.78rem; color: #ddd; margin-top: 0.3rem; }

    /* ── Flower count table ── */
    .flower-count-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 0.5rem;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    }
    .flower-count-table th {
        text-align: left;
        padding: 0.7rem 1rem;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #fff;
        background: linear-gradient(135deg, #f57c00, #e65100);
    }
    .flower-count-table th:last-child { text-align: center; }
    .flower-count-table td {
        padding: 0.65rem 1rem;
        font-size: 0.88rem;
        border-bottom: 1px solid #fff3e0;
        color: #444;
    }
    .flower-count-table tr:last-child td { border-bottom: none; }
    .flower-count-table tr:not(.total-row):hover td { background: #fff8f0; }
    .flower-count-table .count-badge {
        display: inline-block;
        background: linear-gradient(135deg, #43a047, #2e7d32);
        color: #fff;
        font-weight: 700;
        font-size: 0.78rem;
        padding: 0.2rem 0.65rem;
        border-radius: 20px;
        min-width: 1.8rem;
        text-align: center;
    }
    .flower-count-table .total-row td {
        font-weight: 700;
        font-size: 0.95rem;
        background: #fff3e0;
        border-top: 2px solid #f57c00;
        color: #e65100;
    }

    /* ── Flower spinner ── */
    @keyframes flowerFold {
        0%   { transform: rotate(0deg)   scale(1);    }
        25%  { transform: rotate(90deg)  scale(0.45); }
        50%  { transform: rotate(180deg) scale(1);    }
        75%  { transform: rotate(270deg) scale(0.45); }
        100% { transform: rotate(360deg) scale(1);    }
    }
    .flower-spinner-wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 430px;
    }
    .flower-spin {
        font-size: 5.5rem;
        display: inline-block;
        animation: flowerFold 1.4s ease-in-out infinite;
        transform-origin: center;
    }
    .flower-spin-label {
        margin-top: 1.2rem;
        font-size: 1.05rem;
        font-weight: 600;
        color: #f57c00;
        letter-spacing: 0.3px;
    }
    .flower-spin-sub {
        font-size: 0.78rem;
        color: #bbb;
        margin-top: 0.3rem;
    }

    /* ── Divider ── */
    hr { border-color: #fff3e0 !important; margin: 1rem 0 !important; }

    /* ── Success alert ── */
    div[data-testid="stAlert"] { border-radius: 10px !important; }

    /* ── Checkbox ── */
    div[data-testid="stCheckbox"] label { font-size: 0.9rem; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------
# Load API Key
# -----------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "Bloom Braid Builder", ln=True, align="C")
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
    '<a href="http://localhost:8502/index.html" target="_blank" class="bloom-shop-btn">🛍️ Bloom Shop</a>'
    "<h1>Bloom Braid Builder</h1>"
    "<p><b>AI Based System for Flower Recognition and Intelligent Garland Design</b></p>"
    "</div>",
    unsafe_allow_html=True,
)

# -----------------------------------
# Two-column layout
# -----------------------------------
left_col, spacer, right_col = st.columns([4, 0.5, 5])

# ============ LEFT PANEL — Inputs ============
with left_col:
    st.markdown('<div class="section-label">Type</div>', unsafe_allow_html=True)

    arrangement_type = st.radio(
        "What do you want to create?",
        ["Garland", "Bouquet"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown('<div class="section-label">Shape</div>', unsafe_allow_html=True)

    if arrangement_type == "Garland":
        shape = st.selectbox("Shape", list(GARLAND_SHAPES.keys()), label_visibility="collapsed")
    else:
        shape = st.selectbox("Shape", list(BOUQUET_SHAPES.keys()), label_visibility="collapsed")

    st.markdown("---")

    st.markdown('<div class="section-label">Options</div>', unsafe_allow_html=True)

    add_greenleaf = st.checkbox("Add green leaves between flowers", value=True)

    st.markdown("---")

    st.markdown('<div class="section-label">🌸 &nbsp;Flower Images</div>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:0.85rem; color:#aaa; margin-top:-0.25rem; margin-bottom:0.5rem;"><b>Upload up to 5 flower images, choose garland or bouquet, and generate</b></p>', unsafe_allow_html=True)

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

        st.markdown('<div class="section-label">Preview</div>', unsafe_allow_html=True)
        preview_cols = st.columns(min(len(uploaded_files), MAX_FLOWERS))
        for i, file in enumerate(uploaded_files):
            preview_cols[i].image(file, use_container_width=True)

    st.markdown("---")

    generate_clicked = st.button(
        f"✨ Generate {arrangement_type}",
        use_container_width=True,
    )

# ============ RIGHT PANEL — Output ============
with right_col:
    st.markdown('<div class="section-label">✨ &nbsp;Result</div>', unsafe_allow_html=True)

    if "result_image_bytes" not in st.session_state:
        st.session_state.result_image_bytes = None
    if "flower_counts" not in st.session_state:
        st.session_state.flower_counts = None

    top_slot = st.empty()

    if generate_clicked:
        if not uploaded_files:
            st.warning("Upload at least one flower image first.")
            st.stop()

        # Show flower fold animation while generating
        top_slot.markdown(
            '<div class="flower-spinner-wrap">'
            '<div class="flower-spin">🌼</div>'
            '<div class="flower-spin-label">Creating your arrangement…</div>'
            '<div class="flower-spin-sub">This may take a few seconds</div>'
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

        # Update animation for counting phase
        top_slot.markdown(
            '<div class="flower-spinner-wrap">'
            '<div class="flower-spin">🌸</div>'
            '<div class="flower-spin-label">Counting flowers…</div>'
            '<div class="flower-spin-sub">Analyzing the arrangement</div>'
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

        st.success("Generated successfully!")
        st.markdown('<div class="generated-img">', unsafe_allow_html=True)
        st.image(image, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Flower count table
        if st.session_state.flower_counts:
            st.markdown("---")
            st.markdown('<div class="section-label">📊 &nbsp;Flower Count</div>', unsafe_allow_html=True)

            total = 0
            table_html = '<table class="flower-count-table">'
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
        st.markdown("---")
        st.markdown('<div class="section-label">⬇️ &nbsp;Download</div>', unsafe_allow_html=True)

        dl_col1, dl_col2 = st.columns(2)

        with dl_col1:
            st.download_button(
                "⬇ Download PNG",
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
                "⬇ Download PDF",
                data=pdf_bytes,
                file_name="flower_arrangement.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    else:
        top_slot.markdown(
            '<div class="output-placeholder">'
            '<div class="icon">🌼</div>'
            '<div class="label">Your creation will appear here</div>'
            '<div class="hint">Upload flowers → Choose shape → Click Generate</div>'
            "</div>",
            unsafe_allow_html=True,
        )
