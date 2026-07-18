import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
from PIL import Image
import io
import json
from fpdf import FPDF 
import pypdf
import docx
# from docx.shared import Inches, Pt
# from docx.oxml import OxmlElement, parse_xml
# from docx.oxml.ns import qn, nsdecls

# =============================================================================
# 1. Page Configuration & Title
# =============================================================================
st.set_page_config(page_title="SALEM GENAI", page_icon="🤖", layout="centered")

# --- CSS Styling for Layout Elements ---
st.markdown("""
    <style>
    .copy-container-wrapper {
        display: flex;
        justify-content: flex-end;
        margin-top: -8px;
        margin-bottom: 10px;
    }
    .stButton>button {
        text-overflow: ellipsis;
        white-space: nowrap;
        overflow: hidden;
    }
    </style>
""", unsafe_allow_html=True)

# --- Main Page Layout with Logo ---
col1, col2 = st.columns([1, 4]) 
with col1:
    try:
        st.image("salemlogo.png", width=80) 
    except Exception:
        st.write("🏫")
with col2:
    st.title("SALEM HILLS INT'L SCHOOL AI")

try:
    st.logo('salemlogo.png')
except Exception:
    pass

# =============================================================================
# Helper Functions (PDF, Extraction, Copy Engine)
# =============================================================================
def clean_text(text: str) -> str:
    """Replaces common non-Latin-1 characters to prevent PDF generation errors."""
    replacements = {
        '\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'",  
        '\u2013': '-', '\u2014': '-', '\u2022': '*',                  
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- Lesson Plan Helpers Commented Out ---
# def generate_lesson_plan_pdf(lp: dict) -> bytes:
#     ...
# def set_cell_background(cell, fill_hex):
#     ...
# def generate_lesson_plan_docx(lp: dict) -> bytes:
#     ...

def generate_chat_pdf(messages) -> bytes:
    """Generates a regular transcript conversation log PDF file."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.cell(0, 10, txt="SALEM HILLS INT'L SCHOOL CHAT LOG", ln=True, align="C")
    pdf.ln(5)
    
    for msg in messages:
        role = "Student / User" if msg["role"] == "user" else "AI Assistant"
        pdf.set_font("Helvetica", style="B", size=10)
        pdf.cell(0, 6, txt=f"{role}:", ln=True)
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 5, txt=clean_text(msg["content"]))
        pdf.ln(4)
    return bytes(pdf.output())

def extract_text_from_file(uploaded_file) -> str:
    """Extracts text strings from uploaded txt, pdf, and docx variants."""
    if uploaded_file.name.endswith('.txt'):
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.name.endswith('.pdf'):
        try:
            pdf_reader = pypdf.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception as e:
            return f"[Error: {e}]"
    elif uploaded_file.name.endswith('.docx'):
        try:
            doc = docx.Document(uploaded_file)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            return f"[Error: {e}]"
    return ""

def render_copy_button(text_to_copy: str, element_key: str):
    """Renders JavaScript powered clipboard functionality inside chat messages."""
    safe_text = text_to_copy.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
    html_code = f"""
    <div style="display: flex; justify-content: flex-end; font-family: sans-serif;">
        <button onclick="copyToClipboard()" id="btn_{element_key}" style="
            background: none; border: none; color: #6c757d; cursor: pointer;
            display: flex; align-items: center; gap: 4px; font-size: 12px;
            padding: 4px 8px; border-radius: 4px; transition: all 0.2s;
        " onmouseover="this.style.color='#000'; this.style.background='#f0f2f6'" 
           onmouseout="this.style.color='#6c757d'; this.style.background='none'">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            <span id="label_{element_key}">Copy Prompt</span>
        </button>
    </div>
    <script>
    function copyToClipboard() {{
        const text = `{safe_text}`;
        navigator.clipboard.writeText(text).then(() => {{
            const label = document.getElementById('label_{element_key}');
            const btn = document.getElementById('btn_{element_key}');
            label.innerText = 'Copied!'; btn.style.color = '#28a745';
            setTimeout(() => {{ label.innerText = 'Copy Prompt'; btn.style.color = '#6c757d'; }}, 2000);
        }});
    }}
    </script>
    """
    st.markdown('<div class="copy-container-wrapper">', unsafe_allow_html=True)
    components.html(html_code, height=30)
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# 3. Memory & Client Configurations
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "input_value" not in st.session_state:
    st.session_state.input_value = ""
# if "current_lesson_plan" not in st.session_state:
#     st.session_state.current_lesson_plan = None

if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = None

client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    except Exception as e:
        st.error(f"Failed to initialize AI client: {e}")

# =============================================================================
# 4. Sidebar Panels
# =============================================================================
with st.sidebar:
    st.header("Configuration")
    # Reduced mode option purely to Text Chat
    app_mode = st.radio("Select App Mode:", ("💬 Text Chat",))
    st.divider()

    if app_mode == "💬 Text Chat":
        st.subheader("Text Mode Settings")
        system_instruction = st.text_area(
            "System Instructions / AI Persona:",
            value="You are a helpful, expert educational assistant. Break down complex topics simply."
        )
        st.divider()
        st.subheader("Query History")
        user_prompts = []
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                clean_string = msg["content"].split("\n\n")[-1] if "📄 *Attached file:" in msg["content"] else msg["content"]
                if clean_string not in user_prompts:
                    user_prompts.append(clean_string)
        
        if user_prompts:
            for i, prompt in enumerate(user_prompts):
                short_display = prompt[:30] + "..." if len(prompt) > 30 else prompt
                if st.button(f"💬 {short_display}", key=f"hist_btn_{i}", use_container_width=True):
                    st.session_state.input_value = prompt
                    st.rerun()
        else:
            st.info("No queries sent yet.")
            
        st.divider()
        st.subheader("Export Conversation")
        has_messages = len(st.session_state.messages) > 0
        if st.download_button(label="📥 Download Chat as PDF", data=generate_chat_pdf(st.session_state.messages) if has_messages else b"", file_name="chat_transcript.pdf", mime="application/pdf", disabled=not has_messages):
            st.success("Log Transcribed!")
            
    # --- Lesson Plan Generator Sidebar Section Commented Out ---
    # elif app_mode == "📋 Lesson Plan Generator":
    #     ...

    st.divider()
    if st.button("Clear App History / Cache"):
        st.session_state.messages = []
        st.session_state.input_value = ""
        # st.session_state.current_lesson_plan = None
        st.rerun()

# =============================================================================
# 5. Application Core Context Router
# =============================================================================
if app_mode == "💬 Text Chat":
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
        if message["role"] == "user":
            raw_text = message["content"].split("\n\n")[-1] if "📄 *Attached file:" in message["content"] else message["content"]
            render_copy_button(raw_text, f"hist_{idx}")

    uploaded_doc = st.file_uploader("Attach a document (.txt, .pdf, or .docx)", type=["txt", "pdf", "docx"], label_visibility="collapsed")
    user_input = st.chat_input("Ask SALEM anything...")

    if st.session_state.input_value and not user_input:
        user_input = st.session_state.input_value
        st.session_state.input_value = ""

    if user_input:
        if not api_key:
            st.warning("Please provide a valid Gemini API Key in the sidebar secrets configuration to start.")
            st.stop()
        
        doc_text = ""
        if uploaded_doc is not None:
            with st.spinner("Extracting content..."):
                doc_text = extract_text_from_file(uploaded_doc)
        
        full_prompt = user_input
        display_prompt = user_input
        if doc_text:
            full_prompt = f"User Message: {user_input}\n\nAttached Document Content:\n{doc_text}"
            display_prompt = f"📄 *Attached file: {uploaded_doc.name}*\n\n{user_input}"

        with st.chat_message("user"):
            st.markdown(display_prompt)
        render_copy_button(user_input, "live_new")
        st.session_state.messages.append({"role": "user", "content": display_prompt})

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            try:
                with st.spinner("Processing..."):
                    chat = client.chats.create(
                        model="gemini-2.5-flash",
                        config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.7)
                    )
                    response = chat.send_message(full_prompt)
                message_placeholder.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- Lesson Plan Generator Core Screen Commented Out ---
# elif app_mode == "📋 Lesson Plan Generator":
#     ...
