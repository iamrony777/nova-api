import os
import time

from dotenv import load_dotenv

load_dotenv()

async def get_ip(request) -> str:
    """Get the IP address of the incoming request."""

    xff = None
    if request.headers.get('x-forwarded-for'):
        xff, *_ = request.headers['x-forwarded-for'].split(', ')

    possible_ips = [
        xff,
        request.headers.get('cf-connecting-ip'),
        request.client.host
    ]

    detected_ip = next((i for i in possible_ips if i), None)

    return detected_ip

def get_ratelimit_key(request) -> str:
    """Get the IP address of the incoming request."""

    xff = None
    if request.headers.get('x-forwarded-for'):
        xff, *_ = request.headers['x-forwarded-for'].split(', ')

    possible_ips = [
        xff,
        request.headers.get('cf-connecting-ip'),
        request.client.host
    ]

    detected_ip = next((i for i in possible_ips if i), None)

    for whitelisted_ip in os.getenv('NO_RATELIMIT_IPS', '').split():
        if whitelisted_ip in detected_ip:
            custom_key = f'whitelisted-{time.time()}'
            return custom_key

    return detected_ip
