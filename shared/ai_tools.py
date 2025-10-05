import os
from groq import Groq
from dotenv import load_dotenv
from serpapi import GoogleSearch
from random import randint
import ollama
import requests

load_dotenv()

class GroqAPI:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.free_whispers_models = ["whisper-large-v3", "distil-whisper-large-v3-en", "whisper-large-v3-turbo"]

    def chat(self, prompt):
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
            raise Exception("Rate limit exceeded")

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


class OllamaAPI:
    def __init__(self):
        self.client = ollama.Client(host=os.getenv("OLLAMA_HOST"))

    def is_avaiable(self):
        req = requests.get(f'{os.getenv("OLLAMA_HOST")}/api/tags')
        if req.status_code != 200:
            return False
        return True

    def chat(self, prompt):
        system="""
        Você é uma IA em um grupo de amigos que responde perguntas de forma clara e concisa.
        Responda na linguagem que for perguntado e não utilize tags html
        """
        try:
            response = self.client.chat(
                model='granite4:micro',
                messages=[
                    {
                        'role': 'system',
                        'content': system,
                    },
                    {
                        'role': 'user',
                        'content': prompt,
                    },
                ])
            return response['message']['content']
        except Exception as e:
            raise e


# Initialize API instances for export
GROQ_API = GroqAPI()
OLLAMA_API = OllamaAPI()
GOOGLE_IMAGE_API = GoogleSearchAPI()