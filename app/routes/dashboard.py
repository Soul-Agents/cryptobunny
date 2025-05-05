import json
from flask import Blueprint, request, jsonify

from app.utils.db import get_db

# Create Blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/<client_id>', methods=['GET'])
def dashboard(client_id):
    """
    Get dashboard data for a client
    """
    try:
        db = get_db()
        auth_data = db.get_twitter_auth(client_id)
        
        if not auth_data:
            return jsonify({
                "status": "error",
                "message": "Not authenticated"
            }), 401
        
        # Get all agent configurations for the client
        configs = db.get_all_agent_configs(client_id)
        configs_json = json.loads(json.dumps(configs, default=str))
        
        # Get all agent templates from the database
        templates = {}
        template_configs = db.agent_config.find({}, {"agent_name": 1, "user_personality": 1, "model_config": 1})
        
        for config in template_configs:
            agent_name = config.get("agent_name")
            if agent_name and agent_name not in templates:
                templates[agent_name] = {
                    "name": agent_name,
                    "description": config.get("user_personality", "").split('\n')[0][:100] + "..." if config.get("user_personality") else "",
                    "model": config.get("model_config", {}).get("type", "unknown")
                }
        
        # Format user data for dashboard
        user_data = {
            "user_id": auth_data["user_id"],
            "user_name": auth_data["user_name"],
            "created_at": auth_data["created_at"],
            "updated_at": auth_data["updated_at"]
        }
        user_data_json = json.loads(json.dumps(user_data, default=str))
        
        return jsonify({
            "status": "success",
            "user": user_data_json,
            "agent_count": len(configs),
            "agents": configs_json,
            "templates": templates
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get dashboard data: {str(e)}"
        }), 500

@dashboard_bp.route('/stats/<client_id>', methods=['GET'])
def get_client_stats(client_id):
    """
    Get usage statistics for a client
    """
    try:
        db = get_db()
        auth_data = db.get_twitter_auth(client_id)
        
        if not auth_data:
            return jsonify({
                "status": "error",
                "message": "Not authenticated"
            }), 401
        
        # Get agent configurations for the client
        configs = db.get_all_agent_configs(client_id)
        
        # Get tweets and replies for all agents
        user_id = auth_data["user_id"]
        
        # Count tweets by month
        tweets_by_month = {}
        tweets = db.written_ai_tweets.find({"user_id": user_id})
        
        # Process tweets to count by month
        for tweet in tweets:
            created_at = tweet.get("created_at")
            if created_at:
                # Format month as YYYY-MM
                month_key = created_at.strftime("%Y-%m")
                if month_key in tweets_by_month:
                    tweets_by_month[month_key] += 1
                else:
                    tweets_by_month[month_key] = 1
        
        # Count replies by month
        replies_by_month = {}
        replies = db.written_ai_tweet_replies.find({"user_id": user_id})
        
        # Process replies to count by month
        for reply in replies:
            created_at = reply.get("created_at")
            if created_at:
                # Format month as YYYY-MM
                month_key = created_at.strftime("%Y-%m")
                if month_key in replies_by_month:
                    replies_by_month[month_key] += 1
                else:
                    replies_by_month[month_key] = 1
        
        # Calculate total activity stats
        total_tweets = db.written_ai_tweets.count_documents({"user_id": user_id})
        total_replies = db.written_ai_tweet_replies.count_documents({"user_id": user_id})
        
        stats = {
            "agent_count": len(configs),
            "tweet_count": total_tweets,
            "reply_count": total_replies,
            "total_activity": total_tweets + total_replies,
            "tweets_by_month": tweets_by_month,
            "replies_by_month": replies_by_month
        }
        
        return jsonify({
            "status": "success",
            "statistics": stats
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get statistics: {str(e)}"
        }), 500

@dashboard_bp.route('/activity/<client_id>', methods=['GET'])
def get_recent_activity(client_id):
    """
    Get recent activity for all agents owned by a client
    """
    try:
        db = get_db()
        auth_data = db.get_twitter_auth(client_id)
        
        if not auth_data:
            return jsonify({
                "status": "error",
                "message": "Not authenticated"
            }), 401
        
        # Get user ID
        user_id = auth_data["user_id"]
        
        # Get most recent tweets
        limit = int(request.args.get('limit', 10))
        tweets = db.get_last_written_ai_tweets(user_id, limit=limit)
        
        # Get most recent replies
        replies = db.get_last_written_ai_tweet_replies(user_id, limit=limit)
        
        # Format the data for JSON response
        tweets_json = json.loads(json.dumps(tweets, default=str))
        replies_json = json.loads(json.dumps(replies, default=str))
        
        # Combine and sort by timestamp (descending)
        all_activity = []
        
        for tweet in tweets_json:
            all_activity.append({
                "type": "tweet",
                "timestamp": tweet.get("created_at"),
                "data": tweet
            })
        
        for reply in replies_json:
            all_activity.append({
                "type": "reply",
                "timestamp": reply.get("created_at"),
                "data": reply
            })
        
        # Sort by timestamp (newest first)
        sorted_activity = sorted(
            all_activity, 
            key=lambda x: x.get("timestamp", ""), 
            reverse=True
        )
        
        return jsonify({
            "status": "success",
            "activity": sorted_activity[:limit]  # Return only the most recent activity
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get recent activity: {str(e)}"
        }), 500 