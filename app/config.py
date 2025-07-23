import os

class Config:
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0

    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'dummy-api-key')

    REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
    REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'karma_influencer_app/0.1')