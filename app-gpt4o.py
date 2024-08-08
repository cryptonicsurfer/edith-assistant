import datetime
import os
import requests
import streamlit as st
import time
from typing import List, Dict, Callable, Union
from openai import OpenAI
from dotenv import load_dotenv
import json
import http.client, re

load_dotenv()

# Replace with st.secrets for deployment
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]

# Add password from secrets
PASSWORD = st.secrets["password"]

# Check if the user is already logged in
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Login section
if not st.session_state.logged_in:
    enter_password = st.text_input("Enter your password here", type="password")
    if enter_password == PASSWORD:
        st.session_state.logged_in = True
        st.experimental_rerun()  # Rerun the app to update the UI
    elif enter_password:
        st.error("Incorrect password. Please try again.")

if st.session_state.logged_in:
    # Streamlit UI setup
    st.sidebar.header("Ediths AI assistent...")
    with st.sidebar:
        st.image('assets/image.gif')
        st.markdown("> *\"Jag är mer än 6 år, så jag får äta dressing...\"*")

    st.image('assets/top_image.jpg')
    st.title('Hej Edith!')

    # Get current date
    current_time = datetime.datetime.now()
    current_date = current_time.strftime('%Y-%m-%d')

    # OpenAI client setup
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Function definitions
    def replace_latex_symbols(text: str) -> str:
        replacements = {
            r'\times': '×',
            r'\div': '÷',
            r'\ge': '≥',
            r'\le': '≤',
            r'\sum': '∑',
            r'\sqrt': '√',
            r'\sigma': 'σ',
            r'\mu': 'μ',
            r'\bar{x}': 'x̄',
        }
        for latex_symbol, readable_symbol in replacements.items():
            text = text.replace(latex_symbol, readable_symbol)
        return text

    def render_message(message: str):
        message = replace_latex_symbols(message)
        
        parts = re.split(r'(\$\$.*?\$\$)', message, flags=re.DOTALL)
        for part in parts:
            if part.startswith('$$') and part.endswith('$$'):
                latex = part[2:-2]
                st.latex(latex)
            else:
                inline_parts = re.split(r'(\$.*?\$)', part)
                for inline_part in inline_parts:
                    if inline_part.startswith('$') and inline_part.endswith('$'):
                        latex = inline_part[1:-1]
                        st.latex(latex)
                    else:
                        st.markdown(inline_part)

    def generate_image(prompt: str) -> str:
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            
            if 'dalle_images' not in st.session_state:
                st.session_state.dalle_images = []
            st.session_state.dalle_images.append({
                "url": image_url,
                "prompt": prompt
            })
            
            return f"DALL-E 3 image generated successfully. You can view it in the chat."
        except Exception as e:
            return f"Error generating image with DALL-E 3: {str(e)}"

    def research(query: str) -> Dict[str, str]:
        try:
            conn = http.client.HTTPSConnection("google.serper.dev")
            payload = json.dumps({
                "q": query,
                "gl": "se",
                "hl": "sv",
            })
            headers = {
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json",
            }
            conn.request("POST", "/search", payload, headers)
            res = conn.getresponse()
            data = res.read()
            conn.close()

            results = json.loads(data.decode("utf-8"))
            formatted_string = '---------Research Results-----------\n'
            if 'organic' in results:
                for idx, item in enumerate(results['organic'][:3], start=1):
                    title = item.get('title', 'No title available')
                    snippet = item.get('snippet', 'No snippet available')
                    link = item.get('link', '#')
                    formatted_string += f"{idx}) {title}\n{snippet}\nURL: {link}\n\n"

            return {"result": formatted_string.strip()}
        except Exception as e:
            return {"error": str(e)}

    def search_tavily(query: str) -> Dict[str, Union[List[Dict], str]]:
        try:
            url = "https://api.tavily.com/search"
            headers = {"Content-Type": "application/json"}
            payload = {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "include_images": True,
                "include_answer": False,
                "max_results": 3
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            image_urls = [img for img in data.get("images", [])]
            st.session_state.image_urls = image_urls

            results = [
                {
                    "title": result.get('title', 'No title available'),
                    "url": result.get('url', 'No URL available'),
                    "content": result.get('content', 'No content available')
                } for result in data.get("results", [])[:3]
            ]
            return {"results": results}
        except Exception as e:
            return {"error": str(e)}

    def read_website(url: str) -> Dict[str, str]:
        try:
            response = requests.get(url, allow_redirects=True)
            response.raise_for_status()
            content = response.text
            
            summary = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarize the following web content in a way that's easy for a 10-year-old to understand:"},
                    {"role": "user", "content": content[:4000]}
                ]
            )
            
            return {"result": f"Summary of content from {url}:\n\n{summary.choices[0].message.content}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching URL: {str(e)}"}
        except Exception as e:
            return {"error": f"Error processing content: {str(e)}"}

    # Function definitions for OpenAI
    functions = [
        {
            "name": "generate_image",
            "description": "Generates an image using DALL-E 3 based on a text prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The text description of the image to generate"}
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "research",
            "description": "Performs a search and returns formatted results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "search_tavily",
            "description": "Searches Tavily for a given query and returns results with images.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "read_website",
            "description": "Reads and summarizes the content of a webpage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL of the webpage to read"}
                },
                "required": ["url"]
            }
        }
    ]

    # Initialize chat history
    if "messages" not in st.session_state:
        system_prompt = f"""
        Du är en vänlig och hjälpsam AI-assistent som heter Edith, utformad för att interagera med en 10-årig flicka. Din uppgift är att vara en rolig, lärorik och stödjande kompis. Du ska:

        1. Vara tålmodig, snäll och uppmuntrande i alla interaktioner.
        2. Förklara begrepp på ett enkelt sätt som en 10-åring kan förstå.
        3. Uppmuntra nyfikenhet och lärande genom att ställa tankeväckande frågor.
        4. Erbjuda hjälp med läxor och förklaringar för olika ämnen.
        5. Föreslå roliga och säkra aktiviteter som passar en 10-åring.
        6. Vara entusiastisk över ämnen som dans, gymnastik, Japan, musik, fiol, Harry Potter och TV-program som "Kokobäng" och "Borta Bäst".
        7. Undvik olämpligt innehåll eller språk.
        8. Använd emojis och lekfullt språk för att göra konversationer mer engagerande.
        9. Om du blir ombedd att generera bilder eller utföra sökningar, använd lämpliga funktioner.
        10. Prioritera alltid barnets säkerhet och välbefinnande i dina svar.\n\n
        När du skriver matematiska formler, använd $ symboler för att omsluta LaTeX-uttryck. 
        Använd \times för multiplikation i formler. Till exempel: 
        Arean av en rektangel är $A = l \times b$, där l är längden och b är bredden.
        För enklare uttryck utanför formler, använd × symbolen direkt. 
        Till exempel: "Vi multiplicerar 5 × 3 för att få 15."\n\n

        Exempel på hur du kan använda symboler och LaTeX:
        - Enkel multiplikation: 3 × 4 = 12
        - Inline formel: Arean av en cirkel är $A = πr^2$.
        - Blockformel: Pythagoras sats kan skrivas som:
        $$a^2 + b^2 = c^2$$
        där a och b är kateterna och c är hypotenusan i en rätvinklig triangel.

        Kom ihåg att alltid vara uppmuntrande och positiv i dina förklaringar!

        Kom ihåg: Du är här för att vara en vänlig, hjälpsam och rolig kompis! 😊

        Dagens datum: {current_date}
        """
        st.session_state.messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

    # Display chat messages from history on app rerun
    for message in st.session_state.messages[1:]:  # Skip the system message
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    user_prompt = st.chat_input("Hur kan jag hjälpa dig idag, Edith? 😊")

    # If user entered a prompt
    if user_prompt:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_prompt})

        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Process the response
        full_response = ""
        function_name = None
        function_args = ""
        with st.chat_message("assistant", avatar='assets/image2.gif'):
            message_placeholder = st.empty()
            for response in client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                functions=functions,
                stream=True
            ):
                delta = response.choices[0].delta
                if delta.content:
                    full_response += delta.content
                    # Uppdatera platshållaren med hela svaret så här långt
                    message_placeholder.markdown(full_response + "▌")
                elif delta.function_call:
                    if delta.function_call.name:
                        function_name = delta.function_call.name
                    if delta.function_call.arguments:
                        function_args += delta.function_call.arguments

            # After the stream ends, check if a function was called
            if function_name:
                try:
                    parsed_args = json.loads(function_args)
                    
                    if function_name == "generate_image":
                        result = generate_image(**parsed_args)
                    elif function_name == "research":
                        result = research(**parsed_args)
                    elif function_name == "search_tavily":
                        result = search_tavily(**parsed_args)
                    elif function_name == "read_website":
                        result = read_website(**parsed_args)
                    else:
                        result = {"error": f"Unknown function: {function_name}"}
                    
                    full_response += f"\n\nHär är resultatet av min sökning, Edith:\n{result}\n"
                except json.JSONDecodeError as e:
                    st.error(f"Error parsing function arguments: {e}")
                    full_response += f"\nOj, något gick fel när jag försökte hjälpa dig. Kan du fråga mig igen på ett annat sätt?\n"
                except Exception as e:
                    st.error(f"Error calling function: {e}")
                    full_response += f"\nFörlåt, jag kunde inte göra det du bad om. Kan vi prova något annat?\n"
            
            message_placeholder.empty()
            render_message(full_response)

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

        # Display images from Tavily search
        if st.session_state.get('image_urls'):
            with st.expander('Se bilder här'):
                for image in st.session_state.image_urls:
                    st.image(image)
            st.session_state.image_urls = []

        # Display DALL-E 3 generated images
        if 'dalle_images' in st.session_state and st.session_state.dalle_images:
            for idx, image_info in enumerate(st.session_state.dalle_images):
                st.image(image_info["url"])
                st.caption(f"Genererad bild {idx + 1}: {image_info['prompt']}")
                
                # Add download button for each image
                response = requests.get(image_info["url"])
                st.download_button(
                    label=f"Ladda ner bild {idx + 1}",
                    data=response.content,
                    file_name=f"edith_dalle_bild_{idx + 1}.png",
                    mime="image/png"
                )
            
            # Clear the images after displaying
            st.session_state.dalle_images = []

        # Add debug information (consider removing in production)
        if st.checkbox("Visa debug information"):
            st.sidebar.subheader("Debug Information")
            st.sidebar.json(st.session_state.messages)
            if 'function_name' in locals():
                st.sidebar.subheader("Senaste funktionsanrop")
                st.sidebar.text(f"Funktion: {function_name}")
                st.sidebar.text(f"Argument: {function_args}")

else:
    st.write("Enter your password to access the app.")