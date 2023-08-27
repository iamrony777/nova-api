from db import logs, stats, users
from helpers import network

async def after_request(
    incoming_request: dict,
    target_request: dict,
    user: dict,
    credits_cost: int,
    input_tokens: int,
    path: str,
    is_chat: bool,
    model: str,
) -> None:
    if user and incoming_request:
        await logs.log_api_request(user=user, incoming_request=incoming_request, target_url=target_request['url'])

    if credits_cost and user:
        await users.manager.update_by_id(user['_id'], {'$inc': {'credits': -credits_cost}})

    ip_address = await network.get_ip(incoming_request)

    await stats.manager.add_date()
    await stats.manager.add_ip_address(ip_address)
    await stats.manager.add_path(path)
    await stats.manager.add_target(target_request['url'])

    if is_chat:
        await stats.manager.add_model(model)
        await stats.manager.add_tokens(input_tokens, model)
