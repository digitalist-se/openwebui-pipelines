from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
import requests
import os

class Pipeline:
    class Valves(BaseModel):
        WEBHOOK_URL: str

    def __init__(self):
        self.name = "Webhook Pipeline"
        self.valves = self.Valves(WEBHOOK_URL=os.getenv("WEBHOOK_URL", ""))

    async def on_startup(self):
        print(f"on_startup:{__name__}")

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        print(f"pipe:{__name__}")
        



        # Make a request to the webhook
        try:
            response = requests.get(
                f"{self.valves.WEBHOOK_URL}?user_message={user_message}",
                json={
                    "model_id": model_id,
                    "messages": messages,
                    "body": body
                }
            )


            response.raise_for_status()
            return f"Webhook response: {response.text}"
        except requests.RequestException as e:
            return f"Error calling webhook: {str(e)}"