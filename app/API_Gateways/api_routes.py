from flask import Blueprint, jsonify, request
from datetime import datetime
from app.OpenAIConfig.openai_client import OpenAIClient
from app.Scrappers.reddit import RedditScraper
from app.Scrappers.tiktok import scrape_tiktok
from app.Scrappers.facebook import FacebookScraper
from concurrent.futures import ThreadPoolExecutor
from app.Models.models import CommentRedis
import uuid
import re
import random
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import base64

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
    data = request.get_json()

    keywords = data.get('keywords', [])
    limit = int(data.get('limit', 5))

    if not keywords:
        return jsonify({"error": "Debe proporcionar al menos una palabra clave"}), 400

    query = keywords[0]  # usa la primera keyword para el influencer_name
    influencer_name = query.replace("#", "").replace("@", "")

    cached = CommentRedis.get_comments_by_influencer_and_platform(influencer_name, "reddit")
    if cached:
        return jsonify({"message": "Comentarios en caché", "comments": cached}), 200

    if not InfluencerRedis.exists(influencer_name):
        InfluencerRedis.save(influencer_name)

    gpt = OpenAIClient()
    scraper = RedditScraper(keywords=keywords, limit=limit)
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

    # 1. Calcular métricas básicas
    total = len(comments)
    pos = [c for c in comments if c["sentiment"] == "positivo"]
    neg = [c for c in comments if c["sentiment"] == "negativo"]
    neu = [c for c in comments if c["sentiment"] == "neutral"]
    
    scores = [c["score"] for c in comments if isinstance(c["score"], (int, float))]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    # 2. Preparar datos para OpenAI
    # Seleccionar una muestra representativa de comentarios
    sample_comments = []
    if total > 0:
        # Tomar hasta 8 comentarios representativos (2 positivos, 2 negativos, 2 neutrales, 2 mixtos)
        sample_size = min(total, 8)
        sample_comments = random.sample(comments, sample_size)
    
    # Crear prompt para OpenAI
    prompt = f"""
    Eres un experto en análisis de reputación digital. Analiza los comentarios sobre {influencer_name} 
    y proporciona un informe detallado que incluya:

    1. Karma Score: Una puntuación general de reputación (0-100) basada en el sentimiento de los comentarios.
    - Considera la distribución de sentimientos
    - Considera la intensidad de los sentimientos (score)
    - Considera la relevancia de los temas mencionados

    2. Recomendación: Un análisis detallado con recomendaciones estratégicas para mejorar la reputación.
    - Identifica patrones clave en los comentarios positivos y negativos
    - Sugiere acciones concretas para capitalizar lo positivo y mitigar lo negativo
    - Proporciona un plan de acción a corto y largo plazo

    Datos de análisis:
    - Total de comentarios: {total}
    - Comentarios positivos: {len(pos)} ({round(len(pos)/total*100, 1)}%)
    - Comentarios negativos: {len(neg)} ({round(len(neg)/total*100, 1)}%)
    - Comentarios neutrales: {len(neu)} ({round(len(neu)/total*100, 1)}%)
    - Puntuación promedio: {round(avg_score, 2)}

    Ejemplos de comentarios:
    {format_sample_comments(sample_comments)}

    Formato de respuesta EXACTO:
    Karma: [puntuación 0-100]
    Recomendación: [texto plano (no markdown) con extension corta-media con análisis y recomendaciones]
    """
    # 3. Obtener análisis de OpenAI
    try:
        gpt = OpenAIClient()
        response_text = gpt.get_completion(prompt)
        
        # Parsear la respuesta
        karma_score = None
        recommendation = ""
        
        if "Karma:" in response_text and "Recomendación:" in response_text:
            karma_part = response_text.split("Karma:")[1].split("Recomendación:")[0].strip()
            karma_score = extract_karma_score(karma_part)
            
            recommendation = response_text.split("Recomendación:")[1].strip()
        else:
            # Si el formato no es correcto, usar la respuesta completa como recomendación
            recommendation = response_text
            karma_score = calculate_fallback_karma(len(pos), len(neg), len(neu), avg_score)
            
    except Exception as e:
        print(f"Error al obtener análisis de OpenAI: {str(e)}")
        # Fallback a cálculo básico si OpenAI falla
        karma_score = calculate_fallback_karma(len(pos), len(neg), len(neu), avg_score)
        recommendation = generate_fallback_recommendation(karma_score, len(pos), len(neg), len(neu))

    # Generar nube de palabras
    texts = [c['text'] for c in comments]
    wordcloud_img = generate_wordcloud(texts)

    # 4. Preparar respuesta
    return jsonify({
        "total": total,
        "positive": len(pos),
        "neutral": len(neu),
        "negative": len(neg),
        "average_score": avg_score,
        "karma_score": karma_score,
        "recommendation": recommendation,
        "wordcloud": wordcloud_img
    }), 200

# Funciones auxiliares
def format_sample_comments(comments):
    """Formatea comentarios para incluirlos en el prompt"""
    formatted = []
    for i, comment in enumerate(comments):
        formatted.append(f"{i+1}. [{comment['sentiment']} - {comment['score']:.2f}] {comment['text'][:150]}{'...' if len(comment['text']) > 150 else ''}")
    return "\n".join(formatted)

def extract_karma_score(text):
    """Extrae el valor numérico del karma del texto"""
    try:
        # Buscar números en el texto
        numbers = re.findall(r'\d+', text)
        if numbers:
            score = int(numbers[0])
            return min(max(score, 0), 100)  # Asegurar que esté entre 0-100
    except:
        pass
    return None

def calculate_fallback_karma(pos, neg, neu, avg_score):
    """Calculo alternativo de karma si falla OpenAI"""
    # Fórmula: (positivos + 0.5*neutrales) / total * 100
    # Ajustado por la intensidad promedio del sentimiento
    if (pos + neg + neu) == 0:
        return 50
    
    base_score = (pos + 0.5 * neu) / (pos + neg + neu) * 100
    # Ajustar según la intensidad promedio (-1 a 1 -> -25 a 25 puntos)
    intensity_adjustment = avg_score * 25
    return max(0, min(100, base_score + intensity_adjustment))

def generate_fallback_recommendation(karma_score, pos, neg, neu):
    """Genera recomendación básica si falla OpenAI"""
    if karma_score >= 70:
        return (
            "La percepción general es positiva. Recomendamos: "
            "1. Continuar con las estrategias actuales que generan buena percepción\n"
            "2. Resaltar los aspectos positivos en comunicaciones oficiales\n"
            "3. Monitorear comentarios negativos para detectar áreas de mejora puntuales"
        )
    elif karma_score >= 40:
        return (
            "La percepción es neutral. Recomendamos: "
            "1. Identificar los aspectos más mencionados para mejorar\n"
            "2. Desarrollar campañas para fortalecer la imagen positiva\n"
            "3. Responder a comentarios negativos con soluciones concretas"
        )
    else:
        return (
            "La percepción es negativa. Recomendamos: "
            "1. Realizar un análisis profundo de las críticas recurrentes\n"
            "2. Implementar un plan de comunicación para abordar las preocupaciones\n"
            "3. Considerar cambios estratégicos basados en los comentarios más negativos"
        )
    
def generate_wordcloud(texts):
    # Unir todos los comentarios
    all_text = " ".join(texts)
    
    # Crear y configurar wordcloud
    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color='white',
        max_words=100,
        colormap='viridis'
    ).generate(all_text)
    
    # Guardar en buffer
    buffer = BytesIO()
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    
    # Convertir a base64
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"