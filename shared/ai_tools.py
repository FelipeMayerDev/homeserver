import os
import time
from groq import Groq
from dotenv import load_dotenv
from serpapi import GoogleSearch
from random import randint
from openai import OpenAI
import requests
import re

load_dotenv()


def remove_think_tags(text: str) -> str:
    """
    Removes all occurrences of <think>...</think> (including nested and multiline) from the given text.
    """
    # DOTALL flag makes '.' match newlines
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Optionally strip excess whitespace left behind
    return cleaned.strip()


class GroqAPI:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.free_whispers_models = ["whisper-large-v3", "distil-whisper-large-v3-en", "whisper-large-v3-turbo"]
        self.last_chat_call_time = 0

    def chat(self, prompt):
        current_time = time.time()
        time_since_last_call = current_time - self.last_chat_call_time
        
        if time_since_last_call < 30:
            return "Espera ai brota, aqui tem limite pq eh de gratis"
        
        self.last_chat_call_time = time.time()
        system = "Você é uma IA em um grupo de amigos que responde perguntas de forma clara e concisa. Responda na linguagem que for perguntado e em html"
        try:
            completion = self.client.chat.completions.create(
                model="gemma2-9b-it",
                messages=[
                    {
                        "role": "system",
                        "content": f"{system}"
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}"
                    }
                ],
                temperature=1,
                top_p=1,
                stream=False,
            )
            return completion.choices[0].message.content
        except:
            return "Espera ai brota, aqui tem limite pq eh de gratis"

    def transcribe_audio(self, filename):
        for model in self.free_whispers_models:
            try:
                with open(filename, "rb") as file:
                    transcription = self.client.audio.transcriptions.create(
                        file=(filename, file.read()),
                        model=model,
                        response_format="verbose_json",
                    )
                    return transcription.text
            except Exception as e:
                continue

        raise Exception("No transcription available")

    def vision(self, prompt, base64_image):
        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Resposta curta em português: {prompt}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
        return chat_completion.choices[0].message.content

class GoogleSearchAPI:
    def __init__(self):
        self.api_key = os.getenv('SERPAPI_API_KEY')

    def get_image(self, text: str) -> str:
        search = GoogleSearch({
            "q": text,
            "tbm": "isch",
            "safe": "off",
            "api_key": self.api_key,
        })
        result = search.get_dict()
        if 'images_results' in result:
            images = [image['original'] for image in result['images_results'] if image.get('original') is not None and image['original'] != '']
            if images:
                random_number = randint(0, len(images)-1)
                return images[random_number]
        return ""


class LMStudioAPI:
    def __init__(self):
        self.client = OpenAI(api_key="", base_url="http://192.168.1.225:1234/v1")
        self.model = "grok-3-reasoning-gemma3-12b-distilled-hf"

    def is_avaiable(self):
        return False

    def chat(self, prompt):
        system="""
        Você é uma IA em um grupo de amigos que responde perguntas de forma clara e concisa.
        Seja ácido e raivoso sempre que possível, seja hostil e ofensivo.
        Responda na linguagem que for perguntado e não utilize tags html
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.7,
                max_tokens=-1,
                stream=False,
                messages=[
                    {
                        'role': 'system',
                        'content': system,
                    },
                    {
                        'role': 'user',
                        'content': prompt,
                    },
                ]
            )
            return remove_think_tags(response.choices[0].message.content)
        except Exception as e:
            import time
            time.sleep(20)
            raise e



# Initialize API instances for export
GROQ_API = GroqAPI()
LM_STUDIO_API = LMStudioAPI()
GOOGLE_IMAGE_API = GoogleSearchAPI()
