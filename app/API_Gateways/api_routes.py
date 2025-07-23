from flask import Blueprint, jsonify, request
from datetime import datetime
from app.OpenAIConfig.openai_client import OpenAIClient
from app.Scrappers.reddit import RedditScraper
from app.Scrappers.tiktok import scrape_tiktok
from app.Scrappers.facebook import FacebookScraper
from concurrent.futures import ThreadPoolExecutor
from Models.models import CommentRedis
import uuid

from app.Models.models import InfluencerRedis

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/scrape/all', methods=['POST'])
def scrape_all():
    data = request.get_json()
    query = data.get('query')
    limit = int(data.get('limit', 5))

    if not query:
        return jsonify({"error": "Debe proporcionar una búsqueda (influencer o palabra clave)"}), 400

    influencer_name = query.replace("#", "").replace("@", "")

    # Check Redis 
    if not InfluencerRedis.exists(influencer_name):
        InfluencerRedis.save(influencer_name)

    gpt = OpenAIClient()  # <-- temporarily disabled
    results = []
    executor = ThreadPoolExecutor(max_workers=3)

    # Funciones para cada scrapper
    def scrape_reddit():
        scraper = RedditScraper(keywords=[query], limit=limit)
        raw_posts = scraper.scrape()
        print("Reddit raw posts:", raw_posts)
        comments = []
        for post in raw_posts:
            full_text = f"{post['title']} {post['selftext']}".strip()
            sentiment, score = gpt.analyze_sentiment(full_text)
            sentiment, score = "neutral", 0.0  # test values
            comments.append({
                "platform": "reddit",
                "influencer": query,
                "text": full_text,
                "sentiment": sentiment,
                "score": score,
                "date": post['created_utc'].isoformat()
            })
        return comments

    def scrape_tiktok_func():
        tiktok_comments = scrape_tiktok(query=query, num_videos=limit)
        print("TikTok comments:", tiktok_comments)
        comments = []
        for c in tiktok_comments:
            full_text = f"{c['title']} {c['text']}".strip()
            sentiment, score = gpt.analyze_sentiment(full_text)
            sentiment, score = "neutral", 0.0  # test values
            comments.append({
                "platform": "tiktok",
                "influencer": query,
                "text": full_text,
                "sentiment": sentiment,
                "score": score,
                "date": datetime.utcnow().isoformat()
            })
        return comments


    def scrape_facebook():
        fb_scraper = FacebookScraper()
        fb_posts = fb_scraper.search(query)
        comments = []

        for post in fb_posts:
            post_title = post.get("postTitle", "")
            post_comments = post.get("comments", [])

            for comment in post_comments:
                # comment is expected to be a dict: {'commentId': ..., 'postId': ..., 'username': ..., 'comment': ...}
                comment_text = comment.get("comment", "").strip()
                full_text = f"{comment_text}"  # or f"{post_title} {comment_text}" if you want both

                sentiment, score = "neutral", 0.0  # placeholder until OpenAI is set up
                comments.append({
                    "platform": "facebook",
                    "influencer": post.get("influencer", "unknown"),
                    "text": full_text,
                    "sentiment": sentiment,
                    "score": score,
                    "date": post.get("date", datetime.utcnow().isoformat()),
                })

        return comments

    # Ejecutar los 3 scrappers en paralelo
    futures = [
        executor.submit(scrape_reddit),
        executor.submit(scrape_tiktok_func),
        executor.submit(scrape_facebook)
    ]

    for future in futures:
        try:
            results.extend(future.result())
        except Exception as e:
            print(f"Error in scrapper thread: {e}")

    # Añadir influencer a cada comentario para el JSON de salida
    for c in results:
        c["influencer"] = influencer_name
        comment_id = str(uuid.uuid4())
        CommentRedis.save_comment(comment_id, influencer_name, c)

    return jsonify({
        "message": f"Scraping completo para {influencer_name}",
        "comments": results
    }), 200
