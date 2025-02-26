import pandas as pd
import ast
from scrape import get_image_src
import json
import os
from db import mongo
from datetime import datetime
import humanize

class Article:

    MISSING_IMAGE_URL = 'https://yt3.googleusercontent.com/-3Tg8kiLkkT7m1KZ8GhKP9Q8l0ar2xPCipW1Fpqrf0ZstSP1iejX5arX7HrBl2vmho4phtQ0=s900-c-k-c0x00ffffff-no-rj'

    def __init__(
        self,
        uuid,
        byline,
        title,
        lead_text,
        creation_date,
        last_modified,
        tags,
        url,
        image_url,
        body_text,
        related_articles,
        section,
        related_media_links,
        related_articles_counts,
        cleaned_related_articles,
        creation_time,
        number_cleaned_related_articles,
        all_text,
        # Optional values (only present in testset)
        full_text_embeddings='',
        recommendations_results='',
        recommendations='',
        ground_truth='',
        recall_at_5='',
        precision_at_5='',
        map_at_5='',
        # Optional values (only present in big dataset)
        recommendation_explanation='',
        recommendation_similarity='',
        recommendation_llm_rating='',
    ):
        self.uuid = uuid
        self.byline = byline
        self.title = title
        self.lead_text = lead_text
        self.creation_date = creation_date
        self.last_modified = last_modified
        self.tags = tags
        self.url = url
        self.image_url = image_url
        self.body_text = body_text
        self.related_articles = related_articles
        self.section = section
        self.related_media_links = related_media_links
        self.related_articles_counts = related_articles_counts
        self.cleaned_related_articles = cleaned_related_articles
        self.creation_time = creation_time
        self.number_cleaned_related_articles = number_cleaned_related_articles
        self.all_text = all_text
        self.full_text_embeddings = full_text_embeddings
        self.recommendations_results = recommendations_results
        self.recommendations = recommendations
        self.ground_truth = ground_truth
        self.recall_at_5 = recall_at_5
        self.precision_at_5 = precision_at_5
        self.map_at_5 = map_at_5
        self.recommendation_explanation = recommendation_explanation
        self.recommendation_similarity = recommendation_similarity
        self.recommendation_llm_rating = recommendation_llm_rating

