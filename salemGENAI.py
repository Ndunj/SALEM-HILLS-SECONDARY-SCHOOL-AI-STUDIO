import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

# -----------------------------------------------------------------------------
# 1. Page Configuration & Title
# -----------------------------------------------------------------------------
st.set_page_config(page_title="SALEM GENAI", page_icon="🤖", layout="centered")
#st.title("SALEMHILLS AI")
# --- ADDED: Main Page Layout with Logo ---
col1, col2 = st.columns([1, 4]) # Creates a small column for the logo, larger for text

with col1:
    st.image("salemlogo.png", width=80) # Explicit width looks best for titles

with col2:
    st.title("SALEM HILLS INT'L SCHOOL AI Studio")
st.logo('salemlogo.png')
#st.caption("UGO'S AI FOR EDUCATION")

# -----------------------------------------------------------------------------
# 2. Sidebar Configuration
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("Configuration")

    # Securely input API key
    api_key_input = st.text_input("Enter Gemini API Key:", type="password", help="Get your key from Google AI Studio")

    st.divider()

    # Core Switcher: Text Chat vs. Image Generator
    app_mode = st.radio("Select App Mode:", ("💬 Text Chat", "🎨 Image Generator"))

    st.divider()

    if app_mode == "💬 Text Chat":
        st.subheader("Text Mode Settings")
        system_instruction = st.text_area(
            "System Instructions / AI Persona:",
            value="You are a helpful, expert educational assistant. Break down complex topics simply, use step-by-step reasoning, and format lists or sub-questions using lower-case Roman numerals (i, ii, iii)."
        )
    else:
        st.subheader("Image Mode Settings")
        aspect_ratio = st.selectbox(
 "Aspect Ratio:",
            ("1:1", "16:9", "9:16", "4:3", "3:4"),
            index=0
        )

    st.divider()
    if st.button("Clear App History / Cache"):
        st.session_state.messages = []
        st.rerun()

# Determine the API key to use
api_key = api_key_input if api_key_input else None

# -----------------------------------------------------------------------------
# 3. Initialize Single AI Client & Chat History
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

client = None
if api_key:
    try:
        # A single unified client for all developer operations
        client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    except Exception as e:
        st.error(f"Failed to initialize AI client: {e}")

# -----------------------------------------------------------------------------
# 4. Render Existing Chat History (Only displayed in Text Mode)
# -----------------------------------------------------------------------------
if app_mode == "💬 Text Chat":
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# -----------------------------------------------------------------------------
# 5. Handle User Input & Generation Logic
# -----------------------------------------------------------------------------
placeholder_text = "Describe the image you want to create..." if app_mode == "🎨 Image Generator" else "Ask me anything..."

if user_input := st.chat_input(placeholder_text):

    if not api_key:
        st.warning("Please provide a valid Gemini API Key in the sidebar to start.")
 if not api_key:
        st.warning("Please provide a valid Gemini API Key in the sidebar to start.")
        st.stop()

    # --- MODE A: TEXT CHAT MODE ---
    if app_mode == "💬 Text Chat":
        with st.chat_message("user"):
            st.markdown(user_input)

        st.session_state.messages.append({"role": "user", "content": user_input})

        formatted_history = []
        for msg in st.session_state.messages[:-1]:
            role_type = "user" if msg["role"] == "user" else "model"
            formatted_history.append(
                types.Content(role=role_type, parts=[types.Part.from_text(text=msg["content"])])
            )

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            try:
                chat = client.chats.create(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                    ),
                    history=formatted_history
                )
                response = chat.send_message(user_input)
                message_placeholder.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
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
