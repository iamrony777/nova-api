"""User management."""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# the code above is to allow importing from the root folder

import os
import json
import hmac
import fastapi

from dhooks import Webhook, Embed
from dotenv import load_dotenv

import checks.client

from db.users import UserManager

load_dotenv()
router = fastapi.APIRouter(tags=['core'])

async def check_core_auth(request):
    """
    
    ### Checks the request's auth
    Auth is taken from environment variable `CORE_API_KEY`

    """
    received_auth = request.headers.get('Authorization')

    correct_core_api = os.environ['CORE_API_KEY']

    # use hmac.compare_digest to prevent timing attacks
    if received_auth and hmac.compare_digest(received_auth, correct_core_api):
        return fastapi.Response(status_code=403, content='Invalid or no API key given.')

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
        return fastapi.Response(status_code=404, content='User not found.')

    return user

async def new_user_webhook(user: dict) -> None:
    """Runs when a new user is created."""

    dhook = Webhook(os.environ['DISCORD_WEBHOOK__USER_CREATED'])

    embed = Embed(
        description='New User',
        color=0x90ee90,
    )

    embed.add_field(name='ID', value=str(user['_id']), inline=False)
    embed.add_field(name='Discord', value=user['auth']['discord'] or '-')
    embed.add_field(name='Github', value=user['auth']['github'] or '-')

    dhook.send(embed=embed)

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
        return fastapi.Response(status_code=400, content='Invalid or no payload received.')

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
        return fastapi.Response(status_code=400, content='Invalid or no payload received.')

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

    return {
        'library': await checks.client.test_library(),
        'library_moderation': await checks.client.test_library_moderation(),
        'api_moderation': await checks.client.test_api_moderation(),
        'models': await checks.client.test_models()
    }
