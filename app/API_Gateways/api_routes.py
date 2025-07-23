from flask import Blueprint, jsonify, request
from datetime import datetime
from app.OpenAIConfig.openai_client import OpenAIClient
from app.Scrappers.reddit import RedditScraper
from app.Scrappers.tiktok import scrape_tiktok
from app.Scrappers.facebook import FacebookScraper
from concurrent.futures import ThreadPoolExecutor
from app.Models.models import CommentRedis
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
        gpt = OpenAIClient()
        for post in fb_posts:
            post_title = post.get("postTitle", "")
            post_comments = post.get("comments", [])

            for comment in post_comments:
                
                comment_text = comment.get("comment", "").strip()
                full_text = f"{comment_text}" 

                sentiment, score = gpt.analyze_sentiment(full_text)
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

@api_bp.route('/scrape/reddit', methods=['POST'])
def scrape_reddit_route():
    print("[DEBUG] Request data:", request.data)
    print("[DEBUG] Request JSON:", request.get_json())
    data = request.get_json()
    query = data.get('query')
    limit = int(data.get('limit', 5))

    if not query:
        return jsonify({"error": "Debe proporcionar una búsqueda"}), 400

    influencer_name = query.replace("#", "").replace("@", "")
    cached = CommentRedis.get_comments_by_influencer_and_platform(influencer_name, "reddit")
    if cached:
        print("TikTok: Returning cached comments")
        return jsonify({"message": "Comentarios en caché", "comments": cached}), 200

    # If no cached comments, continue scraping
    if not InfluencerRedis.exists(influencer_name):
        InfluencerRedis.save(influencer_name)


    gpt = OpenAIClient()
    scraper = RedditScraper(keywords=[query], limit=limit)
    raw_posts = scraper.scrape()

    comments = []
    for post in raw_posts:
        full_text = f"{post['title']} {post['selftext']}".strip()
        sentiment, score = gpt.analyze_sentiment(full_text)
        comment_data = {
            "platform": "reddit",
            "influencer": influencer_name,
            "text": full_text,
            "sentiment": sentiment,
            "score": score,
            "date": post['created_utc'].isoformat()
        }
        comment_id = str(uuid.uuid4())
        CommentRedis.save_comment(comment_id, influencer_name, comment_data)
        comments.append(comment_data)

    return jsonify({"message": "Scraping de Reddit completado", "comments": comments}), 200

@api_bp.route('/scrape/tiktok', methods=['POST'])
def scrape_tiktok_route():
    data = request.get_json()
    query = data.get('query')
    limit = int(3)

    if not query:
        return jsonify({"error": "Debe proporcionar una búsqueda"}), 400

    influencer_name = query.replace("#", "").replace("@", "")

    # Check cache first
    cached = CommentRedis.get_comments_by_influencer_and_platform(influencer_name, "tiktok")
    if cached:
        print("TikTok: Returning cached comments")
        return jsonify({"message": "Comentarios en caché", "comments": cached}), 200

    # If no cached comments, continue scraping
    if not InfluencerRedis.exists(influencer_name):
        InfluencerRedis.save(influencer_name)

    gpt = OpenAIClient()
    tiktok_comments = scrape_tiktok(query=query, num_videos=limit)

    comments = []
    for c in tiktok_comments:
        full_text = f"{c['title']} {c['text']}".strip()
        sentiment, score = gpt.analyze_sentiment(full_text)
        comment_data = {
            "platform": "tiktok",
            "influencer": influencer_name,
            "text": full_text,
            "sentiment": sentiment,
            "score": score,
            "date": datetime.utcnow().isoformat()
        }
        comment_id = str(uuid.uuid4())
        CommentRedis.save_comment(comment_id, influencer_name, comment_data)
        comments.append(comment_data)

    return jsonify({"message": "Scraping de TikTok completado", "comments": comments}), 200

