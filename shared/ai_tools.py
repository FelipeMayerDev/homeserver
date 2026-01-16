import os
import time
import logging
from groq import Groq
from dotenv import load_dotenv
from serpapi import GoogleSearch
from random import randint
from openai import OpenAI
import base64
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


class Z_Ai:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("Z_AI_API_KEY"), base_url="https://api.z.ai/api/coding/paas/v4/")
        self.chat_model = "glm-4.7"
        self.vision_model = "glm-4.6v"

    def _download_image_as_base64(self, image_url: str) -> str:
        """Baixa a imagem de uma URL e retorna como base64."""
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image_base64 = base64.b64encode(response.content).decode('utf-8')

            # Detect content type from response or default to jpeg
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            if content_type.startswith('image/'):
                content_type = content_type.split('/')[1]

            return f"data:image/{content_type};base64,{image_base64}"
        except Exception as e:
            logging.error(f"Erro ao baixar imagem: {e}")
            raise

    def chat(self, mensagem_usuario, historico=None, image_url=None, image_base64=None):
        """
        Envia uma mensagem para a API e retorna a resposta.
        Se image_url for fornecido, baixa a imagem e converte para base64.
        Se image_base64 for fornecido, usa diretamente.
        """
        messages = []

        if historico:
            messages.extend(historico)

        # Process image: if URL provided, download and convert to base64
        processed_image = None
        if image_url and not image_base64:
            processed_image = self._download_image_as_base64(image_url)
        elif image_base64:
            processed_image = image_base64

        # Seleciona o modelo baseado na presença de imagem
        model = self.vision_model if processed_image else self.chat_model

        # Formata o conteúdo da mensagem
        if processed_image:
            content = [
                {"type": "text", "text": mensagem_usuario},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": processed_image
                    }
                }
            ]
        else:
            content = mensagem_usuario

        messages.append({"role": "user", "content": content})

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Erro ao chamar a API: {e}"


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
                model="llama-3.3-8b-instant",
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



GROQ_API = GroqAPI()
LM_STUDIO_API = LMStudioAPI()
GOOGLE_IMAGE_API = GoogleSearchAPI()
Z_AI_API = Z_Ai()
