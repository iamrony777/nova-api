"""FastAPI setup."""

import fastapi
import pydantic

from rich import print
from dotenv import load_dotenv
from bson.objectid import ObjectId
from fastapi.middleware.cors import CORSMiddleware

import core
import transfer

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

app.add_route('/v1/{path:path}', transfer.handle, ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
