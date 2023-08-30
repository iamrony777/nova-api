"""This module contains the streaming logic for the API."""

import os
import json
import yaml
import dhooks
import asyncio
import aiohttp
import starlette

from rich import print
from dotenv import load_dotenv

import chunks
import proxies
import provider_auth
import after_request
import load_balancing

from helpers import network, chat, errors

load_dotenv()

## Loads config which contains rate limits
with open('config/config.yml', encoding='utf8') as f:
    config = yaml.safe_load(f)

## Where all rate limit requested data will be stored.
# Rate limit data is **not persistent** (It will be deleted on server stop/restart).
user_last_request_time = {}

DEMO_PAYLOAD = {
    'model': 'gpt-3.5-turbo',
    'messages': [
        {
            'role': 'user',
            'content': '1+1='
        }
    ]
}

async def stream(
    path: str='/v1/chat/completions',
    user: dict=None,
    payload: dict=None,
    credits_cost: int=0,
    input_tokens: int=0,
    incoming_request: starlette.requests.Request=None,
):
    """Stream the completions request. Sends data in chunks
    If not streaming, it sends the result in its entirety.
    """

    is_chat = False
    is_stream = payload.get('stream', False)

    model = None

    if 'chat/completions' in path:
        is_chat = True
        model = payload['model']

    if is_chat and is_stream:
        chat_id = await chat.create_chat_id()
        yield await chat.create_chat_chunk(chat_id=chat_id, model=model, content=chat.CompletionStart)
        yield await chat.create_chat_chunk(chat_id=chat_id, model=model, content=None)

    json_response = {}

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'null'
    }

    for _ in range(5):
        # Load balancing: randomly selecting a suitable provider
        # If the request is a chat completion, then we need to load balance between chat providers
        # If the request is an organic request, then we need to load balance between organic providers
        try:
            if is_chat:
                target_request = await load_balancing.balance_chat_request(payload)
            else:
                
                # In this case we are doing a organic request. "organic" means that it's not using a reverse engineered front-end, but rather ClosedAI's API directly
                # churchless.tech is an example of an organic provider, because it redirects the request to ClosedAI.
                target_request = await load_balancing.balance_organic_request({
                    'method': incoming_request.method,
                    'path': path,
                    'payload': payload,
                    'headers': headers,
                    'cookies': incoming_request.cookies
                })
        except ValueError as exc:
            webhook = dhooks.Webhook(os.environ['DISCORD_WEBHOOK__API_ISSUE'])
            webhook.send(content=f'API Issue: **`{exc}`**\nhttps://i.imgflip.com/7uv122.jpg')
            yield await errors.yield_error(500, 'Sorry, the API has no working keys anymore.', 'The admins have been messaged automatically.')
            return

        target_request['headers'].update(target_request.get('headers', {}))

        if target_request['method'] == 'GET' and not payload:
            target_request['payload'] = None

        # We haven't done any requests as of right now, everything until now was just preparation
        # Here, we process the request
        async with aiohttp.ClientSession(connector=proxies.get_proxy().connector) as session:
            try:
                async with session.request(
                    method=target_request.get('method', 'POST'),
                    url=target_request['url'],
                    data=target_request.get('data'),
                    json=target_request.get('payload'),
                    headers=target_request.get('headers', {}),
                    cookies=target_request.get('cookies'),
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(
                        connect=2,
                        total=float(os.getenv('TRANSFER_TIMEOUT', '120'))
                    ),
                ) as response:

                    if response.status == 429:
                        continue

                    if response.content_type == 'application/json':
                        data = await response.json()

                        if 'invalid_api_key' in str(data) or 'account_deactivated' in str(data):
                            print('[!] invalid api key', target_request.get('provider_auth'))
                            await provider_auth.invalidate_key(target_request.get('provider_auth'))
                            continue

                        if response.ok:
                            json_response = data

                    if is_stream:
                        try:
                            response.raise_for_status()
                        except Exception as exc:
                            if 'Too Many Requests' in str(exc):
                                continue

                        async for chunk in chunks.process_chunks(
                            chunks=response.content.iter_any(),
                            is_chat=is_chat,
                            chat_id=chat_id,
                            model=model,
                            target_request=target_request
                        ):
                            yield chunk

                    break

            except Exception as exc:
                print(f'[!] {type(exc)} - {exc}')
                continue

            if (not json_response) and is_chat:
                print('[!] chat response is empty')
                continue

    if is_chat and is_stream:
        yield await chat.create_chat_chunk(chat_id=chat_id, model=model, content=chat.CompletionStop)
        yield 'data: [DONE]\n\n'

    if not is_stream and json_response:
        yield json.dumps(json_response)

    await after_request.after_request(
        incoming_request=incoming_request,
        target_request=target_request,
        user=user,
        credits_cost=credits_cost,
        input_tokens=input_tokens,
        path=path,
        is_chat=is_chat,
        model=model,
    )

    print(f'[+] {path} -> {model or "")

if __name__ == '__main__':
    asyncio.run(stream())
