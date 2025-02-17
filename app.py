from flask import Flask, render_template, request, jsonify, session
from utils import ArticleRecommendationFacade, dump_db_jsonl
import uuid
from db import mongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os
from datetime import datetime, timezone
import pandas as pd

app = Flask(__name__)

# Initialize the facade with the provided paths
facade = ArticleRecommendationFacade('data/combined_articles_recommendations.csv', 'data/articles_big_dataset.csv')

load_dotenv()
app.secret_key = os.getenv('EXPERT_STUDY_SECRET_KEY')

# MongoDB configuration
app.config["MONGO_URI"] = os.getenv('MONGODB_URI')

# Initialize PyMongo
mongo.init_app(app)

@app.before_request
def assign_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

@app.route('/')
def home():
    # Convert creation_date to a proper datetime type
    facade.testset_articles_df['creation_date'] = pd.to_datetime(
        facade.testset_articles_df['creation_date'], errors='coerce'
    )

    # Sort by creation_date descending.
    sorted_df = facade.testset_articles_df.sort_values(by='creation_date', ascending=False)

    articles_list = sorted_df[['uuid', 'title', 'section']].to_dict('records')

    return render_template('home.html', articles=articles_list)

@app.route('/article/<string:article_id>')
def article_recommendations(article_id):
    result = facade.get_article(article_id)
    recommendations = facade.get_recommendations(article_id)

    related_articles = set(result.cleaned_related_articles)
    recommended_articles = set(rec.uuid for rec in recommendations)
    missed_article_ids = related_articles - recommended_articles
    missed_articles = [facade.get_article(aid) for aid in missed_article_ids]

    return render_template('article.html', article=result, recommendations=recommendations, missed_articles=missed_articles)

@app.route('/recommendation/<string:article_id>/<string:recommendation_id>')
def recommendation(article_id, recommendation_id):
    article = facade.get_article(article_id)
    recommendations = facade.get_recommendations(article_id)
    recommendation = next((rec for rec in recommendations if rec.uuid == recommendation_id), None)
    return render_template('recommendation.html', article=article, recommendation=recommendation)

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.get_json()
    article_id = data.get('article_id')
    recommendation_id = data.get('recommendation_id')
    rating = data.get('rating')
    comment = data.get('comment', '')
    session_id = session.get('session_id')
    timestamp = datetime.now(timezone.utc).timestamp()

    # Use dot notation to set nested feedback: session -> article id -> recommendation id
    feedback_field = f"feedback.{article_id}.{recommendation_id}"
    mongo.db.feedback.update_one(
        {"session_id": session_id},
        {
            "$setOnInsert": {"session_id": session_id},
            "$set": {feedback_field: {"rating": rating, "comment": comment, "timestamp": timestamp}}
        },
        upsert=True
    )

    dump_db_jsonl()
    return jsonify({'status': 'success'}), 200

if __name__ == "__main__":
    app.run(debug=True)
