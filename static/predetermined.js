// static/predetermined.js

// ... existing code ...
document.addEventListener('DOMContentLoaded', function () {
    // Create a container div for navigation if it doesn't exist
    var navContainer = document.getElementById('navigation-buttons');
    if (!navContainer) {
        navContainer = document.createElement('div');
        navContainer.id = 'navigation-buttons';
        navContainer.style.marginTop = '20px';
        navContainer.style.textAlign = 'center';
        document.body.appendChild(navContainer);
    }

    // Create Previous Button
    var prevButton = document.createElement('button');
    prevButton.textContent = 'Forrige';
    prevButton.className = 'btn';
    prevButton.style.position = 'fixed';
    prevButton.style.left = '10px';
    prevButton.style.top = '50%';
    prevButton.style.transform = 'translateY(-50%)';
    // Hide button when at first index
    if (currentIndex <= 0) {
        prevButton.style.display = 'none';
    }
    document.body.appendChild(prevButton);

    // Create Next Button
    var nextButton = document.createElement('button');
    nextButton.textContent = 'Neste';
    nextButton.className = 'btn';
    nextButton.style.position = 'fixed';
    nextButton.style.right = '10px';
    nextButton.style.top = '50%';
    nextButton.style.transform = 'translateY(-50%)';
    // Hide the next button if at the last index
    if (currentIndex === -1 || currentIndex >= predeterminedArticles.length - 1) {
        nextButton.style.display = 'none';
    }
    document.body.appendChild(nextButton);

    // Event listener for Previous
    prevButton.addEventListener('click', function () {
        // 1) Submit feedback
        submitAllFeedback().then(() => {
            // 2) Now do the existing "go to previous" logic
            if (currentIndex > 0) {
                var prevArticleId = predeterminedArticles[currentIndex - 1];
                window.location.href = '/article/' + prevArticleId;
            }
        });
    });

    // Event listener for Next
    nextButton.addEventListener('click', function () {
        // 1) Submit feedback
        submitAllFeedback().then(() => {
            // 2) Now do the existing "go to next" logic
            if (currentIndex >= 0 && currentIndex < predeterminedArticles.length - 1) {
                var nextArticleId = predeterminedArticles[currentIndex + 1];
                window.location.href = '/article/' + nextArticleId;
            }
        });
    });

});