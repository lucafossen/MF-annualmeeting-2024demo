# MediaFutures annual meeting demo

## Installation and running
1. Copy necessary files (`articles_big_dataset.csv` and `combined_articles_recommendations.csv`) into a new folder `data/`
2. Create a virtual environment and activate it
Note: you need to place  in the `data` folder before running (they were too big to push to github).

3. Configre a .env file:
```
EXPERT_STUDY_SECRET_KEY=any_secret_key
MONGODB_URI=mongodb://localhost:27017/mf_expert_study
```
4. install packages with `pip install -r requirements_all.txt`
5. run webapp with `python app.py` and open the IP address specified in the terminal

## Project Structure

- `app.py`: The main Flask application file and entry point to starting the web app.
- `utils.py`: Contains utility functions and classes for retrieving articles and recommendations.
- `templates/`: HTML templates using jinja2 templating for rendering web pages.
- `static/`: Static file like CSS for styling the web pages.