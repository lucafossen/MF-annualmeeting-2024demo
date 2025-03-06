/**
 * Displays a dropdown notification with the given message.
 * @param {string} message - The message to display.
 */
export function showDropdownNotification(message, backgroundColor = '#4c77ce', textColor = '#ffffff', duration = 5000) {
    // Remove any existing notification
    const existingNotification = document.querySelector('.dropdown-notification');
    if (existingNotification) {
        existingNotification.remove();
    }

    // Create the notification element
    const notification = document.createElement('div');
    notification.classList.add('dropdown-notification');
    notification.textContent = message;

    // Set custom colors
    notification.style.backgroundColor = backgroundColor;
    notification.style.color = textColor;

    // Insert the notification at the root of the DOM
    document.body.appendChild(notification);

    // Automatically remove the notification after 5 seconds
    setTimeout(() => {
        notification.classList.add('slide-up');
        notification.addEventListener('animationend', () => {
            notification.remove();
        });
    }, duration);
}