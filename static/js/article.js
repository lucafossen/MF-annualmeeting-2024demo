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

    submitAllButton.addEventListener('click', function (event) {
        event.preventDefault();

        // Gather all feedback
        const recommendations = document.querySelectorAll('.recommendation-item');
        let feedbackData = [];

        recommendations.forEach((recItem) => {
            const ratingSelect = recItem.querySelector('.rating-input');
            const commentField = recItem.querySelector('.feedback-comment');

            const articleId = ratingSelect.getAttribute('data-article-id');
            const recId = ratingSelect.getAttribute('data-rec-id');
            const ratingValue = ratingSelect.value;
            const commentValue = commentField.value.trim();

            // Check if user selected a rating
            if (ratingValue) {
                feedbackData.push({
                    article_id: articleId,
                    recommendation_id: recId,
                    rating: ratingValue,
                    comment: commentValue
                });
            }
        });

        if (feedbackData.length === 0) {
            alert('Please select at least one rating before submitting.');
            return;
        }

        // Send all feedback in a single batch of fetch calls
        feedbackData.forEach((feedback) => {
            fetch('/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(feedback)
            })
                .then(response => response.json())
                .then(data => {
                    console.log('Feedback submitted:', data);
                    updateSusButton();
                })
                .catch((error) => {
                    console.error('Error:', error);
                });
        });

        // Reset the fields
            recommendations.forEach((recItem) => {
                const ratingSelect = recItem.querySelector('.rating-input');
                const commentField = recItem.querySelector('.feedback-comment');

                // Only reset if a rating was selected
                if (ratingSelect.value) {
                    ratingSelect.value = '';
                    commentField.value = '';
                }
            });
    });

    function updateSusButton() {
        fetch('/get_rating_count')
            .then(response => response.json())
            .then(data => {
                const count = data.count || 0;

                if (count >= ratingThreshold) {
                    console.log('Rating threshold reached:', count);

                    const fullMessage = `Tusen takk! Du har vurdert ${count} artikler. Fortsett gjerne å vurdere, eller gå videre til spørreskjemaet.`;
                    showDropdownNotification(fullMessage, '#00b613', '#000000', 7000);

                    ratingStatus.innerText = `Tusen takk! Du har vurdert ${count} artikler. Fortsett gjerne å vurdere, eller gå videre til spørreskjemaet.`;
                    susButton.disabled = false;
                    susButton.style.backgroundColor = '#00b613';
                    susButton.style.cursor = 'pointer';
                    susButton.innerText = `Gå videre til spørreskjemaet`;
                    susButton.addEventListener('click', () => {
                        window.location.href = '/sus';
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

    // Initial call to update the SUS button on page load
    updateSusButton();
});