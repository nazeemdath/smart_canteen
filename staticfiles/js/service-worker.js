self.addEventListener('push', function(event) {
    let notificationData = event.data ? event.data.json() : {};

    const title = notificationData.title || 'New Notification';
    const options = {
        body: notificationData.body || 'You have a new message.',
        icon: '/static/img/icon/heart.png',  // Add the path to your notification icon
        badge: '/path/to/your/badge.png'  // Optional: Path to a badge icon
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    // You can add actions like opening the app or navigating to a specific URL
    event.waitUntil(
        clients.openWindow("https://canteen.com/profile/status")
    );
});
