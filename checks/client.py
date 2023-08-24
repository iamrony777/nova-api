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

api_endpoint = os.getenv('CHECKS_ENDPOINT', 'http://localhost:2332/v1')

async def test_server():
    """Tests if the API server is running."""

    try:
        request_start = time.perf_counter()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=f'{api_endpoint.replace("/v1", "")}',
                timeout=3
            )
            response.raise_for_status()

        assert response.json()['ping'] == 'pong', 'The API did not return a correct response.'
    except httpx.ConnectError as exc:
        raise ConnectionError(f'API is not running on port {api_endpoint}.') from exc

    else:
        return time.perf_counter() - request_start

async def test_chat(model: str=MODEL, messages: List[dict]=None) -> dict:
    """Tests an API api_endpoint."""

    json_data = {
        'model': model,
        'messages': messages or MESSAGES,
        'stream': False
    }

    request_start = time.perf_counter()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=f'{api_endpoint}/chat/completions',
            headers=HEADERS,
            json=json_data,
            timeout=10,
        )
        response.raise_for_status()

    assert '2' in response.json()['choices'][0]['message']['content'], 'The API did not return a correct response.'
    return time.perf_counter() - request_start

async def test_library_chat():
    """Tests if the api_endpoint is working with the OpenAI Python library."""

    request_start = time.perf_counter()
    completion = openai.ChatCompletion.create(
        model=MODEL,
        messages=MESSAGES
    )

    assert '2' in completion.choices[0]['message']['content'], 'The API did not return a correct response.'
    return time.perf_counter() - request_start

async def test_models():
    """Tests the models endpoint."""

    request_start = time.perf_counter()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url=f'{api_endpoint}/models',
            headers=HEADERS,
            timeout=3
        )
        response.raise_for_status()
        res = response.json()

    all_models = [model['id'] for model in res['data']]

    assert 'gpt-3.5-turbo' in all_models, 'The model gpt-3.5-turbo is not present in the models endpoint.'
    return time.perf_counter() - request_start

async def test_api_moderation() -> dict:
    """Tests the moderation endpoint."""

    request_start = time.perf_counter()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=f'{api_endpoint}/moderations',
            headers=HEADERS,
            timeout=5,
            json={'input': 'fuck you, die'}
        )

    assert response.json()['results'][0]['flagged'] == True, 'Profanity not detected'
    return time.perf_counter() - request_start

# ==========================================================================================

async def demo():
    """Runs all tests."""

    try:
        for _ in range(30):
            if await test_server():
                break

            print('Waiting until API Server is started up...')
            time.sleep(1)
        else:
            raise ConnectionError('API Server is not running.')

        print('[lightblue]Checking if the API works...')
        print(await test_chat())

        print('[lightblue]Checking if the API works with the Python library...')
        print(await test_library_chat())

        print('[lightblue]Checking if the moderation endpoint works...')
        print(await test_api_moderation())

        print('[lightblue]Checking the models endpoint...')
        print(await test_models())

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
    asyncio.run(demo())
