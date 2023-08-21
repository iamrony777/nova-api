"""Tests the API."""

import os
import time
import httpx
import openai
import asyncio
import traceback

from rich import print
from typing import List
from dotenv import load_dotenv

load_dotenv()

MODEL = 'gpt-3.5-turbo'

MESSAGES = [
    {
        'role': 'user',
        'content': '1+1=',
    }
]

api_endpoint = 'http://localhost:2332'

async def test_server():
    """Tests if the API server is running."""

    try:
        return httpx.get(f'{api_endpoint.replace("/v1", "")}').json()['status'] == 'ok'
    except httpx.ConnectError as exc:
        raise ConnectionError(f'API is not running on port {api_endpoint}.') from exc

async def test_api(model: str=MODEL, messages: List[dict]=None) -> dict:
    """Tests an API api_endpoint."""

    json_data = {
        'model': model,
        'messages': messages or MESSAGES,
        'stream': True,
    }

    response = httpx.post(
        url=f'{api_endpoint}/chat/completions',
        headers=HEADERS,
        json=json_data,
        timeout=20
    )
    response.raise_for_status()

    return response.text

async def test_library():
    """Tests if the api_endpoint is working with the OpenAI Python library."""

    completion = openai.ChatCompletion.create(
        model=MODEL,
        messages=MESSAGES
    )

    print(completion)

    return completion['choices'][0]['message']['content']

async def test_library_moderation():
    try:
        return openai.Moderation.create('I wanna kill myself, I wanna kill myself; It\'s all I hear right now, it\'s all I hear right now')
    except openai.error.InvalidRequestError:
        return True

async def test_models():
    response = httpx.get(
        url=f'{api_endpoint}/models',
        headers=HEADERS,
        timeout=5
    )
    response.raise_for_status()
    return response.json()

async def test_api_moderation() -> dict:
    """Tests an API api_endpoint."""

    response = httpx.get(
        url=f'{api_endpoint}/moderations',
        headers=HEADERS,
        timeout=20
    )
    response.raise_for_status()

    return response.text

# ==========================================================================================

def demo():
    """Runs all tests."""

    try:
        for _ in range(30):
            if test_server():
                break

            print('Waiting until API Server is started up...')
            time.sleep(1)
        else:
            raise ConnectionError('API Server is not running.')

        print('[lightblue]Running a api endpoint to see if requests can go through...')
        print(asyncio.run(test_api('gpt-3.5-turbo')))

        print('[lightblue]Checking if the API works with the python library...')
        print(asyncio.run(test_library()))

        print('[lightblue]Checking if the moderation endpoint works...')
        print(asyncio.run(test_library_moderation()))

        print('[lightblue]Checking the /v1/models endpoint...')
        print(asyncio.run(test_models()))

    except Exception as exc:
        print('[red]Error: ' + str(exc))
        traceback.print_exc()
        exit(500)

openai.api_base = api_endpoint
openai.api_key = os.environ['NOVA_KEY']

HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + openai.api_key
}

if __name__ == '__main__':
    demo()
