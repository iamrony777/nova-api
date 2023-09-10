"""This module contains functions for checking if a message violates the moderation policy."""

import time
import difflib
import asyncio
import aiocache
import profanity_check

from typing import Union
from Levenshtein import distance

cache = aiocache.Cache(aiocache.SimpleMemoryCache)

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
    """Checks if the input violates the moderation policy.
    """
    # use aio cache to cache the result
    inp = input_to_text(inp)

    # utilize the cache
    if await cache.exists(inp):
        return await cache.get(inp)
    else:
        await cache.set(inp, await is_policy_violated__own_model(inp))
        return await cache.get(inp)

async def is_policy_violated__own_model(inp: Union[str, list]) -> bool:
    """Checks if the input violates the moderation policy using our own model."""

    inp = input_to_text(inp).lower()

    if profanity_check.predict([inp])[0]:
        return 'Sorry, our moderation AI has detected NSFW content in your message.'

    return False

if __name__ == '__main__':
    while True:
        print(asyncio.run(is_policy_violated(input('-> '))))
