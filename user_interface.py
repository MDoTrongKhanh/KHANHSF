import os
import requests

class User_Interface:
    def __init__(self):
        self.token = os.getenv("MY_SECRET_TOKEN")
        if not self.token:
            raise RuntimeError("Missing token! Please set MY_SECRET_TOKEN in GitHub Secrets.")
        self.api_url = "https://api.example.com/data"
    
    async def main(self):
        data = await self.get_account()
        print("Account Data:", data)
    
    async def get_account(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(self.api_url, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"Account error: {response.json().get('error', 'Unknown error')}")
        return response.json()

if __name__ == "__main__":
    import asyncio
    asyncio.run(User_Interface().main())
