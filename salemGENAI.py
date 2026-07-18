import streamlit as st
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

# --- Main Page Layout with Logo ---
col1, col2 = st.columns([1, 4]) # Creates a small column for the logo, larger for text
with col1:
    try:
        st.image("salemlogo.png", width=80) # Explicit width looks best for titles
    except Exception:
        # Fallback if logo file is not locally present yet
        st.write("🏫")
with col2:
    st.title("SALEM HILLS INT'L SCHOOL AI")

try:
    st.logo('salemlogo.png')
except Exception:
    pass

# =============================================================================
# PDF Generation & Document Reading Helper Functions
# =============================================================================
def clean_text_for_pdf(text: str) -> str:
    """Replaces common non-Latin-1 characters to prevent PDF generation errors."""
    replacements = {
        '\u201c': '"', '\u201d': '"',  # Smart double quotes
        '\u2018': "'", '\u2019': "'",  # Smart single quotes
        '\u2013': '-', '\u2014': '-',  # En/Em dashes
        '\u2022': '*',                  # Bullet points
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    # Encode and decode back, replacing any remaining un-renderable characters with '?'
    return text.encode('latin-1', 'replace').decode('latin-1')


def generate_pdf(messages) -> bytes:
    """Generates a clean PDF containing only core material, filtering out chatbot meta-dialogue."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title / Header
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, txt="SALEM HILLS INT'L SCHOOL", ln=True, align="C")
    pdf.set_font("Helvetica", style="I", size=10)
    pdf.cell(0, 5, txt="AI Studio - Official Transcript", ln=True, align="C")
    pdf.ln(10)
    
    # Divider line
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # Phrasing signatures to filter out of the final document
    noise_phrases = [
        "download chat as pdf", 
        "look for the button", 
        "in the sidebar on the left", 
        "within this chat interface"
    ]
    
    for msg in messages:
        # Check if this specific block is mostly chatbot meta-dialogue about download instructions
        content_lower = msg["content"].lower()
        if any(phrase in content_lower for phrase in noise_phrases) and len(msg["content"]) < 400:
            # Skip rendering this message completely if it's just the AI explaining the sidebar button
            continue
            
        role = "Student / User" if msg["role"] == "user" else "AI Assistant"
        
        # Format Role Name
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.cell(0, 8, txt=f"{role}:", ln=True)
        
        # Format Message Content
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

# =============================================================================
# 2. Sidebar Configuration
# =============================================================================
with st.sidebar:
    st.header("Configuration")

    # Core Switcher: Text Chat vs. Image Generator
    app_mode = st.radio("Select App Mode:", ("💬 Text Chat",))#, "🎨 Image Generator"))

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
    else:
        st.subheader("Image Mode Settings")
        aspect_ratio = st.selectbox(
            "Aspect Ratio:",
            ("1:1", "16:9", "9:16", "4:3", "3:4"),
            index=0
        )

    st.divider()
    
    # --- DYNAMIC PDF DOWNLOAD BUTTON ---
    if app_mode == "💬 Text Chat":
        st.subheader("Export Conversation")
        # Check if we actually have messages to download
        has_messages = len(st.session_state.get("messages", [])) > 0
        
        try:
            # Only generate the PDF if there are active messages
            pdf_bytes = generate_pdf(st.session_state.messages) if has_messages else b""
            
            st.download_button(
                label="📥 Download Chat as PDF",
                data=pdf_bytes,
                file_name="salem_hills_ai_transcript.pdf",
                mime="application/pdf",
                disabled=not has_messages, # This gray-outs the button if empty!
                help="Start a chat first to download the transcript." if not has_messages else "Click to download this chat as a PDF"
            )
        except Exception as e:
            st.error(f"Could not prepare PDF: {e}")
        st.divider()
    if st.button("Clear App History / Cache"):
        st.session_state.messages = []
        st.rerun()

# --- SECURE KEY HANDLING ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = None

# =============================================================================
# 3. Initialize Single AI Client & Chat History
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

client = None
if api_key:
    try:
        # A single unified client for all developer operations
        client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    except Exception as e:
        st.error(f"Failed to initialize AI client: {e}")

# =============================================================================
# 4. Render Existing Chat History (Only displayed in Text Mode)
# =============================================================================
if app_mode == "💬 Text Chat":
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# =============================================================================
# 5. Handle User Input & Generation Logic
# =============================================================================
# Document Uploader Segment supporting .txt, .pdf, and .docx
uploaded_doc = None
if app_mode == "💬 Text Chat":
    uploaded_doc = st.file_uploader(
        "Attach a document (.txt, .pdf, or .docx) to your query:", 
        type=["txt", "pdf", "docx"], 
        label_visibility="collapsed"
    )

placeholder_text = "Describe the image you want to create..." if app_mode == "🎨 Image Generator" else "Ask SALEM anything..."
if user_input := st.chat_input(placeholder_text):

    if not api_key:
        st.warning("Please provide a valid Gemini API Key in the sidebar secrets configuration to start.")
        st.stop()

    # Process file text if a document is present
    doc_text = ""
    if uploaded_doc is not None:
        with st.spinner("Extracting content from file..."):
            doc_text = extract_text_from_file(uploaded_doc)
    
    # Combine user prompt text and document text if available
    full_prompt = user_input
    display_prompt = user_input
    if doc_text:
        full_prompt = f"User Message: {user_input}\n\nAttached Document Content:\n{doc_text}"
        display_prompt = f"📄 *Attached file: {uploaded_doc.name}*\n\n{user_input}"

    # --- MODE A: TEXT CHAT MODE ---
    if app_mode == "💬 Text Chat":
        with st.chat_message("user"):
            st.markdown(display_prompt)

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
                # Wrap the processing and API call in a spinner
                with st.spinner("Processing your response..."):
                    chat = client.chats.create(
                        model="gemini-2.5-flash",
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.7,
                        ),
                        history=formatted_history
                    )
                    # Send the full prompt containing document text to Gemini
                    response = chat.send_message(full_prompt)
                
                # Once the spinner block is exited, write the response and refresh
                message_placeholder.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                # Trigger quick rerun to refresh the sidebar so the PDF download button immediately detects the update
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {e}")

    # --- MODE B: NATIVE IMAGE GENERATION MODE ---
    elif app_mode == "🎨 Image Generator":
        with st.chat_message("user"):
            st.markdown(f"**Generate Image for:** *{user_input}*")

        with st.chat_message("assistant"):
            st.info("🎨 Generating your image via Gemini, please wait...")

            try:
                # Call Gemini's native image generation configuration
                response = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=user_input,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio=aspect_ratio
                        )
                    )
                )

                # Check parts for image payload return
                image_found = False
                for part in response.parts:
                    if part.inline_data:
                        image_bytes = part.inline_data.data
                        image = Image.open(io.BytesIO(image_bytes))
                        st.image(image, caption=f"Result for: '{user_input}'", use_container_width=True)
                        image_found = True

                if not image_found:
                    st.warning("No image payload returned. Check your description or content filters.")

            except Exception as e:
                st.error(f"Failed to generate image: {e}")
