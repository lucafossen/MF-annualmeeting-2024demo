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
import time

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
def compute_progress(doc, predetermined_articles, article_id):
    """
    Build a list of articles (in the order of predetermined_articles) with a 'progress' attribute:
    'none', 'partial', or 'full'.
    Then return only the subset of articles up to the last partial/full plus 10 more.
    """
    start_time = time.time()  # Start timing

    progress_list = []

    # 1. Determine progress state for each article
    for article_uuid in predetermined_articles:

        # Feedback for this article
        feedback_for_article = {}
        if doc and "feedback" in doc and article_uuid in doc["feedback"]:
            feedback_for_article = doc["feedback"][article_uuid]

        total_recs = 5 # Hard coded but should be a constant
        rated_count = len(feedback_for_article)

        if rated_count == 0:
            state = "none"
        elif rated_count < total_recs:
            state = "partial"
        else:
            state = "full"

        progress_list.append({
            "uuid": article_uuid,
            # "title": article.title,
            "progress": state
        })

    # 2. Find the last rated (partial or full) article's index
    last_rated_index = -1
    for i, article_info in enumerate(progress_list):
        if article_info["progress"] in ["partial", "full"]:
            last_rated_index = i

    # 3. Determine how many articles to return
    if last_rated_index == -1:
        # No articles are rated yet, so just show the first 10
        max_index = min(9, len(progress_list) - 1)
    else:
        # Show up to last_rated_index + 10
        max_index = min(last_rated_index + 10, len(progress_list) - 1)

    if article_id in predetermined_articles:
        article_index = predetermined_articles.index(article_id)
        if article_index > max_index:
            # If the current article is beyond the max_index, set max_index to the current article index
            max_index = article_index

    # 4. Slice the progress_list to keep only what we need to display
    subset_to_display = progress_list[:max_index + 1]

    end_time = time.time()  # End timing
    print(f"compute_progress took {end_time - start_time:.4f} seconds")

    return subset_to_display, last_rated_index, article_index

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

    # Generate the predetermined articles list once per session if not already set
    if 'predetermined_articles' not in session:
        # Get all article uuids from the testset articles DataFrame
        articles = facade.testset_articles_df['uuid'].tolist()
        session_id = session.get('session_id')
        # Seed the random generator with a hash of the session_id
        seed = hash(session_id)
        random.Random(seed).shuffle(articles)
        session['predetermined_articles'] = articles

    predetermined_articles = session['predetermined_articles']

    if not predetermined_articles:
        return "No articles available", 400

    # Get the feedback doc for this session
    doc = mongo.db.feedback.find_one({"session_id": session.get('session_id')})

    # Reuse compute_progress to determine the last rated article
    # We'll just pass the first article in predetermined_articles as 'article_id'
    # so that compute_progress can return last_rated_index.
    first_article = predetermined_articles[0]
    _, last_rated_index, _ = compute_progress(doc, predetermined_articles, first_article)

    # If no article is partially or fully rated, redirect to the first article;
    # otherwise, redirect to the last partially/fully rated one.
    if last_rated_index == -1:
        article_to_load = first_article
    else:
        article_to_load = predetermined_articles[last_rated_index]

    return redirect(url_for('article_recommendations', article_id=article_to_load))

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
    progress, _, progress_index = compute_progress(doc, predetermined_articles, article_id)
    print(f"Progress index: {progress_index}, type: {type(progress_index)}")
    return render_template(
        'article.html',
        article=result,
        recommendations=recommendations,
        missed_articles=missed_articles,
        use_predetermined_flow=app.config['USE_PREDETERMINED_FLOW'],
        predetermined_articles=predetermined_articles,
        progress=progress,
        progress_index=progress_index,
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

@app.route('/store_company', methods=['POST'])
def store_company():
    data = request.get_json(silent=True) or {}
    company = data.get('company', '').strip()

    # Get or create session_id
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id

    # Upsert into the feedback collection
    timestamp = datetime.now(timezone.utc).timestamp()
    mongo.db.feedback.update_one(
        {"session_id": session_id},
        {
            "$setOnInsert": {"session_id": session_id},
            "$set": {"company": company, "company_timestamp": timestamp}
        },
        upsert=True
    )

    return jsonify({"status": "success", "company": company})

@app.route('/get_user_feedback', methods=['GET'])
def get_user_feedback():
    session_id = session.get('session_id')
    doc = mongo.db.feedback.find_one({"session_id": session_id}) or {}
    # We only need to return the part under "feedback" if it exists
    feedback_data = doc.get('feedback', {})
    return jsonify(feedback_data)

@app.route('/sus', methods=['GET', 'POST'])
def sus():
    if request.method == 'POST':
        # Collect demographic info
        age = request.form.get('age')
        gender = request.form.get('gender')
        experience = request.form.get('experience')

        # Gather all SUS responses
        sus_responses = {}
        for i in range(1, 11):
            sus_key = f"sus_question{i}"
            sus_responses[sus_key] = request.form.get(sus_key)

        # Gather additional free-text feedback, if present
        additional_feedback = request.form.get('additional_feedback')

        # Prepare data to store
        session_id = session.get('session_id')
        timestamp = datetime.now(timezone.utc).timestamp()

        # We store everything under "sus_feedback" in the same document in "feedback" collection
        sus_update_data = {
            "sus_feedback": {
                "timestamp": timestamp,
                "age": age,
                "gender": gender,
                "experience": experience,
                "sus_responses": sus_responses,
                "additional_feedback": additional_feedback
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
