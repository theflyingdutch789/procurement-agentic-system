import {
  showLoginForm,
  showRegisterForm,
  handleLogin,
  handleRegister,
} from './auth.js';
import {
  setQuery,
  handleSendMessage,
  handleInputKeydown,
  toggleSidebar,
} from './chat.js';
import { initApp } from './app.js';

function bindAuthUI() {
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', (event) => {
      handleLogin(event);
    });
  }

  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.addEventListener('submit', (event) => {
      handleRegister(event);
    });
  }

  const toRegisterLink = document.querySelector('[data-action="show-register"]');
  if (toRegisterLink) {
    toRegisterLink.addEventListener('click', (event) => {
      event.preventDefault();
      showRegisterForm();
    });
  }

  const toLoginLink = document.querySelector('[data-action="show-login"]');
  if (toLoginLink) {
    toLoginLink.addEventListener('click', (event) => {
      event.preventDefault();
      showLoginForm();
    });
  }
}

function bindChatUI() {
  const exampleButtons = document.querySelectorAll('[data-example-query]');
  exampleButtons.forEach((button) => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      setQuery(button.dataset.exampleQuery || button.textContent.trim());
    });
  });

  const messageInput = document.getElementById('message-input');
  if (messageInput) {
    messageInput.addEventListener('keydown', handleInputKeydown);
  }

  const chatForm = document.querySelector('.chat-input-form');
  if (chatForm) {
    chatForm.addEventListener('submit', (event) => {
      handleSendMessage(event);
    });
  }

  const mobileToggle = document.querySelector('.mobile-menu-toggle');
  if (mobileToggle) {
    mobileToggle.addEventListener('click', (event) => {
      event.preventDefault();
      toggleSidebar();
    });
  }

  // Mobile sidebar close button
  const mobileSidebarClose = document.getElementById('mobile-sidebar-close');
  if (mobileSidebarClose) {
    mobileSidebarClose.addEventListener('click', (event) => {
      event.preventDefault();
      toggleSidebar(); // Close the sidebar
    });
  }

  // Sidebar backdrop (click outside to close)
  const sidebarBackdrop = document.getElementById('sidebar-backdrop');
  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', (event) => {
      event.preventDefault();
      toggleSidebar(); // Close the sidebar
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  bindAuthUI();
  bindChatUI();
  initApp();
});