class ArticleRecommendationFacade:
    def __init__(self, testset_articles: str, big_articles: str):
        # Load recommendations (testset) articles
        self.testset_articles_df = pd.read_csv(testset_articles)
        # Convert string representations of lists/dicts to actual lists/dicts for specific columns
        list_columns = ['byline','tags','related_articles','related_media_links','cleaned_related_articles','full_text_embeddings','recommendations', 'recommendations results']
        for col in list_columns:
            self.testset_articles_df[col] = self.testset_articles_df[col].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else []
            )

        # Load all articles
        self.big_articles_df = pd.read_csv(big_articles)
        # Convert string representations of lists/dicts to actual lists/dicts for specific columns
        # Essentially, the same as above, but without 'full_text_embeddings', 'recommendations'
        list_columns = ['byline','tags','related_articles','related_media_links','cleaned_related_articles']
        for col in list_columns:
            self.big_articles_df[col] = self.big_articles_df[col].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else []
            )

        # Optional caches for efficiency
        self.article_cache = {}
        self.recommendation_cache = {}

        self.feedback_file = 'data/feedback.json'
        # Load existing feedback
        if os.path.exists(self.feedback_file):
            with open(self.feedback_file, 'r') as f:
                self.feedback_data = json.load(f)
        else:
            self.feedback_data = {}

    def get_article(self, article_id: str):
        """Retrieve article details by ID."""
        # Check cache first
        if article_id in self.article_cache:
            return self.article_cache[article_id]

        # Search for article in both DataFrames
        testset_article_row = self.testset_articles_df[self.testset_articles_df['uuid'] == article_id]
        big_article_row = self.big_articles_df[self.big_articles_df['uuid'] == article_id]

        # Initialize article_data with big_articles data if available
        if not big_article_row.empty:
            article_data = big_article_row.iloc[0].to_dict()
        else:
            article_data = {}

        # Overwrite with testset_articles data if available
        if not testset_article_row.empty:
            testset_article_data = testset_article_row.iloc[0].to_dict()
            article_data.update(testset_article_data)

        article_object = Article(
            uuid=article_data.get('uuid', article_id),
            byline=article_data.get('byline', []),
            title=article_data.get('title', f'Article {article_id} Not Found'),
            lead_text=article_data.get('lead_text', ''),
            creation_date=pd.to_datetime(article_data.get('creation_date', ''), errors='coerce'),
            last_modified=pd.to_datetime(article_data.get('last_modified', ''), errors='coerce'),
            tags=article_data.get('tags', []),
            url=article_data.get('url', ''),
            image_url=(article_data.get('related_media_links')[0] if article_data.get('related_media_links') else Article.MISSING_IMAGE_URL),
            body_text=article_data.get('body_text', ''),
            related_articles=article_data.get('related_articles', []),
            section=article_data.get('section', ''),
            related_media_links=article_data.get('related_media_links', []),
            related_articles_counts=article_data.get('related_articles_counts', 0),
            cleaned_related_articles=article_data.get('cleaned_related_articles', []),
            creation_time=article_data.get('creation_time', ''),
            number_cleaned_related_articles=article_data.get('number_cleaned_related_articles', 0),
            all_text=article_data.get('all_text', ''),
            full_text_embeddings=article_data.get('full_text_embeddings', []),
            recommendations_results=article_data.get('recommendations_results', ''),
            recommendations=article_data.get('recommendations', []),
            ground_truth=article_data.get('ground_truth', ''),
            recall_at_5=article_data.get('recall_at_5', None),
            precision_at_5=article_data.get('precision_at_5', None),
            map_at_5=article_data.get('map_at_5', None)
        )
        self.article_cache[article_id] = article_object  # Cache for future access
        return article_object
        # else:
        #     return None  # Return None if not found

    def get_recommendations(self, article_id: str) -> list:
        """Retrieve recommendations for a given article ID."""
        # Check cache first
        if article_id in self.recommendation_cache:
            return self.recommendation_cache[article_id]

        results = []

        # Get the 'related_articles' field for the article
        original_article_row = self.testset_articles_df[self.testset_articles_df['uuid'] == article_id]
        if not original_article_row.empty:
            # Compute the original article's creation date once
            original_creation_date = pd.to_datetime(original_article_row.iloc[0].get('creation_date', ''), errors='coerce')
            print(f"Original creation date: {original_creation_date}")
            related_articles_field = original_article_row.iloc[0]['recommendations']
            if related_articles_field:
                # Loop through the related articles of the original article
                for article_id in related_articles_field:
                    recommended_article_row = self.big_articles_df[self.big_articles_df['uuid'] == article_id]
                    if recommended_article_row.empty:
                        article_data = {}
                    else:
                        article_data = recommended_article_row.iloc[0].to_dict()
                    # Get the specific recommendation details for the recommendation
                    for result in original_article_row.iloc[0]['recommendations results']:
                        if result[2] == article_id:
                            recommendation_llm_rating = result[0]
                            recommendation_similarity = int(round(result[3], 2)*100) # turn into percentage
                            recommendation_explanation = result[5]
                    # Calculate the age difference (in a human-readable format) between recommended and original article
                    rec_creation_date = pd.to_datetime(article_data.get('creation_date', ''), errors='coerce')
                    recommendation_age = None
                    if original_creation_date is not pd.NaT and rec_creation_date is not pd.NaT:
                        delta = rec_creation_date - original_creation_date
                        recommendation_age = humanize.naturaldelta(delta.to_pytimedelta())
                    print(f"Recommendation age: {recommendation_age}")
                    print("*"*50)
                    # Create the Article object as before
                    article_object = Article(
                    uuid=article_data.get('uuid', article_id),
                    byline=article_data.get('byline', []),
                    title=article_data.get('title', f'Article {article_id} Not Found'),
                    lead_text=article_data.get('lead_text', ''),
                    creation_date=pd.to_datetime(article_data.get('creation_date', ''), errors='coerce'),
                    last_modified=pd.to_datetime(article_data.get('last_modified', ''), errors='coerce'),
                    tags=article_data.get('tags', []),
                    url=article_data.get('url', ''),
                    image_url=(article_data.get('related_media_links')[0] if article_data.get('related_media_links') else Article.MISSING_IMAGE_URL),
                    body_text=article_data.get('body_text', ''),
                    related_articles=article_data.get('related_articles', []),
                    section=article_data.get('section', ''),
                    related_media_links=article_data.get('related_media_links', []),
                    related_articles_counts=article_data.get('related_articles_counts', 0),
                    cleaned_related_articles=article_data.get('cleaned_related_articles', []),
                    creation_time=article_data.get('creation_time', ''),
                    number_cleaned_related_articles=article_data.get('number_cleaned_related_articles', 0),
                    all_text=article_data.get('all_text', ''),
                    recommendation_explanation=recommendation_explanation,
                    recommendation_similarity=recommendation_similarity,
                    recommendation_llm_rating=recommendation_llm_rating,
                        )
                    # Attach the computed human-readable recommendation age to the recommended article object
                    article_object.recommendation_age = recommendation_age
                    results.append(article_object)

        self.recommendation_cache[article_id] = results # Cache
        return results

def dump_db_jsonl():
    """
    Dumps all user feedback to a JSON Lines (JSONL) file.
    """
    os.makedirs('db_dump', exist_ok=True)

    # Query all user preferences
    user_preferences = mongo.db.feedback.find()

    # Define the file path with a timestamp
    file_path = f'db_dump/dump_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.jsonl'

    # Write each feedback as a separate JSON line
    with open(file_path, 'w') as jsonl_file:
        for user_pref in user_preferences:
            # Remove the ObjectId as it is not JSON serializable by default
            user_pref['_id'] = str(user_pref['_id'])
            jsonl_file.write(json.dumps(user_pref) + '\n')
