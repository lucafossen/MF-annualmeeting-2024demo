import { showDropdownNotification } from './dropdown.js';
// Show overlay on the first visit
window.addEventListener('load', () => {
        if (!localStorage.getItem('shownOverlay')) {
            document.getElementById('instructionsOverlay').style.display = 'block';
        }
    });
// Move the startHintTimer function to global scope so it can be accessed by hideOverlay()
function startHintTimer() {
    const scrollHint = document.getElementById('scrollHint');
    const hintAlreadyShown = localStorage.getItem('scrollHintShown');

    function hasScrolledSmallArticles() {
        const smallArticlesSection = document.querySelector('.small-articles-section');
        if (smallArticlesSection) {
            const rect = smallArticlesSection.getBoundingClientRect();
            return rect.bottom <= (window.innerHeight || document.documentElement.clientHeight);
        }
        return false;
    }

    if (!hintAlreadyShown) {
        // After 5 seconds, if the user hasn't scrolled yet, show the hint.
        const hintTimeout = setTimeout(() => {
            if (!hasScrolledSmallArticles()) {
                scrollHint.classList.add('visible');
            }
        }, 5000);

        // When user scrolls, hide the hint (if visible) and set a flag.
        function onUserScroll() {
            if (hasScrolledSmallArticles()) {
                scrollHint.classList.remove('visible');
                localStorage.setItem('scrollHintShown', 'true');
                window.removeEventListener('scroll', onUserScroll);
            }
        }
        window.addEventListener('scroll', onUserScroll);
    }
}

function hideOverlay() {
    document.getElementById('instructionsOverlay').style.display = 'none';
    localStorage.setItem('shownOverlay', 'true');

    // Start the hint timer after the overlay is closed
    startHintTimer();
}

