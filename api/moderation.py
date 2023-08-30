"""This module contains functions for checking if a message violates the moderation policy."""

import time
import asyncio
import aiohttp
import profanity_check

import proxies
import provider_auth
import load_balancing

from typing import Union

def input_to_text(inp: Union[str, list]) -> str:
    """Converts the input to a string."""

    text = inp

    if isinstance(inp, list):
        text = ''
        if isinstance(inp[0], dict):
            for msg in inp:
                text += msg['content'] + '\n'

        else:
            text = '\n'.join(inp)

    return text

async def is_policy_violated(inp: Union[str, list]) -> bool:
    """
    ### Check if a message violates the moderation policy.
    You can either pass a list of messages consisting of dicts with "role" and "content", as used in the API parameter,
    or just a simple string.
    
    Returns True if the message violates the policy, False otherwise.
    """

    text = input_to_text(inp)
    return await is_policy_violated__own_model(text)

    for _ in range(1):
        req = await load_balancing.balance_organic_request(
            {
                'path': '/v1/moderations',
                'payload': {'input': text}
            }
        )

        async with aiohttp.ClientSession(connector=proxies.get_proxy().connector) as session:
            try:
                async with session.request(
                    method=req.get('method', 'POST'),
                    url=req['url'],
                    data=req.get('data'),
                    json=req.get('payload'),
                    headers=req.get('headers'),
                    cookies=req.get('cookies'),
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=2),
                ) as res:
                    res.raise_for_status()
                    json_response = await res.json()

                    categories = json_response['results'][0]['category_scores']

                    if json_response['results'][0]['flagged']:
                        return max(categories, key=categories.get)

                    return False

            except Exception as exc:
                if '401' in str(exc):
                    await provider_auth.invalidate_key(req.get('provider_auth'))
                print('[!] moderation error:', type(exc), exc)
                continue

async def is_policy_violated__own_model(inp: Union[str, list]) -> bool:
    inp = input_to_text(inp)

    if profanity_check.predict([inp])[0]:
        return 'own model detected'

    return False

if __name__ == '__main__':
    print(asyncio.run(is_policy_violated('kill ms')))
