import requests
from urllib.parse import quote

class FacebookScraper:
    def __init__(self, port: int = 8888):
        self.port = port
        self.base_url = f"http://localhost:{port}/facebook/search/"

    def search(self, query: str):
        encoded_query = quote(query)
        full_url = self.base_url + encoded_query
        print(f"Sending search request: {full_url}")

        try:
            response = requests.get(full_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to fetch results: {e}")
            return []
