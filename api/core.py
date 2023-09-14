"""User management."""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# the code above is to allow importing from the root folder

import json
import hmac
import fastapi

from dhooks import Webhook, Embed
from dotenv import load_dotenv

import checks.client

from helpers import errors
from db.users import UserManager

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

@router.get('/users')
async def get_users(discord_id: int, incoming_request: fastapi.Request):
    """Returns a user by their discord ID. Requires a core API key."""

    auth = await check_core_auth(incoming_request)
    if auth:
        return auth

    # Get user by discord ID
    manager = UserManager()
    user = await manager.user_by_discord_id(discord_id)
    if not user:
        return await errors.error(404, 'Discord user not found in the API database.', 'Check the `discord_id` parameter.')

    return user

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

    # Create the user 
    manager = UserManager()
    user = await manager.create(discord_id)
    await new_user_webhook(user)

    return user

@router.put('/users')
async def update_user(incoming_request: fastapi.Request):
    """Updates a user. Requires a core API key."""

    auth_error = await check_core_auth(incoming_request)

    if auth_error:
        return auth_error

    try:
        payload = await incoming_request.json()
        discord_id = payload.get('discord_id')
        updates = payload.get('updates')
    except (json.decoder.JSONDecodeError, AttributeError):
        return await errors.error(
            400, 'Invalid or no payload received.',
            'The payload must be a JSON object with a `discord_id` key and an `updates` key.'
        )

    # Update the user
    manager = UserManager()
    user = await manager.update_by_discord_id(discord_id, updates)

    return user

@router.get('/checks')
async def run_checks(incoming_request: fastapi.Request):
    """Tests the API. Requires a core API key."""

    auth_error = await check_core_auth(incoming_request)

    if auth_error:
        return auth_error

    results = {}

    funcs = [
        checks.client.test_chat_non_stream_gpt4,
        checks.client.test_chat_stream_gpt3,
        checks.client.test_function_calling,
        checks.client.test_image_generation,
        checks.client.test_speech_to_text,
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
