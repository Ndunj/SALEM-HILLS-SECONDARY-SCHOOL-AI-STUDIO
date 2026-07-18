import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
from PIL import Image
import io
from fpdf import FPDF 
import pypdf
import docx

# =============================================================================
# 1. Page Configuration & Title
# =============================================================================
st.set_page_config(page_title="SALEM GENAI", page_icon="🤖", layout="centered")

# --- CSS Styling for Layout Elements ---
st.markdown("""
    <style>
    /* Aligns the HTML container perfectly to the right side underneath chat messages */
    .copy-container-wrapper {
        display: flex;
        justify-content: flex-end;
        margin-top: -8px;
        margin-bottom: 10px;
    }
    /* Simple styling rule to cut off ultra-long prompt titles in the sidebar with ellipses (...) */
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
def clean_text_for_pdf(text: str) -> str:
    """Replaces common non-Latin-1 characters to prevent PDF generation errors."""
    replacements = {
        '\u201c': '"', '\u201d': '"',  
        '\u2018': "'", '\u2019': "'",  
        '\u2013': '-', '\u2014': '-',  
        '\u2022': '*',                  
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')


def generate_pdf(messages) -> bytes:
    """Generates a clean PDF containing only core material."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, txt="SALEM HILLS INT'L SCHOOL", ln=True, align="C")
    pdf.set_font("Helvetica", style="I", size=10)
    pdf.cell(0, 5, txt="AI Studio - Official Transcript", ln=True, align="C")
    pdf.ln(10)
    
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    noise_phrases = ["download chat as pdf", "look for the button", "in the sidebar on the left"]
    
    for msg in messages:
        content_lower = msg["content"].lower()
        if any(phrase in content_lower for phrase in noise_phrases) and len(msg["content"]) < 400:
            continue
            
        role = "Student / User" if msg["role"] == "user" else "AI Assistant"
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.cell(0, 8, txt=f"{role}:", ln=True)
        
        pdf.set_font("Helvetica", size=10)
        cleaned_content = clean_text_for_pdf(msg["content"])
        pdf.multi_cell(0, 5, txt=cleaned_content)
        pdf.ln(6)
        
    return bytes(pdf.output())


def extract_text_from_file(uploaded_file) -> str:
    """Extracts text content from uploaded text, PDF, or Word (.docx) documents."""
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
            return f"[Error reading PDF content: {e}]"
            
    elif uploaded_file.name.endswith('.docx'):
        try:
            doc = docx.Document(uploaded_file)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return "\n".join(text)
        except Exception as e:
            return f"[Error reading Word document: {e}]"
            
    return ""


def render_copy_button(text_to_copy: str, element_key: str):
    """Renders a small JavaScript-driven copy icon button aligned to the right."""
    safe_text = text_to_copy.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
    
    html_code = f"""
    <div style="display: flex; justify-content: flex-end; font-family: sans-serif;">
        <button onclick="copyToClipboard()" id="btn_{element_key}" style="
            background: none;
            border: none;
            color: #6c757d;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 4px;
            transition: all 0.2s;
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
            label.innerText = 'Copied!';
            btn.style.color = '#28a745';
            setTimeout(() => {{
                label.innerText = 'Copy Prompt';
                btn.style.color = '#6c757d';
            }}, 2000);
        }}).catch(err => {{
            console.error('Failed to copy: ', err);
        }});
    }}
    </script>
    """
    st.markdown('<div class="copy-container-wrapper">', unsafe_allow_html=True)
    components.html(html_code, height=30)
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# 2. Session State Initialization
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# Using a persistent placeholder text variable so history links can populate the text entry window
if "input_value" not in st.session_state:
    st.session_state.input_value = ""

# =============================================================================
# 3. Sidebar Configuration (Left Panel)
# =============================================================================
with st.sidebar:
    st.header("Configuration")
    app_mode = st.radio("Select App Mode:", ("💬 Text Chat",))
    st.divider()

    if app_mode == "💬 Text Chat":
        st.subheader("Text Mode Settings")
        system_instruction = st.text_area(
            "System Instructions / AI Persona:",
            value=(
                "You are a helpful, expert educational assistant. Break down complex topics simply, "
                "use step-by-step reasoning, and format lists or sub-questions using lower-case Roman numerals (i, ii, iii). "
                "\n\nIMPORTANT: If the user asks you to create, download, or export a PDF of your chat, "
                "cheerfully remind them that they can download the entire conversation right now as a professional PDF "
                "by clicking the 'Download Chat as PDF' button in the sidebar on the left!"
            )
        )
    st.divider()
    
    # --- INTERACTIVE QUERY HISTORY ZONE ---
    if app_mode == "💬 Text Chat":
        st.subheader("Query History")
        
        # Filter all historical messages submitted by the user
        user_prompts = []
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                # Strip out the file path formatting to get the clean prompt text string
                clean_string = msg["content"].split("\n\n")[-1] if "📄 *Attached file:" in msg["content"] else msg["content"]
                if clean_string not in user_prompts:
                    user_prompts.append(clean_string)
        
        if user_prompts:
            for i, prompt in enumerate(user_prompts):
                # Slice prompt text to 30 characters maximum to keep the layout tidy
                short_display = prompt[:30] + "..." if len(prompt) > 30 else prompt
                
                # Render history selections as individual buttons. Clicking one loads it into the entry widget.
                if st.button(f"💬 {short_display}", key=f"hist_btn_{i}", use_container_width=True):
                    st.session_state.input_value = prompt
                    st.rerun()
        else:
            st.info("No queries sent yet.")
            
        st.divider()

    if app_mode == "💬 Text Chat":
        st.subheader("Export Conversation")
        has_messages = len(st.session_state.messages) > 0
        try:
            pdf_bytes = generate_pdf(st.session_state.messages) if has_messages else b""
            st.download_button(
                label="📥 Download Chat as PDF",
                data=pdf_bytes,
                file_name="salem_hills_ai_transcript.pdf",
                mime="application/pdf",
                disabled=not has_messages,
                help="Start a chat first to download the transcript."
            )
        except Exception as e:
            st.error(f"Could not prepare PDF: {e}")
        st.divider()
        
    if st.button("Clear App History / Cache"):
        st.session_state.messages = []
        st.session_state.input_value = ""
        st.rerun()

# --- SECURE KEY HANDLING ---
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
# 4. Render Existing Chat History & Copy Icons
# =============================================================================
if app_mode == "💬 Text Chat":
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
        
        if message["role"] == "user":
            raw_text = message["content"].split("\n\n")[-1] if "📄 *Attached file:" in message["content"] else message["content"]
            render_copy_button(raw_text, f"hist_{idx}")

# =============================================================================
# 5. Handle User Input & Generation Logic
# =============================================================================
uploaded_doc = None
if app_mode == "💬 Text Chat":
    uploaded_doc = st.file_uploader(
        "Attach a document (.txt, .pdf, or .docx)", 
        type=["txt", "pdf", "docx"], 
        label_visibility="collapsed"
    )

# Use dynamic context placeholder configuration to feed history selection straight to input
placeholder_text = "Ask SALEM anything..."
user_input = st.chat_input(placeholder_text, key="chat_input_box")

# Handle text selection activation routing when history items are clicked
if st.session_state.input_value and not user_input:
    user_input = st.session_state.input_value
    # Instantly clear values out so the interface doesn't get locked permanently into this historical selection loop
    st.session_state.input_value = ""

if user_input:
    if not api_key:
        st.warning("Please provide a valid Gemini API Key in the sidebar secrets configuration to start.")
        st.stop()

    doc_text = ""
    if uploaded_doc is not None:
        with st.spinner("Extracting content from file..."):
            doc_text = extract_text_from_file(uploaded_doc)
    
    full_prompt = user_input
    display_prompt = user_input
    if doc_text:
        full_prompt = f"User Message: {user_input}\n\nAttached Document Content:\n{doc_text}"
        display_prompt = f"📄 *Attached file: {uploaded_doc.name}*\n\n{user_input}"

    if app_mode == "💬 Text Chat":
        with st.chat_message("user"):
            st.markdown(display_prompt)
        
        render_copy_button(user_input, "live_new")
        st.session_state.messages.append({"role": "user", "content": display_prompt})

        formatted_history = []
        for msg in st.session_state.messages[:-1]:
            role_type = "user" if msg["role"] == "user" else "model"
            formatted_history.append(
                types.Content(role=role_type, parts=[types.Part.from_text(text=msg["content"])])
            )

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            try:
                with st.spinner("Processing your response..."):
                    chat = client.chats.create(
                        model="gemini-2.5-flash",
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.7,
                        ),
                        history=formatted_history
                    )
                    response = chat.send_message(full_prompt)
                
                message_placeholder.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {e}")
