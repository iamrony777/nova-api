"""User management."""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# the code above is to allow importing from the root folder

import time
import json
import hmac
import httpx
import fastapi
import functools

from dhooks import Webhook, Embed
from dotenv import load_dotenv

import checks.client

from helpers import errors
from db import users, finances

load_dotenv()
router = fastapi.APIRouter(tags=['core'])

async def check_core_auth(request):
    """Checks the core API key. Returns nothing if it's valid, otherwise returns an error.
    """
    received_auth = request.headers.get('Authorization')

    correct_core_api = os.environ['CORE_API_KEY']

    # use hmac.compare_digest to prevent timing attacks
    if not (received_auth and hmac.compare_digest(received_auth, correct_core_api)):
        return await errors.error(401, 'The core API key you provided is invalid.', 'Check the `Authorization` header.')

    return None

async def new_user_webhook(user: dict) -> None:
    """Runs when a new user is created."""

    dhook = Webhook(os.environ['DISCORD_WEBHOOK__USER_CREATED'])

    embed = Embed(
        description='New User',
        color=0x90ee90,
    )

    dc = user['auth']['discord']

    embed.add_field(name='ID', value=str(user['_id']), inline=False)
    embed.add_field(name='Discord', value=dc or '-')
    embed.add_field(name='Github', value=user['auth']['github'] or '-')

    dhook.send(content=f'<@{dc}>', embed=embed)


@router.get('/users')
async def get_users(discord_id: int, incoming_request: fastapi.Request):
    """Returns a user by their discord ID. Requires a core API key."""

    auth = await check_core_auth(incoming_request)
    if auth: return auth

    user = await users.manager.user_by_discord_id(discord_id)
    if not user:
        return await errors.error(404, 'Discord user not found in the API database.', 'Check the `discord_id` parameter.')

    # turn the ObjectId into a string
    user['_id'] = str(user['_id'])

    return user

@router.post('/users')
async def create_user(incoming_request: fastapi.Request):
    """Creates a user. Requires a core API key."""

    auth_error = await check_core_auth(incoming_request)

    if auth_error:
        return auth_error

    try:
        payload = await incoming_request.json()
        discord_id = payload.get('discord_id')
    except (json.decoder.JSONDecodeError, AttributeError):
        return await errors.error(400, 'Invalid or no payload received.', 'The payload must be a JSON object with a `discord_id` key.')

    user = await users.manager.create(discord_id)
    await new_user_webhook(user)

    user['_id'] = str(user['_id'])

    return user

@router.put('/users')
async def update_user(incoming_request: fastapi.Request):
    """Updates a user. Requires a core API key."""

    auth_error = await check_core_auth(incoming_request)
    if auth_error: return auth_error

    try:
        payload = await incoming_request.json()
        discord_id = payload.get('discord_id')
        updates = payload.get('updates')
    except (json.decoder.JSONDecodeError, AttributeError):
        return await errors.error(
            400, 'Invalid or no payload received.',
            'The payload must be a JSON object with a `discord_id` key and an `updates` key.'
        )

    user = await users.manager.update_by_discord_id(discord_id, updates)

    return user

@router.get('/checks')
async def run_checks(incoming_request: fastapi.Request):
    """Tests the API. Requires a core API key."""

    auth_error = await check_core_auth(incoming_request)
    if auth_error: return auth_error

    results = {}

    funcs = [
        checks.client.test_chat_non_stream_gpt4,
        checks.client.test_chat_stream_gpt3,
        checks.client.test_function_calling,
        checks.client.test_image_generation,
        # checks.client.test_speech_to_text,
        checks.client.test_models
    ]

    for func in funcs:
        try:
            result = await func()
        except Exception as exc:
            results[func.__name__] = str(exc)
        else:
            results[func.__name__] = result

    return results

async def get_crypto_price(cryptocurrency: str) -> float:
    """Gets the price of a cryptocurrency using coinbase's API."""

    if os.path.exists('cache/crypto_prices.json'):
        with open('cache/crypto_prices.json', 'r') as f:
            cache = json.load(f)
    else:
        cache = {}

    is_old = time.time() - cache.get('_last_updated', 0) > 60 * 60

    if is_old or cryptocurrency not in cache:
        async with httpx.AsyncClient() as client:
            response = await client.get(f'https://api.coinbase.com/v2/prices/{cryptocurrency}-USD/spot')
            usd_price = float(response.json()['data']['amount'])

            cache[cryptocurrency] = usd_price
            cache['_last_updated'] = time.time()

            with open('cache/crypto_prices.json', 'w') as f:
                json.dump(cache, f)

    return cache[cryptocurrency]

@router.get('/finances')
async def get_finances(incoming_request: fastapi.Request):
    """Return financial information. Requires a core API key."""

    auth_error = await check_core_auth(incoming_request)
    if auth_error: return auth_error

    transactions = await finances.manager.get_entire_financial_history()

    for table in transactions:
        for transaction in transactions[table]:
            currency = transaction['currency']

            if '-' in currency:
                currency = currency.split('-')[0]

            amount = transaction['amount']

            if currency == 'mBTC':
                currency = 'BTC'
                amount = transaction['amount'] / 1000

            amount_in_usd = await get_crypto_price(currency) * amount
            transactions[table][transactions[table].index(transaction)]['amount_usd'] = amount_in_usd

    return transactions
