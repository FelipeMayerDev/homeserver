from telegraph.aio import Telegraph
from shared.x import tweet_to_html
import logging
import asyncio

logging.basicConfig(level=logging.INFO)

telegraph = Telegraph()

async def init_telegraph():
    acc = await telegraph.create_account(short_name="GustavoBraga")
    logging.info(f"Access token: {dir(acc)}")
    return telegraph

async def generate_telegraph(tweet_id):
    html = tweet_to_html(tweet_id)
    response = await telegraph.create_page(
        'Focky rola imensa',
        html_content=html
    )
    return response['url']


