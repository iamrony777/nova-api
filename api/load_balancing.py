import random
import asyncio

import providers

async def _get_module_name(module) -> str:
    name = module.__name__
    if '.' in name:
        return name.split('.')[-1]
    return name

async def balance_chat_request(payload: dict) -> dict:
    """
    ### Load balance the chat completion request between chat providers.
    Providers are sorted by streaming and models. Target (provider.chat_completion) is returned
    """

    providers_available = []

    for provider_module in providers.MODULES:
        if payload['stream'] and not provider_module.STREAMING:
            continue

        if payload['model'] not in provider_module.MODELS:
            continue

        providers_available.append(provider_module)

    if not providers_available:
        raise ValueError(f'The model "{payload["model"]}" is not available. MODEL_UNAVAILABLE')

    provider = random.choice(providers_available)
    target = await provider.chat_completion(**payload)

    module_name = await _get_module_name(provider)
    target['module'] = module_name

    return target

async def balance_organic_request(request: dict) -> dict:
    """
    ### Load balance non-chat completion request
    Balances between other "organic" providers which respond in the desired format already.
    Organic providers are used for non-chat completions, such as moderation and other paths.    
    """
    providers_available = []

    if not request.get('headers'):
        request['headers'] = {
            'Content-Type': 'application/json'
        }

    for provider_module in providers.MODULES:
        if not provider_module.ORGANIC:
            continue

        if '/moderations' in request['path']:
            if not provider_module.MODERATIONS:
                continue

        providers_available.append(provider_module)

    provider = random.choice(providers_available)
    target = await provider.organify(request)

    module_name = await _get_module_name(provider)
    target['module'] = module_name

    return target

if __name__ == '__main__':
    req = asyncio.run(balance_chat_request(payload={'model': 'gpt-3.5-turbo', 'stream': True}))
    print(req['url'])
