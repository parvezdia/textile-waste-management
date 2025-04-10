class NotificationHandler {
    constructor() {
        this.socket = null;
        this.badge = document.querySelector('.notification-badge');
        this.unreadCount = 0;
        this.connect();
        this.setupEventListeners();
    }

    connect() {
        const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsPath = `${wsScheme}://${window.location.host}/ws/notifications/`;
        
        this.socket = new WebSocket(wsPath);
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleNotification(data);
        };

        this.socket.onclose = () => {
            console.log('WebSocket connection closed. Attempting to reconnect...');
            setTimeout(() => this.connect(), 1000);
        };
    }

    setupEventListeners() {
        // Update unread count on page load
        fetch('/notifications/unread-count/')
            .then(response => response.json())
            .then(data => this.updateBadge(data.count));
    }

    handleNotification(data) {
        const { notification_type, message } = data;
        
        // Show notification using SweetAlert2
        showNotification(notification_type.toLowerCase(), message);
        
        // Update badge count
        this.unreadCount++;
        this.updateBadge(this.unreadCount);
    }

    updateBadge(count) {
        this.unreadCount = count;
        if (this.badge) {
            this.badge.textContent = count;
            this.badge.style.display = count > 0 ? 'block' : 'none';
        }
    }
}

// Initialize notification handler when document is ready
document.addEventListener('DOMContentLoaded', () => {
    new NotificationHandler();
});

// SweetAlert2 notification presets
const notificationPresets = {
    'ORDER_UPDATE': {
        icon: 'info',
        color: '#3085d6'
    },
    'PAYMENT_UPDATE': {
        icon: 'success',
        color: '#28a745'
    },
    'NEW_WASTE_AVAILABLE': {
        icon: 'info',
        color: '#17a2b8'
    },
    'DESIGN_UPDATE': {
        icon: 'info',
        color: '#6610f2'
    },
    'SYSTEM_NOTIFICATION': {
        icon: 'warning',
        color: '#ffc107'
    }
};

// Function to mark a notification as read
function markAsRead(notificationId) {
    fetch(`/notifications/mark-read/${notificationId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateNotificationCount();
            // Optionally remove or update the notification in the UI
            const notificationElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
            if (notificationElement) {
                notificationElement.classList.remove('unread');
            }
        }
    });
}

// Function to mark all notifications as read
function markAllAsRead() {
    fetch('/notifications/mark-all-read/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateNotificationCount();
            // Update UI to reflect all notifications are read
            document.querySelectorAll('.unread').forEach(elem => {
                elem.classList.remove('unread');
            });
            // Show success message
            showNotification('success', 'All notifications marked as read');
        }
    });
}