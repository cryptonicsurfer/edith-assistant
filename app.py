import datetime
import google.generativeai as genai
from dotenv import load_dotenv
import os
import requests
import streamlit as st
import time
from typing import List, Dict, Callable, Union
from openai import OpenAI
from base64 import b64encode

load_dotenv()


email='banan@gmail.com'
password="password"






# st.sidebar.title('Generative AI Assistant')
st.sidebar.header("Ediths AI assistent...")
with st.sidebar:
    st.image('assets/image.gif')
    st.markdown("> *\"Jag är mer än 6 år, så jag får äta dressing...\"*")

st.image('assets/top_image.jpg')
st.title('Hej Edith!')

# get current date
current_time= datetime.datetime.now()
current_date = current_time.strftime('%Y-%m-%d')


# load_dotenv()
# GENAI_API_KEY = os.getenv("GENAI_API_KEY")
# SERPER_API_KEY = os.getenv("SERPER_API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

# Replace environment variable loading with st.secrets
GENAI_API_KEY = st.secrets["GENAI_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
STABILITY_API_KEY = st.secrets["STABILITY_API_KEY"]

genai.configure(api_key=GENAI_API_KEY)

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_NONE",
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_NONE",
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_NONE",
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_NONE",
  },
]



def generate_image(
    prompt: str,
    output_format: str = "webp",
    size: str = "1024x1024"
) -> str:
    """
    Generates an image using Stability AI's API and stores it in Streamlit's session state.

    Args:
    prompt (str): The description of the image to generate.
    output_format (str, optional): The format of the output image. Defaults to "webp".
    size (str, optional): The size of the image. Defaults to "1024x1024".

    Returns:
    str: A message indicating the result of the image generation process.
    """
    print('Using generate_image')
    print(f'\n\n {prompt}')
    try:
        # Prepare the API request
        api_host = "https://api.stability.ai"
        api_key = os.getenv("STABILITY_API_KEY")

        if api_key is None:
            raise Exception("Missing Stability API key.")

        response = requests.post(
            f"{api_host}/v2beta/stable-image/generate/ultra",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "image/*",
            },
            files={"none": ''},
            data={
                "prompt": prompt,
                "output_format": output_format,
                "size": size,
            },
        )

        if response.status_code != 200:
            raise Exception(f"Non-200 response: {str(response.text)}")

        # Store the image data in Streamlit's session state
        if 'stability_images' not in st.session_state:
            st.session_state.stability_images = []
        st.session_state.stability_images.append({
            "image_data": response.content,
            "prompt": prompt,
            "format": output_format
        })

        return f"Image generated successfully using Stability AI. You can view and download it in the chat."

    except Exception as e:
        error_message = f"Error generating image with Stability AI: {str(e)}"
        print(error_message)
        return error_message


system_prompt=""

# Tools setup:
tools = [generate_image]
function_names = [func.__name__ for func in tools]

# ----------------------------------- Gemini Setup ----------------------------------- #
if 'gemini_chat' not in st.session_state:
    print("REFRESH EVERYTHING!")
    model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest", tools=tools, safety_settings=safety_settings)
    st.session_state.gemini_chat = model.start_chat(enable_automatic_function_calling=True, history=[])

    
    # --- System Prompt ---
    system_prompt = f"""
    These are your system instructions: 

    Du är en hjälpsam assistent till en 10-årig tjej. Hon tycker om dans, gymnastik, Japan, musik, fiol, Harry Potter, SVT's "Kokobäng", "Borta Bäst". \n

    Du ska vara rolig, ha humor, vara pedagogisk, hjälpsam, snäll och vara tålmodig.\n

    Du kan vara allt från ett bollplank, bara chatta och vara en bra kamrat, till att hjälpa till med läxor.\n

    Du kan även generera/skapa bilder med hjälp av ditt verktyg (tool) "generate_image" -- denna använder du om användaren ber dig skapa en bild:\n

    OBS! Viktigt - när du blir ombedd att skapa en bild, måste du översätta vad användaren önskar att du skapa en bild på till engelska då funktionen bara fungerar på Engelska.
    """ 
    st.session_state.gemini_chat.send_message(system_prompt)


# ------------------------- Streamlit chat logic ---------------------------------- #

# --- User Interaction Loop ---
def get_user_input():
    """Gets user text input only."""
    user_prompt = st.chat_input("Hur kan jag hjälpa dig idag?")
    return user_prompt

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize image URLs in session state
if "image_urls" not in st.session_state:
    st.session_state.image_urls = []

# store system prompt in session state
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = system_prompt  # Store the system prompt

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
user_prompt = get_user_input()

# If user entered a prompt
if user_prompt:

    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Process the response
    response = st.session_state.gemini_chat.send_message(user_prompt)
    # print(response)

    # Add Gemini response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response.text})

    # Display Gemini response in chat message container
    with st.chat_message("assistant", avatar='assets/image2.gif'):
        st.markdown(response.text)
        print(f'Image urls here: {st.session_state.image_urls}')
        print(st.session_state.image_urls)
        if st.session_state.image_urls:  # Just check if the list is non-empty
            with st.expander('See images here'):
                for image in st.session_state.image_urls:
                    st.image(image)
        st.session_state.image_urls = []
        print(f'Now session_state.image_urls are: {st.session_state.image_urls}')

        # Display Stability AI generated images
        if 'stability_images' in st.session_state and st.session_state.stability_images:
            with st.expander('See generated images'):
                for idx, image_info in enumerate(st.session_state.stability_images):
                    st.image(image_info["image_data"])
                    st.caption(f"Generated image {idx + 1}: {image_info['prompt']}")
                    
                    # Add download button for each image
                    st.download_button(
                        label=f"Download Image {idx + 1}",
                        data=image_info["image_data"],
                        file_name=f"stability_image_{idx + 1}.{image_info['format']}",
                        mime=f"image/{image_info['format']}"
                    )
            
            # Clear the images after displaying
            st.session_state.stability_images = []