@api_bp.route('/scrape/facebook', methods=['POST'])
def scrape_facebook_route():
    data = request.get_json()
    query = data.get('query')
    limit = int(data.get('limit', 5))  # Puedes ignorar esto si Facebook no lo necesita

    if not query:
        return jsonify({"error": "Debe proporcionar una búsqueda"}), 400

    influencer_name = query.replace("#", "").replace("@", "")
    cached = CommentRedis.get_comments_by_influencer_and_platform(influencer_name, "tiktok")
    if cached:
        print("TikTok: Returning cached comments")
        return jsonify({"message": "Comentarios en caché", "comments": cached}), 200

    # If no cached comments, continue scraping
    if not InfluencerRedis.exists(influencer_name):
        InfluencerRedis.save(influencer_name)

    gpt = OpenAIClient()
    fb_scraper = FacebookScraper()
    fb_posts = fb_scraper.search(query)

    comments = []
    for post in fb_posts:
        post_title = post.get("postTitle", "")
        post_comments = post.get("comments", [])

        for comment in post_comments:
            comment_text = comment.get("comment", "").strip()
            full_text = f"{comment_text}"
            sentiment, score = gpt.analyze_sentiment(full_text)

            comment_data = {
                "platform": "facebook",
                "influencer": influencer_name,
                "text": full_text,
                "sentiment": sentiment,
                "score": score,
                "date": post.get("date", datetime.utcnow().isoformat())
            }
            comment_id = str(uuid.uuid4())
            CommentRedis.save_comment(comment_id, influencer_name, comment_data)
            comments.append(comment_data)

    return jsonify({"message": "Scraping de Facebook completado", "comments": comments}), 200

def normalize_influencer_name(name: str) -> str:
    return name.lower().replace("_", " ").strip()

@api_bp.route('/comments/<influencer_name>', methods=['GET'])
def get_comments(influencer_name):
    print(f"[DEBUG] influencer_name recibido: '{influencer_name}'")
    exists = InfluencerRedis.exists(influencer_name)
    print(f"{influencer_name} exists")
    print(f"[DEBUG] Influencer exists in Redis? {exists}")

    if not exists:
        return jsonify({"error": "Influencer no encontrado"}), 404

    comments = CommentRedis.get_comments_by_influencer(influencer_name)
    if not comments:
        return jsonify([]), 200

    comments_sorted = sorted(comments, key=lambda c: c.get("date", ""), reverse=True)
    return jsonify(comments_sorted), 200



@api_bp.route('/analytics/<influencer_name>', methods=['GET'])
def influencer_analytics(influencer_name):
    if not InfluencerRedis.exists(influencer_name):
        return jsonify({"error": "Influencer no encontrado"}), 404

    comments = CommentRedis.get_comments_by_influencer(influencer_name)
    if not comments:
        return jsonify({"error": "No se encontraron comentarios"}), 404

    total = len(comments)
    pos = [c for c in comments if c["sentiment"] == "positivo"]
    neg = [c for c in comments if c["sentiment"] == "negativo"]
    neu = [c for c in comments if c["sentiment"] == "neutral"]

    scores = [c["score"] for c in comments if isinstance(c["score"], (int, float))]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    if avg_score > 0.1:
        karma = "positivo"
        recommendation = (
            "La percepción general del público hacia esta figura es positiva. "
            "Los comentarios analizados reflejan un apoyo significativo y una buena aceptación. "
            "Esto sugiere que su imagen pública es sólida y bien recibida por la mayoría."
        )
    elif avg_score < -0.1:
        karma = "negativo"
        recommendation = (
            "La mayoría de los comentarios tienen un tono negativo, lo que indica una percepción desfavorable del público. "
            "Este resultado podría ser señal de una crisis de reputación o un problema de imagen que merece atención inmediata."
        )
    else:
        karma = "neutral"
        recommendation = (
            "Los comentarios están equilibrados entre opiniones positivas y negativas. "
            "No se identifica una tendencia clara, lo cual puede indicar polarización entre los seguidores o falta de interés general. "
            "Sería recomendable monitorear más de cerca la evolución de esta percepción."
        )
    return jsonify({
        "total": total,
        "positive": len(pos),
        "neutral": len(neu),
        "negative": len(neg),
        "average_score": avg_score,
        "karma_score": karma,
        "recommendation": recommendation
    }), 200
