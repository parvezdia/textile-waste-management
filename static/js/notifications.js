// Fetch unread notifications count
function updateNotificationCount() {
    fetch('/notifications/count/')
        .then(response => response.json())
        .then(data => {
            const count = data.count;
            // Update any notification badges/counters here
            const notificationBadge = document.querySelector('.notification-badge');
            if (notificationBadge) {
                notificationBadge.textContent = count;
                notificationBadge.style.display = count > 0 ? 'inline' : 'none';
            }
        });
}

// Mark notification as read
function markAsRead(notificationId) {
    fetch(`/notifications/mark-read/${notificationId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateNotificationCount();
        }
    });
}

// Mark all notifications as read
function markAllAsRead() {
    fetch('/notifications/mark-all-read/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateNotificationCount();
            showNotification('success', 'All notifications marked as read');
        }
    });
}

// WebSocket connection for real-time notifications
let notificationSocket = null;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws/notifications/`;
    
    notificationSocket = new WebSocket(url);
    
    notificationSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.type === 'notification') {
            showNotification(data.notification_type.toLowerCase(), data.message);
            updateNotificationCount();
        }
    };

    notificationSocket.onclose = function() {
        setTimeout(connectWebSocket, 3000); // Reconnect after 3 seconds
    };
}

// Initialize notifications system
document.addEventListener('DOMContentLoaded', function() {
    updateNotificationCount();
    connectWebSocket();
});