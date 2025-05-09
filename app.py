from flask import Flask, render_template, request, jsonify, session
from utils import ArticleRecommendationFacade
import uuid
from dotenv import load_dotenv
import os
load_dotenv()

# Initialize the facade with the provided paths
facade = ArticleRecommendationFacade('data/combined_articles_recommendations.csv', 'data/articles_big_dataset.csv')

app = Flask(__name__)

app.secret_key = os.getenv('EXPERT_STUDY_SECRET_KEY', 'default')


@app.before_request
def assign_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

@app.route('/')
def home():
    articles_list = facade.testset_articles_df[['uuid', 'title', 'section']].to_dict('records')
    return render_template('home.html', articles=articles_list)

@app.route('/article/<string:article_id>')
def article_recommendations(article_id):
    # Use the facade to get article details and recommendations
    result = facade.get_article(article_id)
    recommendations = facade.get_recommendations(article_id)

    # Compute missed recommendations
    related_articles = set(result.cleaned_related_articles)
    recommended_articles = set(rec.uuid for rec in recommendations)
    missed_article_ids = related_articles - recommended_articles
    missed_articles = [facade.get_article(article_id) for article_id in missed_article_ids]
    # print(f'Missed articles: {missed_articles}')

    return render_template('article.html', article=result, recommendations=recommendations, missed_articles=missed_articles)

@app.route('/recommendation/<string:article_id>/<string:recommendation_id>')
def recommendation(article_id, recommendation_id):
    # Use the facade to get article details and recommendations
    article = facade.get_article(article_id)
    recommendations = facade.get_recommendations(article_id)

    # Find the recommendation with the matching recommendation_id
    recommendation = next((rec for rec in recommendations if rec.uuid == recommendation_id), None)

    return render_template('recommendation.html', article=article, recommendation=recommendation)

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.get_json()
    article_id = data.get('article_id')
    recommendation_id = data.get('recommendation_id')
    feedback_type = data.get('feedback')
    session_id = session.get('session_id')

    # Save feedback to the backend
    facade.save_feedback(article_id, recommendation_id, feedback_type, session_id)

    return jsonify({'status': 'success'}), 200

if __name__ == "__main__":
    app.run(debug=True)