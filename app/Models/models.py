from datetime import datetime
import redis
import json

# Connect to Redis (adjust host/port/db if needed)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


class InfluencerRedis:
    @staticmethod
    def save(name):
        """Create or update influencer with current timestamp."""
        key = f"influencer:{name}"
        r.hset(key, mapping={
            'name': name,
            'last_scrape': datetime.utcnow().isoformat()
        })

    @staticmethod
    def get(name):
        """Retrieve influencer data."""
        key = f"influencer:{name}"
        return r.hgetall(key)

    @staticmethod
    def get_all():
        """Retrieve all influencers."""
        keys = r.keys("influencer:*")
        return [r.hgetall(k) for k in keys]
    @staticmethod
    def exists(name):
        """Check if influencer exists."""
        key = f"influencer:{name}"
        return r.exists(key)

class CommentRedis:
    @staticmethod
    def save_comment(comment_id, influencer_name, comment_data):
        # Save the comment itself
        r.set(f"comment:{comment_id}", json.dumps(comment_data))

        # Add reference to influencer's set of comments
        r.sadd(f"influencer_comments:{influencer_name}", comment_id)

    @staticmethod
    def get_comment(comment_id):
        data = r.get(f"comment:{comment_id}")
        return json.loads(data) if data else None

    @staticmethod
    def get_all_comments():
        keys = r.keys("comment:*")
        return [json.loads(r.get(k)) for k in keys]

    @staticmethod
    def get_comments_by_influencer(influencer_name):
        comment_ids = r.smembers(f"influencer_comments:{influencer_name}")
        comments = []
        for comment_id in comment_ids:
            cid = comment_id.decode('utf-8') if isinstance(comment_id, bytes) else comment_id
            if r.exists(f"comment:{cid}"):
                comments.append(json.loads(r.get(f"comment:{cid}")))
                print(f"[DEBUG] Tipo de comment_id: {type(comment_id)}, valor: {comment_id}")

        return comments

    @staticmethod
    def get_comments_by_influencer_and_platform(influencer_name, platform):
        comment_ids = r.smembers(f"influencer_comments:{influencer_name}")
        comments = []
        for comment_id in comment_ids:
            if r.exists(f"comment:{comment_id}"):
                comment = json.loads(r.get(f"comment:{comment_id}"))
                if comment.get("platform") == platform:
                    comments.append(comment)
        return comments

