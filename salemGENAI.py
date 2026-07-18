import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
from PIL import Image
import io
import json
import os
import sqlite3
import hashlib
from fpdf import FPDF 
import pypdf
import docx

# =============================================================================
# 1. Page Configuration & Custom Styles
# =============================================================================
st.set_page_config(page_title="SALEM GENAI", page_icon="🤖", layout="centered")

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
    .welcome-text {
        font-size: 15px;
        color: #4A4A4A;
        font-weight: 500;
        margin-bottom: -10px;
        padding-left: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. Database Initialization (Lightweight User Storage)
# =============================================================================
DB_FILE = "users.db"

def init_db():
    """Creates the users table if it doesn't already exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Helper to encrypt passwords securely before saving to database."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    """Inserts a new user into the database securely."""
    username = username.strip().lower()
    if not username or not password:
        return False, "Username and password cannot be empty."
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                  (username, hash_password(password)))
        conn.commit()
        return True, "Account created successfully! Please log in."
    except sqlite3.IntegrityError:
        return False, "Username already exists. Please choose another one."
    finally:
        conn.close()

def verify_user(username, password):
    """Checks credentials against the stored records."""
    username = username.strip().lower()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    
    if row and row[0] == hash_password(password):
        return True
    return False

# Trigger database generation setup
init_db()

# =============================================================================
# 3. Dynamic Authentication Portal Layout
# =============================================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

def show_auth_portal():
    """Renders a clean tabbed UI for Login vs Registration."""
    st.markdown("<h2 style='text-align: center;'>🏫 SALEM HILLS INT'L SCHOOL AI</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: grey;'>Authenticate or sign up below to enter the workspace.</p>", unsafe_allow_html=True)
    
    tab_login, tab_signup = st.tabs(["🔒 Log In", "📝 Sign Up / Register"])
    
    with tab_login:
        with st.form("login_form"):
            user_input = st.text_input("Username").strip()
            pass_input = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            
            if submit_login:
                if verify_user(user_input, pass_input):
                    st.session_state.authenticated = True
                    st.session_state.username = user_input.strip()
                    st.success("Access Granted! Loading your workspace...")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password. Please try again.")
                    
    with tab_signup:
        with st.form("signup_form"):
            new_user = st.text_input("Choose Username").strip()
            new_pass = st.text_input("Choose Password", type="password")
            confirm_pass = st.text_input("Confirm Password", type="password")
            submit_signup = st.form_submit_button("Create My Account", use_container_width=True)
            
            if submit_signup:
                if new_pass != confirm_pass:
                    st.error("Passwords do not match. Please verify.")
                elif len(new_pass) < 4:
                    st.error("Password must be at least 4 characters long.")
                else:
                    success, msg = create_user(new_user, new_pass)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

# Active Gateway Shield
if not st.session_state.authenticated:
    show_auth_portal()
    st.stop()

# =============================================================================
# 4. User-Isolated Persistent File History Helpers
# =============================================================================
# Force history filename to use lowercase variant to ensure consistency
HISTORY_FILE = f"query_history_{st.session_state.username.lower()}.txt"

def save_query_to_file(query_text: str):
    clean_query = query_text.replace("\n", " ").strip()
    if not clean_query:
        return
    existing = load_queries_from_file()
    if clean_query not in existing:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(clean_query + "\n")

def load_queries_from_file():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()][::-1]

def clear_file_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)

# =============================================================================
# Helper Functions (PDF, Extraction, Copy Engine)
# =============================================================================
def clean_text(text: str) -> str:
    replacements = {
        '\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'",  
        '\u2013': '-', '\u2014': '-', '\u2022': '*',                  
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_chat_pdf(messages) -> bytes:
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
# 5. Workspace Main Page Layout Setup
# =============================================================================
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

if "messages" not in st.session_state:
    st.session_state.messages = []
if "input_value" not in st.session_state:
    st.session_state.input_value = ""

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
# 6. Sidebar Panels (Workspace Mode)
# =============================================================================
with st.sidebar:
    st.markdown(f"👤 Account: **{st.session_state.username}**")
    
    if st.button("Log Out", type="secondary", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.messages = []
        st.session_state.input_value = ""
        st.rerun()
        
    st.divider()
    st.header("Configuration")
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
        persistent_prompts = load_queries_from_file()
        
        if persistent_prompts:
            for i, prompt in enumerate(persistent_prompts[:20]):
                short_display = prompt[:30] + "..." if len(prompt) > 30 else prompt
                if st.button(f"💬 {short_display}", key=f"hist_btn_{i}", use_container_width=True):
                    st.session_state.input_value = prompt
                    st.rerun()
        else:
            st.info("No queries saved yet.")
            
        st.divider()
        st.subheader("Export Conversation")
        has_messages = len(st.session_state.messages) > 0
        if st.download_button(label="📥 Download Chat as PDF", data=generate_chat_pdf(st.session_state.messages) if has_messages else b"", file_name="chat_transcript.pdf", mime="application/pdf", disabled=not has_messages):
            st.success("Log Transcribed!")

    st.divider()
    if st.button("Clear App History / Cache"):
        st.session_state.messages = []
        st.session_state.input_value = ""
        clear_file_history()
        st.rerun()

# =============================================================================
# 7. Application Core Context Router
# =============================================================================
if app_mode == "💬 Text Chat":
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
        if message["role"] == "user":
            raw_text = message["content"].split("\n\n")[-1] if "📄 *Attached file:" in message["content"] else message["content"]
            render_copy_button(raw_text, f"hist_{idx}")

    uploaded_doc = st.file_uploader("Attach a document (.txt, .pdf, or .docx)", type=["txt", "pdf", "docx"], label_visibility="collapsed")
    
    # --- DYNAMIC PERSONALIZED GREETING INJECTOR ---
    greeting_str = f"Hi, {st.session_state.username}, how do we begin today?"
    st.markdown(f'<p class="welcome-text">{greeting_str}</p>', unsafe_allow_html=True)
    
    user_input = st.chat_input("Ask SALEM anything...")

    if st.session_state.input_value and not user_input:
        user_input = st.session_state.input_value
        st.session_state.input_value = ""

    if user_input:
        if not api_key:
            st.warning("Please provide a valid Gemini API Key in the sidebar secrets configuration to start.")
            st.stop()
        
        save_query_to_file(user_input)
        
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
