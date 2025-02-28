// static/predetermined.js

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
    prevButton.textContent = 'Previous';
    prevButton.style.marginRight = '10px';
    prevButton.disabled = (currentIndex <= 0); // Disable if at the first article
    navContainer.appendChild(prevButton);

    // Create Next Button
    var nextButton = document.createElement('button');
    nextButton.textContent = 'Next';
    nextButton.style.marginLeft = '10px';
    nextButton.disabled = (currentIndex === -1 || currentIndex >= predeterminedArticles.length - 1);
    navContainer.appendChild(nextButton);

    // Optionally, create a Finish button if at the end of the list
    var finishButton = document.createElement('button');
    finishButton.textContent = 'Finish';
    finishButton.style.marginLeft = '20px';
    finishButton.style.display = (currentIndex === predeterminedArticles.length - 1) ? 'inline-block' : 'none';
    navContainer.appendChild(finishButton);

    // Event listener for Previous
    prevButton.addEventListener('click', function () {
        if (currentIndex > 0) {
            var prevArticleId = predeterminedArticles[currentIndex - 1];
            // Redirect to the article details page for the previous article.
            // Adjust the URL pattern according to your route structure.
            window.location.href = '/article/' + prevArticleId;
        }
    });

    // Event listener for Next
    nextButton.addEventListener('click', function () {
        if (currentIndex >= 0 && currentIndex < predeterminedArticles.length - 1) {
            var nextArticleId = predeterminedArticles[currentIndex + 1];
            window.location.href = '/article/' + nextArticleId;
        }
    });

    // Event listener for Finish
    finishButton.addEventListener('click', function () {
        // Redirect to a finish page or back to the home page as desired.
        window.location.href = '/';
    });
});