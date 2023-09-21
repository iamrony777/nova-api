from stats import * 
import asyncio

manager = StatsManager()

asyncio.run(manager.get_model_usage())
