import streamlit as st
from openai import OpenAI
from PIL import Image
from fpdf import FPDF
import base64
import io
import os
import json
import tempfile
from dotenv import load_dotenv

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
    .main-title {
        text-align: center;
        padding: 0.5rem 0 1.5rem 0;
        border-bottom: 2px solid #f0f2f6;
        margin-bottom: 1.5rem;
    }
    .main-title h1 {
        font-size: 2.2rem;
        margin-bottom: 0.25rem;
    }
    .main-title p {
        color: #888;
        font-size: 0.95rem;
    }

    [data-testid="stAppViewBlockContainer"] {
        padding-top: 1rem;
    }

    .section-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #999;
        margin-bottom: 0.75rem;
    }

    .output-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 400px;
        color: #bbb;
        text-align: center;
    }
    .output-placeholder .icon {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    .output-placeholder p {
        font-size: 0.9rem;
    }

    .generated-img img {
        border-radius: 12px;
        border: 1px solid #e0e0e0;
    }

    .stDownloadButton > button {
        width: 100%;
    }

    .flower-count-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 0.5rem;
    }
    .flower-count-table th {
        text-align: left;
        padding: 0.5rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #888;
        border-bottom: 2px solid #555;
    }
    .flower-count-table td {
        padding: 0.6rem 0.75rem;
        font-size: 0.9rem;
        border-bottom: 1px solid #444;
        color: inherit;
    }
    .flower-count-table tr:last-child td {
        border-bottom: none;
    }
    .flower-count-table .count-badge {
        display: inline-block;
        background: #2e7d32;
        color: #fff;
        font-weight: 700;
        font-size: 0.8rem;
        padding: 0.15rem 0.55rem;
        border-radius: 10px;
        min-width: 1.5rem;
        text-align: center;
    }
    .flower-count-table .total-row td {
        font-weight: 700;
        font-size: 0.95rem;
        border-top: 2px solid #555;
        padding-top: 0.7rem;
    }
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
    '<div class="main-title">'
    "<h1>🌸 Bloom Braid Builder</h1>"
    "<p><b>AI Based System for flower recognition and intelligent Garland Design</b></p>"
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

    st.markdown('<div class="section-label">Flower Images</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="section-label">Result</div>', unsafe_allow_html=True)

    if "result_image_bytes" not in st.session_state:
        st.session_state.result_image_bytes = None
    if "flower_counts" not in st.session_state:
        st.session_state.flower_counts = None

    if generate_clicked:
        if not uploaded_files:
            st.warning("Upload at least one flower image first.")
            st.stop()

        with st.spinner(f"Creating your {arrangement_type.lower()}..."):

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

        # Count flowers in the generated image
        with st.spinner("Counting flowers..."):
            try:
                st.session_state.flower_counts = count_flowers_in_image(
                    st.session_state.result_image_bytes
                )
            except Exception:
                st.session_state.flower_counts = None

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
            st.markdown('<div class="section-label">Flower Count</div>', unsafe_allow_html=True)

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
        st.markdown('<div class="section-label">Download</div>', unsafe_allow_html=True)

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
        st.markdown(
            '<div class="output-placeholder">'
            '<div class="icon">🌼</div>'
            "<p>Your generated image will appear here</p>"
            "</div>",
            unsafe_allow_html=True,
        )
