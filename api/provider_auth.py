"""This module contains functions for authenticating with providers."""

import os
import asyncio

from dotenv import load_dotenv
from dhooks import Webhook, Embed

load_dotenv()

async def invalidation_webhook(provider_and_key: str) -> None:
    """Runs when a new user is created."""

    dhook = Webhook(os.environ['DISCORD_WEBHOOK__API_ISSUE'])

    embed = Embed(
        description='Key Invalidated',
        color=0xffee90,
    )

    embed.add_field(name='Provider', value=provider_and_key.split('>')[0])
    embed.add_field(name='Key (censored)', value=f'||{provider_and_key.split(">")[1][:10]}...||', inline=False)

    dhook.send(embed=embed)

async def invalidate_key(provider_and_key: str) -> None:
    """

    Invalidates a key stored in the secret/ folder by storing it in the associated .invalid.txt file.
    The schmea in which <provider_and_key> should be passed is:
    <provider_name><key>, e.g.
    closed4>cd-...

    """

    if not provider_and_key:
        return

    provider = provider_and_key.split('>')[0]
    provider_file = f'secret/{provider}.txt'
    key = provider_and_key.split('>')[1]

    with open(provider_file, encoding='utf8') as f_in:
        text = f_in.read()

    with open(provider_file, 'w', encoding='utf8') as f_out:
        f_out.write(text.replace(key, ''))

    with open(f'secret/{provider}.invalid.txt', 'a', encoding='utf8') as f:
        f.write(key + '\n')

    await invalidation_webhook(provider_and_key)

if __name__ == '__main__':
    asyncio.run(invalidate_key('closed>demo-...'))
