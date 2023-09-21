import os
import asyncio

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

class FinanceManager:
    def __init__(self):
        self.conn = AsyncIOMotorClient(os.environ['MONGO_URI'])

    async def _get_collection(self, collection_name: str):
        return self.conn['finances'][collection_name]

    async def get_entire_financial_history(self):
        donations_db = await self._get_collection('donations')
        expenses_db = await self._get_collection('expenses')

        # turn both into JSON-like lists of dicts at once (make sure to fix the _id)
        history = {'donations': [], 'expenses': []}

        async for donation in donations_db.find():
            donation['_id'] = str(donation['_id'])
            history['donations'].append(donation)

        async for expense in expenses_db.find():
            expense['_id'] = str(expense['_id'])
            history['expenses'].append(expense)

        # sort all by timestamp
        history['donations'] = sorted(history['donations'], key=lambda x: x['timestamp'])

        return history

manager = FinanceManager()

if __name__ == '__main__':
    print(asyncio.run(manager.get_entire_financial_history()))
