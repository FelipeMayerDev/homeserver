import tweepy
import os
import re
import html
from datetime import datetime
from dotenv import load_dotenv
import logging

load_dotenv()

X_TOKEN = os.getenv("X_BEARER_TOKEN")
API_KEY = os.getenv("X_API_KEY")
API_SECRET = os.getenv("X_API_SECRET")
ACCESS_TOKEN =  os.getenv("X_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

def get_x_tweet(tweet_id: str):
    if not tweet_id:
        return None

    logging.info(f"Fetching tweet {tweet_id} from X using user auth")

    client = tweepy.Client(
        bearer_token=X_TOKEN,
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )

    tweet = client.get_tweet(
        id=tweet_id,
        tweet_fields=["created_at", "text", "author_id", "public_metrics", "attachments"],
        expansions=["author_id", "attachments.media_keys"],
        user_fields=["username", "name", "profile_image_url"],
        media_fields=["url", "preview_image_url", "type"]
    )

    # Texto do tweet
    texto = tweet.data["text"]

    # Usuário (autor)
    autor = tweet.includes["users"][0]
    nome = autor["name"]
    arroba = "@" + autor["username"]

    # Imagens
    imagens = []
    if "media" in tweet.includes:
        for m in tweet.includes["media"]:
            if m["type"] == "photo":
                imagens.append(m["url"])

    return {
        "nome": nome,
        "arroba": arroba,
        "texto": texto,
        "imagens": imagens,
        "fonte_url": f"https://x.com/{arroba[1:]}/status/{tweet_id}",
    }

def tweet_to_html(tweet_id: str) -> str:
    logging.info(f"Converting tweet {tweet_id} to HTML")
    if "twitter.com" in tweet_id or "x.com" in tweet_id:
        tweet_id = tweet_id.split("/")[-1]
        tweet_id = tweet_id.split("?")[0]

    tweet = get_x_tweet(tweet_id)
    if not tweet:
        return ""
    return tweet_to_telegraph_html(tweet["nome"], tweet["arroba"], tweet["texto"], tweet["imagens"], tweet["fonte_url"])

def linkify(text: str) -> str:
    # URLs
    text = re.sub(r'(https?://\S+)', r'<a href="\1">\1</a>', text)
    # Menções @user
    text = re.sub(r'(?<!\w)@([A-Za-z0-9_]{1,15})', r'<a href="https://x.com/\1">@\1</a>', text)
    # Hashtags #tag
    text = re.sub(r'(?<!\w)#(\w+)', r'<a href="https://x.com/hashtag/\1">#\1</a>', text)
    return text

def tweet_to_telegraph_html(nome: str, arroba: str, texto: str, imagens: list[str] | None = None,
                            fonte_url: str | None = None, data: datetime | None = None) -> str:
    imagens = imagens or []
    data_str = f' · {data.strftime("%d/%m/%Y %H:%M")}' if data else ''
    fonte = f' • <a href="{html.escape(fonte_url)}">ver no X</a>' if fonte_url else ''

    # texto: escapa e aplica links, preserva quebras de linha
    safe = html.escape(texto)
    safe = linkify(safe)
    safe = safe.replace("\n", "<br>")

    parts = []
    # Título (Telegraph usa o "title" fora do conteúdo via API; aqui deixamos um h3 dentro também)
    parts.append(f'<h3>{html.escape(nome)}</h3>')
    parts.append(f'<p><em>{html.escape(arroba)}</em>{data_str}{fonte}</p>')
    parts.append(f'<p>{safe}</p>')

    # Imagens
    for url in imagens:
        parts.append(f'<figure><img src="{html.escape(url)}"/></figure>')

    # Rodapé opcional
    parts.append('<p>Fonte: X (Twitter)</p>')

    # Container final (Telegraph aceita tags básicas: h1–h4, p, img, figure, a, b, i/em, strong)
    html_out = "\n".join(parts)
    return html_out