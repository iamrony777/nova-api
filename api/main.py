"""FastAPI setup."""

import fastapi
import pydantic
import functools

from rich import print
from dotenv import load_dotenv
from json import JSONDecodeError
from bson.objectid import ObjectId
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler

from helpers import network

import core
import handler
import moderation

load_dotenv()

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.include_router(core.router)

limiter = Limiter(
    swallow_errors=True,
    key_func=network.get_ratelimit_key, default_limits=[
    '2/second',
    '20/minute',
    '300/hour'
])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.on_event('startup')
async def startup_event():
    """Runs when the API starts up."""
    # https://stackoverflow.com/a/74529009
    pydantic.json.ENCODERS_BY_TYPE[ObjectId]=str

@app.get('/')
async def root():
    """
    Returns general information about the API.
    """

    return {
        'hi': 'Welcome to the Nova API!',
        'learn_more_here': 'https://nova-oss.com',
        'github': 'https://github.com/novaoss/nova-api',
        'core_api_docs_for_nova_developers': '/docs',
        'ping': 'pong'
    }

@app.route('/v1/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
async def v1_handler(request: fastapi.Request):
    res = await handler.handle(request)
    return res

@functools.lru_cache()
@app.post('/moderate')
async def moderate(request: fastapi.Request):
    try:
        prompt = await request.json()
        prompt = prompt['text']
    except (KeyError, JSONDecodeError):
        return fastapi.Response(status_code=400)

    result = await moderation.is_policy_violated__own_model(prompt)
    return result or ''
