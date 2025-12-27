import { checkAuth, getCurrentUser, showLoginForm } from './auth.js';
import { initChat, autoResizeTextarea } from './chat.js';

let isAuthenticated = false;
let currentUser = null;
let listenersInitialized = false;

export async function initApp() {
    const loadingScreen = document.getElementById('loading-screen');
    const authScreen = document.getElementById('auth-screen');
    const chatApp = document.getElementById('chat-app');

    try {
        if (!listenersInitialized) {
            setupGlobalListeners();
            listenersInitialized = true;
        }

        // Check authentication status
        isAuthenticated = await checkAuth();

        if (isAuthenticated) {
            // Get current user
            currentUser = await getCurrentUser();

            if (currentUser) {
                // Show chat app
                loadingScreen.classList.add('hidden');
                authScreen.classList.add('hidden');
                chatApp.classList.remove('hidden');

                // Update user info in UI
                const userNameEl = document.getElementById('user-name');
                if (userNameEl) {
                    userNameEl.textContent = currentUser.username;
                }

                // Initialize chat interface
                await initChat();
            } else {
                // User not found, show auth
                showAuthScreen();
            }
        } else {
            // Not authenticated, show auth screen
            showAuthScreen();
        }
    } catch (error) {
        console.error('App initialization error:', error);
        showAuthScreen();
    }
}

export function showAuthScreen() {
    const loadingScreen = document.getElementById('loading-screen');
    const authScreen = document.getElementById('auth-screen');
    const chatApp = document.getElementById('chat-app');

    loadingScreen.classList.add('hidden');
    chatApp.classList.add('hidden');
    authScreen.classList.remove('hidden');

    // Show login form by default
    showLoginForm();
}
function setupGlobalListeners() {
    // Handle textarea auto-resize on input
    const messageInput = document.getElementById('message-input');
    if (messageInput) {
        messageInput.addEventListener('input', (e) => {
            autoResizeTextarea(e.target);
        });
    }

    // Handle window resize to adjust textarea
    window.addEventListener('resize', () => {
        const activeInput = document.getElementById('message-input');
        if (activeInput) {
            autoResizeTextarea(activeInput);
        }
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (event) => {
        const sidebar = document.getElementById('sidebar');
        const menuToggle = document.querySelector('.mobile-menu-toggle');

        if (!sidebar || !menuToggle) return;

        const isClickInsideSidebar = sidebar.contains(event.target);
        const isClickOnToggle = menuToggle.contains(event.target);

        if (!isClickInsideSidebar && !isClickOnToggle && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
        }
    });

    // Handle escape key to close sidebar on mobile
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            const sidebar = document.getElementById('sidebar');
            if (sidebar && sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
            }
        }
    });

    // Online/offline logging
    window.addEventListener('online', () => console.log('Connection restored'));
    window.addEventListener('offline', () => console.log('Connection lost'));

    // Prevent zoom on double tap on iOS
    let lastTouchEnd = 0;
    document.addEventListener('touchend', (event) => {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
            event.preventDefault();
        }
        lastTouchEnd = now;
    }, false);

    // Add active class to forms when input is focused (for better mobile UX)
    document.addEventListener('focusin', (event) => {
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            const formGroup = event.target.closest('.form-group');
            if (formGroup) {
                formGroup.classList.add('active');
            }
        }
    });

    document.addEventListener('focusout', (event) => {
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            const formGroup = event.target.closest('.form-group');
            if (formGroup) {
                formGroup.classList.remove('active');
            }
        }
    });

    console.log('%cAI Database Assistant', 'font-size: 20px; font-weight: bold; color: #6366f1;');
    console.log('%cPowered by GPT-5 & MongoDB', 'font-size: 12px; color: #8b5cf6;');
    console.log('Version: 1.0.0');
    console.log('Environment:', window.location.hostname);
}
