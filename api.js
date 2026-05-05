const API_BASE = 'http://localhost:8000';

function getToken() {
    return localStorage.getItem('token');
}

function getRefreshToken() {
    return localStorage.getItem('refresh_token');
}

function getUser() {
    const raw = localStorage.getItem('user');
    try {
        return raw ? JSON.parse(raw) : null;
    } catch (error) {
        return null;
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    window.location.href = 'index.html';
}

async function apiRequest(endpoint, method = 'GET', body = null) {
    const token = getToken();
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, options);

    if (response.status === 401) {
        logout();
        return null;
    }

    let data = null;
    if (response.status !== 204) {
        try {
            data = await response.json();
        } catch (error) {
            data = null;
        }
    }

    return {
        ok: response.ok,
        status: response.status,
        data,
        json: async () => data,
    };
}

async function loadNotifications() {
    try {
        const response = await apiRequest('/notifications?unread=true');
        if (!response) return [];
        const data = await response.json();
        const count = data.unread_count || 0;
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'block' : 'none';
        }
        return data.data || [];
    } catch (error) {
        console.error('Error loading notifications:', error);
        return [];
    }
}

async function loadUserSettings() {
    try {
        const response = await apiRequest('/settings');
        if (!response) return null;
        const data = await response.json();
        return data.data || null;
    } catch (error) {
        console.error('Error loading settings:', error);
        return null;
    }
}

function requireAuth() {
    if (!getToken()) {
        window.location.href = 'index.html';
        return false;
    }
    return true;
}

function showNotification(message, type = 'info') {
    let notification = document.getElementById('notification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'notification';
        notification.className = 'notification';
        document.body.appendChild(notification);
    }
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    setTimeout(() => {
        notification.classList.remove('show');
    }, 4000);
}
