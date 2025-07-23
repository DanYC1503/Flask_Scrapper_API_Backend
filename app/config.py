import os

class Config:
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0

    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'dummy-api-key')
