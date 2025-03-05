from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from utils import ArticleRecommendationFacade, dump_db_jsonl
import uuid
from db import mongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os
from datetime import datetime, timezone
import pandas as pd
import random

app = Flask(__name__)

# Initialize the facade with the provided paths
facade = ArticleRecommendationFacade('data/combined_articles_recommendations.csv', 'data/articles_big_dataset.csv')

load_dotenv()
app.secret_key = os.getenv('EXPERT_STUDY_SECRET_KEY')

# MongoDB configuration
app.config["MONGO_URI"] = os.getenv('MONGODB_URI')

# Use predetermined flow for the expert study
app.config['USE_PREDETERMINED_FLOW'] = True

# Initialize PyMongo
mongo.init_app(app)

# Helper function to compute data for progress bar
def compute_progress(doc, predetermined_articles):
    """
    Build a list of articles (in the order of predetermined_articles) with a 'progress' attribute:
    'none', 'partial', or 'full', based on how many recommendations have been rated.
    """
    progress_list = []

    for article_uuid in predetermined_articles:
        # Retrieve the article metadata from your facade:
        article = facade.get_article(article_uuid)
        if not article:
            # If for some reason the facade can't find this article, skip
            continue

        # Extract relevant info for the progress state
        feedback_for_this_article = {}
        if doc and "feedback" in doc and article_uuid in doc["feedback"]:
            feedback_for_this_article = doc["feedback"][article_uuid]

        recs_for_this_article = facade.get_recommendations(article_uuid)

        total_recs = len(recs_for_this_article)
        rated_count = len(feedback_for_this_article)

        if rated_count == 0:
            state = "none"
        elif rated_count < total_recs:
            state = "partial"
        else:
            state = "full"

        progress_list.append({
            "uuid": article_uuid,
            "title": article.title,
            "progress": state
        })

    return progress_list

@app.before_request
def assign_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

@app.route('/catalogue')
def home():
    # Convert creation_date to a proper datetime type
    facade.testset_articles_df['creation_date'] = pd.to_datetime(
        facade.testset_articles_df['creation_date'], errors='coerce'
    )

    # Sort by creation_date descending.
    sorted_df = facade.testset_articles_df.sort_values(by='creation_date', ascending=False)

    articles_list = sorted_df[['uuid', 'title', 'section']].to_dict('records')

    return render_template('home.html', articles=articles_list)

# New endpoint to start the predetermined flow
@app.route('/')
def start_predetermined():
    app.config['USE_PREDETERMINED_FLOW'] = True
    # Generate the predetermined articles list once per session
    if 'predetermined_articles' not in session:
        # Get all article uuids from the testset articles DataFrame
        articles = facade.testset_articles_df['uuid'].tolist()
        session_id = session.get('session_id')
        # Seed the random generator with a hash of the session_id
        seed = hash(session_id)  # {{ edit_2 }}
        random.Random(seed).shuffle(articles)  # {{ edit_3 }}
        session['predetermined_articles'] = articles  # {{ edit_4 }}

    predetermined_articles = session['predetermined_articles']
    first_article = predetermined_articles[0] if predetermined_articles else None
    return redirect(url_for('article_recommendations', article_id=first_article))

@app.route('/article/<string:article_id>')
def article_recommendations(article_id):
    result = facade.get_article(article_id)
    recommendations = facade.get_recommendations(article_id)
    related_articles = set(result.cleaned_related_articles)
    recommended_articles = set(rec.uuid for rec in recommendations)
    missed_article_ids = related_articles - recommended_articles
    missed_articles = [facade.get_article(aid) for aid in missed_article_ids]

    # Retrieve the predetermined list from the session
    predetermined_articles = session.get('predetermined_articles', [])

    # Grab the feedback doc from the database
    doc = mongo.db.feedback.find_one({"session_id": session.get('session_id')})

    # Pass predetermined_articles to the updated compute_progress
    progress = compute_progress(doc, predetermined_articles)

    return render_template(
        'article.html',
        article=result,
        recommendations=recommendations,
        missed_articles=missed_articles,
        use_predetermined_flow=app.config['USE_PREDETERMINED_FLOW'],
        predetermined_articles=predetermined_articles,
        progress=progress
    )

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

    return jsonify({'status': 'success'}), 200

@app.route('/sus', methods=['GET', 'POST'])
def sus():
    if request.method == 'POST':
        # Collect demographic info
        age = request.form.get('age')
        gender = request.form.get('gender')

        # Gather all SUS responses
        sus_responses = {}
        for i in range(1, 11):
            sus_key = f"sus_question{i}"
            sus_responses[sus_key] = request.form.get(sus_key)

        # Prepare data to store
        session_id = session.get('session_id')
        timestamp = datetime.now(timezone.utc).timestamp()

        # We store everything under "sus_feedback" in the same document in "feedback" collection
        sus_update_data = {
            "sus_feedback": {
                "timestamp": timestamp,
                "age": age,
                "gender": gender,
                "sus_responses": sus_responses
            }
        }

        # Update the document for this session
        mongo.db.feedback.update_one(
            {"session_id": session_id},
            {
                "$setOnInsert": {"session_id": session_id},
                "$set": sus_update_data
            },
            upsert=True
        )

        # Optionally dump after updating
        dump_db_jsonl()

        return "Takk for at du svarte på undersøkelsen!"
    else:
        return render_template('sus.html')

@app.route('/get_rating_count', methods=['GET'])
def get_rating_count():
    session_id = session.get('session_id')
    doc = mongo.db.feedback.find_one({"session_id": session_id})

    count = 0
    # If we have feedback, count how many recommendation-level feedback entries there are
    if doc and "feedback" in doc:
        for article_id, recommendations in doc["feedback"].items():
            # Each article has a dict of recommendations, so add up their length
            count += len(recommendations)

    return jsonify({'count': count})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
