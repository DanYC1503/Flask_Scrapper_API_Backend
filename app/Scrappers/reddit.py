import praw
from datetime import datetime
from flask import current_app
from app.services.cleaner import TextCleaner

class RedditScraper:
    def __init__(self, keywords=None, limit=50):
        self.keywords = keywords or []
        self.limit = limit
        self.reddit = praw.Reddit(
            client_id=current_app.config.get("REDDIT_CLIENT_ID"),
            client_secret=current_app.config.get("REDDIT_CLIENT_SECRET"),
            user_agent=current_app.config.get("REDDIT_USER_AGENT")
        )

    def scrape(self):
        results = []
        for keyword in self.keywords:
            search_results = self.reddit.subreddit("all").search(keyword, limit=self.limit, sort='new')
            for submission in search_results:
                submission.comments.replace_more(limit=0)
                comments = [TextCleaner.clean(c.body) for c in submission.comments.list()[:5]]

                clean_title = TextCleaner.clean(submission.title or "")
                clean_selftext = TextCleaner.clean(submission.selftext or "")

                result = {
                    "post_id": submission.id,
                    "title": clean_title,
                    "selftext": clean_selftext,
                    "keyword": TextCleaner.clean(keyword),
                    "score": submission.score,
                    "upvote_ratio": submission.upvote_ratio,
                    "num_comments": submission.num_comments,
                    "is_original_content": submission.is_original_content,
                    "link_flair_text": TextCleaner.clean(submission.link_flair_text or ""),
                    "subreddit": submission.subreddit.display_name,
                    "created_utc": datetime.utcfromtimestamp(submission.created_utc),
                    "url": submission.url,
                    "permalink": f"https://www.reddit.com{submission.permalink}",
                    "author": TextCleaner.clean(str(submission.author)) if submission.author else "unknown",
                    "author_karma": submission.author.link_karma if submission.author else 0,
                    "author_created_utc": datetime.utcfromtimestamp(submission.author.created_utc) if submission.author else None,
                    "top_comments": comments,
                    # Análisis de sentimiento se añadirá después vía OpenAIClient
                    "sentiment": None,
                    "score_sentiment": None,
                    "platform": "reddit"
                }

                results.append(result)

        return results