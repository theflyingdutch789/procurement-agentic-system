/**
 * Authentication functions
 */

import { API_BASE } from './config.js';

// Show login form
export function showLoginForm() {
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('register-form').classList.add('hidden');
    document.getElementById('login-error').classList.add('hidden');
    document.getElementById('register-error').classList.add('hidden');
}

// Show register form
export function showRegisterForm() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('register-form').classList.remove('hidden');
    document.getElementById('login-error').classList.add('hidden');
    document.getElementById('register-error').classList.add('hidden');
}

// Handle login form submission
export async function handleLogin(event) {
    event.preventDefault();

    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const errorDiv = document.getElementById('login-error');

    // Get form data
    const username = form.username.value.trim();
    const password = form.password.value;

    // Disable submit button
    submitBtn.disabled = true;
    submitBtn.classList.add('btn-loading');
    errorDiv.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (data.success) {
            // Store user info
            localStorage.setItem('user', JSON.stringify(data.user));

            // Redirect to chat
            window.location.reload();
        } else {
            // Show error
            errorDiv.textContent = data.error || 'Login failed';
            errorDiv.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Login error:', error);
        errorDiv.textContent = 'Failed to connect to server';
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.classList.remove('btn-loading');
    }

    return false;
}

// Handle register form submission
export async function handleRegister(event) {
    event.preventDefault();

    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const errorDiv = document.getElementById('register-error');

    // Get form data
    const username = form.username.value.trim();
    const email = form.email.value.trim();
    const password = form.password.value;
    const full_name = form.full_name.value.trim();

    // Validate
    if (username.length < 3) {
        errorDiv.textContent = 'Username must be at least 3 characters';
        errorDiv.classList.remove('hidden');
        return false;
    }

    if (password.length < 6) {
        errorDiv.textContent = 'Password must be at least 6 characters';
        errorDiv.classList.remove('hidden');
        return false;
    }

    // Disable submit button
    submitBtn.disabled = true;
    submitBtn.classList.add('btn-loading');
    errorDiv.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ username, email, password, full_name })
        });

        const data = await response.json();

        if (data.success) {
            // Store user info
            localStorage.setItem('user', JSON.stringify(data.user));

            // Redirect to chat
            window.location.reload();
        } else {
            // Show error
            errorDiv.textContent = data.error || 'Registration failed';
            errorDiv.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Registration error:', error);
        errorDiv.textContent = 'Failed to connect to server';
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.classList.remove('btn-loading');
    }

    return false;
}

// Handle logout
export async function handleLogout() {
    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Logout error:', error);
    }

    // Clear local storage
    localStorage.removeItem('user');
    localStorage.removeItem('currentConversation');

    // Reload page
    window.location.reload();
}

// Check authentication status
export async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/auth/check`, {
            credentials: 'include'
        });

        const data = await response.json();
        return data.authenticated;
    } catch (error) {
        console.error('Auth check error:', error);
        return false;
    }
}

// Get current user info
export async function getCurrentUser() {
    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            credentials: 'include'
        });

        const data = await response.json();
        if (data.success) {
            return data.user;
        }
    } catch (error) {
        console.error('Get user error:', error);
    }
    return null;
}