var ratingThreshold = 20;
document.addEventListener('DOMContentLoaded', function () {
    const susButton = document.getElementById('susButton');
    const submitAllButton = document.getElementById('submitAll');
    const ratingStatus = document.getElementById('ratingStatus');
    const companyForm = document.getElementById('companyForm');

    // 1. On page load, populate each recommendation’s input values from localStorage
    function loadRecommendationsFromLocalStorage() {
        const recommendations = document.querySelectorAll('.recommendation-item');
        recommendations.forEach((recItem) => {
            const ratingSelect = recItem.querySelector('.rating-input');
            const commentField = recItem.querySelector('.feedback-comment');

            // We'll build a key based on IDs
            const articleId = ratingSelect.getAttribute('data-article-id');
            const recId = ratingSelect.getAttribute('data-rec-id');
            const storageKey = `feedback_${articleId}_${recId}`;

            // Retrieve data from localStorage
            const storedData = localStorage.getItem(storageKey);
            if (storedData) {
                const { rating, comment } = JSON.parse(storedData);
                if (rating) ratingSelect.value = rating;
                if (comment) commentField.value = comment;
            }
        });
    }

    // 2. Whenever the user changes a rating or comment, store in localStorage
    function attachInputListeners() {
        const recommendations = document.querySelectorAll('.recommendation-item');
        recommendations.forEach((recItem) => {
            const ratingSelect = recItem.querySelector('.rating-input');
            const commentField = recItem.querySelector('.feedback-comment');

            const articleId = ratingSelect.getAttribute('data-article-id');
            const recId = ratingSelect.getAttribute('data-rec-id');
            const storageKey = `feedback_${articleId}_${recId}`;

            // Listen for change on the rating dropdown
            ratingSelect.addEventListener('change', () => {
                saveToLocalStorage(storageKey, ratingSelect.value, commentField.value);
            });

            // Listen for input changes in the comment box
            commentField.addEventListener('input', () => {
                saveToLocalStorage(storageKey, ratingSelect.value, commentField.value);
            });
        });
    }

    function saveToLocalStorage(storageKey, rating, comment) {
        localStorage.setItem(storageKey, JSON.stringify({ rating, comment }));
    }

    if (companyForm) {
        companyForm.addEventListener('submit', function (event) {
            event.preventDefault(); // Prevent actual form submission
            const companyValue = document.getElementById('companyInput').value.trim();

            fetch('/store_company', {
                method: 'POST',
                headers: {
                'Content-Type': 'application/json'
                },
                body: JSON.stringify({ company: companyValue })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Company info saved:', data);
                // Once saved, hide the overlay and do not reload the page
                hideOverlay();
            })
            .catch(err => {
                console.error('Error storing company info:', err);
                // Even if error, you could choose to hide the overlay or not
                hideOverlay();
            });
        });
    }

    fetch('/get_user_feedback')
        .then(response => response.json())
        .then(feedbackData => {
            const recommendations = document.querySelectorAll('.recommendation-item');

            recommendations.forEach((recItem) => {
                const ratingSelect = recItem.querySelector('.rating-input');
                const articleId = ratingSelect.getAttribute('data-article-id');
                const recId = ratingSelect.getAttribute('data-rec-id');

                // If there's an existing rating for articleId->recId, turn green
                if (
                    feedbackData[articleId] &&
                    feedbackData[articleId][recId] &&
                    feedbackData[articleId][recId].rating
                ) {
                    const feedbackSection = recItem.querySelector('.feedback-section');
                    if (feedbackSection) {
                        feedbackSection.style.backgroundColor = 'green';
                    }
                }
            });
        })
        .catch(error => console.error('Error fetching user feedback:', error));

    function submitAllFeedback() {
        return new Promise((resolve, reject) => {
            const recommendations = document.querySelectorAll('.recommendation-item');
            let feedbackItems = [];

            recommendations.forEach((recItem) => {
                const ratingSelect = recItem.querySelector('.rating-input');
                const commentField = recItem.querySelector('.feedback-comment');

                const articleId = ratingSelect.getAttribute('data-article-id');
                const recId = ratingSelect.getAttribute('data-rec-id');
                const ratingValue = ratingSelect.value;
                const commentValue = commentField.value.trim();

                if (ratingValue) {
                    feedbackItems.push({
                        article_id: articleId,
                        recommendation_id: recId,
                        rating: ratingValue,
                        comment: commentValue,
                        domElement: recItem
                    });
                }
            });

            // if (feedbackItems.length === 0) {
            //     alert('Please select at least one rating before submitting.');
            //     // We resolve anyway so navigation can continue
            //     resolve();
            //     return;
            // }

            // Submit each feedback via fetch, and wait for them all
            let fetchPromises = feedbackItems.map((feedbackObj) => {
                return fetch('/feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        article_id: feedbackObj.article_id,
                        recommendation_id: feedbackObj.recommendation_id,
                        rating: feedbackObj.rating,
                        comment: feedbackObj.comment
                    })
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Feedback submitted:', data);
                    // Turn green once successfully submitted
                    const section = feedbackObj.domElement.querySelector('.feedback-section');
                    if (section) {
                        section.style.backgroundColor = 'green';
                    }
                    // Optionally show a dropdown “Saved!” message
                    showDropdownNotification('Lagret!', '#4c77ce', '#ffffff', 2000);
                    updateSusButton();
                })
                .catch(error => console.error('Error:', error));
            });

            // Once all fetches are done, resolve
            Promise.all(fetchPromises).then(() => resolve());
        });
    }

    // Expose it to window so predetermined.js can call it
    window.submitAllFeedback = submitAllFeedback;

    function updateSusButton() {
        fetch('/get_rating_count')
            .then(response => response.json())
            .then(data => {
                const count = data.count || 0;
                if (count >= ratingThreshold) {
                    console.log('Rating threshold reached:', count);
                    ratingStatus.innerHTML = `Tusen takk! Du har vurdert <b>${count}</b> artikler. Fortsett gjerne å vurdere, eller gå videre til spørreskjemaet.`;
                    susButton.disabled = false;
                    susButton.style.backgroundColor = '#00b613';
                    susButton.style.cursor = 'pointer';
                    susButton.innerText = 'Gå videre til spørreskjemaet';
                    susButton.addEventListener('click', () => {
                        submitAllFeedback().then(() => {
                            window.location.href = '/sus';
                        });
                    });
                } else {
                    ratingStatus.innerText = `Vennligst vurder ${ratingThreshold - count} flere anbefalinger for å låse opp spørreskjemaet`;
                    susButton.innerText = `${ratingThreshold - count} igjen`;
                }
            })
            .catch(error => {
                console.error('Kan ikke hente vurderingstelling:', error);
            });
    }


    // Call your new localStorage functions
    loadRecommendationsFromLocalStorage();
    attachInputListeners();

    // Initial call to update the SUS button on page load
    updateSusButton();
});