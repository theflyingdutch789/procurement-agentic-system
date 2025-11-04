/**
 * Chat functionality
 */

import { API_BASE } from './config.js';
import { DataVisualizer } from './visualizations.js';
import { handleLogout } from './auth.js';

let currentConversation = null;
let conversations = [];
let isLoading = false;
const DEFAULT_MAX_RESULTS = 10;

// Toggle sidebar (mobile)
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');

    sidebar.classList.toggle('open');

    // Toggle backdrop on mobile
    if (backdrop) {
        backdrop.classList.toggle('show');
    }
}

// Toggle sidebar collapse (desktop)
function toggleSidebarCollapse() {
    const sidebar = document.getElementById('sidebar');
    const isCollapsed = sidebar.classList.toggle('collapsed');

    // Save state to localStorage
    localStorage.setItem('sidebarCollapsed', isCollapsed);
}

// Restore sidebar collapse state on load
function restoreSidebarState() {
    const sidebar = document.getElementById('sidebar');
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';

    if (isCollapsed) {
        sidebar.classList.add('collapsed');
    }
}

// Create new conversation
async function createNewConversation() {
    console.log('[createNewConversation] Starting...');
    try {
        const response = await fetch(`${API_BASE}/chat/conversations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({})  // Send empty JSON object
        });

        console.log('[createNewConversation] Response status:', response.status);

        const data = await response.json();
        console.log('[createNewConversation] Response data:', data);

        if (data.success) {
            currentConversation = data.conversation;
            localStorage.setItem('currentConversation', JSON.stringify(currentConversation));

            // Clear messages
            clearMessages();

            // Update UI
            updateConversationTitle(currentConversation.title);
            await loadConversations();

            // Close sidebar on mobile
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.remove('open');

            // Focus input for immediate use
            const messageInput = document.getElementById('message-input');
            if (messageInput) {
                messageInput.focus();
            }

            console.log('[createNewConversation] Success!');
        } else {
            console.error('[createNewConversation] Failed:', data.error);
            showToast(data.error || 'Failed to create new conversation');
        }
    } catch (error) {
        console.error('[createNewConversation] Exception:', error);
        showToast('Failed to create new conversation. Please try again.');
    }
}

// Load conversations list
async function loadConversations() {
    try {
        const response = await fetch(`${API_BASE}/chat/conversations?limit=50`, {
            credentials: 'include'
        });

        const data = await response.json();
        if (data.success) {
            conversations = data.conversations;
            renderConversationsList();

            // Update stats
            await loadUserStats();
        }
    } catch (error) {
        console.error('Load conversations error:', error);
    }
}

// Render conversations list
function renderConversationsList() {
    const listContainer = document.getElementById('conversations-list');
    if (!listContainer) return;

    if (conversations.length === 0) {
        listContainer.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: var(--gray-500); font-size: 0.875rem;">
                No conversations yet.<br>Start a new chat!
            </div>
        `;
        return;
    }

    listContainer.innerHTML = conversations.map(conv => {
        const isActive = currentConversation && currentConversation._id === conv._id;
        const time = formatTime(conv.updated_at);

        return `
            <div class="conversation-item ${isActive ? 'active' : ''}" data-conversation-id="${conv._id}">
                <div class="conversation-content">
                    <div class="conversation-title">${escapeHtml(conv.title)}</div>
                    <div class="conversation-time">${time}</div>
                </div>
                <button class="conversation-delete-btn" data-conversation-id="${conv._id}" title="Delete conversation" aria-label="Delete conversation">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        <line x1="10" y1="11" x2="10" y2="17"></line>
                        <line x1="14" y1="11" x2="14" y2="17"></line>
                    </svg>
                </button>
            </div>
        `;
    }).join('');
}

// Load a specific conversation
async function loadConversation(conversationId) {
    try {
        const response = await fetch(`${API_BASE}/chat/conversations/${conversationId}`, {
            credentials: 'include'
        });

        const data = await response.json();
        if (data.success) {
            currentConversation = data.conversation;
            localStorage.setItem('currentConversation', JSON.stringify(currentConversation));

            // Render messages
            renderMessages();

            // Update title
            updateConversationTitle(currentConversation.title);

            // Close sidebar on mobile
            document.getElementById('sidebar').classList.remove('open');

            // Re-render list to update active state
            renderConversationsList();
        }
    } catch (error) {
        console.error('Load conversation error:', error);
    }
}

// Render messages in current conversation
function renderMessages() {
    console.log('[renderMessages] Starting...', currentConversation);
    const messagesContainer = document.getElementById('chat-messages');
    const welcomeMessage = document.getElementById('welcome-message');

    if (!messagesContainer) {
        console.error('[renderMessages] Messages container not found');
        return;
    }

    if (!currentConversation || !currentConversation.messages || currentConversation.messages.length === 0) {
        console.log('[renderMessages] No messages, showing welcome');
        // Clear all messages
        const children = Array.from(messagesContainer.children);
        children.forEach(child => {
            if (child.id !== 'welcome-message') {
                child.remove();
            }
        });

        // Show welcome message if it exists
        if (welcomeMessage) {
            welcomeMessage.classList.remove('hidden');
        } else {
            console.warn('[renderMessages] Welcome message element not found in DOM');
        }
        return;
    }

    console.log('[renderMessages] Rendering', currentConversation.messages.length, 'messages');

    // Hide welcome message
    if (welcomeMessage) {
        welcomeMessage.classList.add('hidden');
    }

    // Clear existing messages (but keep welcome message)
    const children = Array.from(messagesContainer.children);
    children.forEach(child => {
        if (child.id !== 'welcome-message') {
            child.remove();
        }
    });

    // Render all messages
    currentConversation.messages.forEach(msg => {
        // User message
        const userMsgEl = createMessageElement('user', msg.query, msg.timestamp);
        messagesContainer.appendChild(userMsgEl);

        // Assistant message
        const assistantMsg = createAssistantMessage(msg.response);
        const assistantMsgEl = createMessageElement('assistant', assistantMsg, msg.timestamp);
        messagesContainer.appendChild(assistantMsgEl);

        // Initialize visualizations for this message
        initializeVisualizations(assistantMsgEl);
    });

    // Scroll to bottom
    scrollToBottom();
    console.log('[renderMessages] Complete');
}

// Create message element
function createMessageElement(role, content, timestamp) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatarLetter = role === 'user' ? 'U' : 'AI';
    const authorName = role === 'user' ? 'You' : 'AI Assistant';
    const time = timestamp ? formatTime(timestamp) : '';

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarLetter}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">${authorName}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-bubble">${content}</div>
        </div>
    `;

    return messageDiv;
}

// Initialize visualizations in a message element
function initializeVisualizations(messageElement) {
    if (!DataVisualizer) {
        console.warn('[Chat] DataVisualizer not available');
        return;
    }

    const placeholders = messageElement.querySelectorAll('.visualization-placeholder');

    placeholders.forEach(placeholder => {
        try {
            // Decode HTML entities before parsing JSON
            const decodeHtml = (html) => {
                const txt = document.createElement('textarea');
                txt.innerHTML = html;
                return txt.value;
            };

            const results = JSON.parse(decodeHtml(placeholder.dataset.results));
            const analysis = JSON.parse(decodeHtml(placeholder.dataset.analysis));

            // Create visualization container
            const container = DataVisualizer.createVisualizationContainer(
                placeholder.id,
                analysis
            );

            if (container) {
                placeholder.replaceWith(container);

                // Render visualization after a brief delay to ensure DOM is ready
                setTimeout(() => {
                    DataVisualizer.renderVisualization(
                        placeholder.id,
                        results,
                        analysis
                    );
                }, 100);
            }
        } catch (error) {
            console.error('[Chat] Failed to initialize visualization:', error);
            console.error('[Chat] Error details:', error.message);
            console.error('[Chat] Stack trace:', error.stack);
            placeholder.innerHTML = `<div class="error-message">Failed to render visualization: ${error.message}</div>`;
        }
    });
}

// Create assistant message HTML from response
function createAssistantMessage(response) {
    let html = '';

    // Add answer if present
    if (response.answer) {
        html += `<div>${escapeHtml(response.answer)}</div>`;
    }

    // Add visualization if data is available (only for multiple results)
    if (response.results && response.results.length > 1 && DataVisualizer) {
        const vizId = `viz-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const analysis = DataVisualizer.analyzeData(response.results, response.pipeline);

        if (analysis.type !== 'none') {
            // Properly escape JSON for HTML attributes
            const resultsJson = JSON.stringify(response.results)
                .replace(/&/g, '&amp;')
                .replace(/'/g, '&apos;')
                .replace(/"/g, '&quot;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');

            const analysisJson = JSON.stringify(analysis)
                .replace(/&/g, '&amp;')
                .replace(/'/g, '&apos;')
                .replace(/"/g, '&quot;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');

            html += `<div id="${vizId}" class="visualization-placeholder"
                         data-results="${resultsJson}"
                         data-analysis="${analysisJson}">
                     </div>`;
        }
    }

    // Add result count if present
    if (response.result_count !== undefined) {
        html += `<div class="message-result-count">Found ${response.result_count} result(s)</div>`;
    }

    // Add pipeline if present (collapsible)
    if (response.pipeline && response.pipeline.length > 0) {
        html += `<details style="margin-top: 0.5rem;">
            <summary style="cursor: pointer; font-size: 0.875rem; color: var(--gray-600);">
                View MongoDB Pipeline
            </summary>
            <pre>${JSON.stringify(response.pipeline, null, 2)}</pre>
        </details>`;
    }

    // Add execution time
    if (response.execution_time_seconds) {
        html += `<div class="message-result-count">
            Executed in ${response.execution_time_seconds.toFixed(2)}s
        </div>`;
    }

    return html || 'No response';
}

// Clear messages in current conversation
function clearMessages() {
    const messagesContainer = document.getElementById('chat-messages');
    const welcomeMessage = document.getElementById('welcome-message');

    if (!messagesContainer) {
        console.error('[clearMessages] Messages container not found');
        return;
    }

    // Remove all messages except the welcome message
    const children = Array.from(messagesContainer.children);
    children.forEach(child => {
        if (child.id !== 'welcome-message') {
            child.remove();
        }
    });

    // Show welcome message
    if (welcomeMessage) {
        welcomeMessage.classList.remove('hidden');
    } else {
        console.warn('[clearMessages] Welcome message element not found');
    }
}

// Delete a specific conversation
async function deleteConversation(conversationId) {
    // Find the conversation being deleted
    const convToDelete = conversations.find(c => c._id === conversationId);
    if (!convToDelete) return;

    // Check if this is the only conversation
    const isOnlyConversation = conversations.length === 1;

    const confirmed = await showConfirmModal(
        isOnlyConversation ? 'Clear Conversation' : 'Delete Conversation',
        isOnlyConversation
            ? 'Are you sure you want to clear all messages in this conversation? This action cannot be undone.'
            : `Are you sure you want to delete "${convToDelete.title}"? This action cannot be undone.`
    );

    if (!confirmed) {
        return;
    }

    try {
        if (isOnlyConversation) {
            // Just clear the messages, keep the conversation
            console.log('[deleteConversation] Clearing conversation:', conversationId);

            const response = await fetch(
                `${API_BASE}/chat/conversations/${conversationId}/clear`,
                {
                    method: 'POST',
                    credentials: 'include'
                }
            );

            console.log('[deleteConversation] Clear response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[deleteConversation] Clear failed:', errorText);
                showToast('Failed to clear conversation', 'error');
                return;
            }

            const data = await response.json();
            console.log('[deleteConversation] Clear response data:', data);

            if (data.success) {
                // Reload conversations list to get updated title from backend
                console.log('[deleteConversation] Reloading conversations...');
                await loadConversations();

                // If this is the current conversation, reload it to get fresh data
                if (currentConversation && currentConversation._id === conversationId) {
                    console.log('[deleteConversation] Reloading current conversation');
                    await loadConversation(conversationId);
                }

                showToast('Conversation cleared successfully', 'success');
            } else {
                console.error('[deleteConversation] Clear failed:', data.error);
                showToast(data.error || 'Failed to clear conversation', 'error');
            }
        } else {
            // Delete the conversation completely
            console.log('[deleteConversation] Deleting conversation:', conversationId);

            const response = await fetch(
                `${API_BASE}/chat/conversations/${conversationId}`,
                {
                    method: 'DELETE',
                    credentials: 'include'
                }
            );

            console.log('[deleteConversation] Response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[deleteConversation] Delete failed:', errorText);
                showToast('Failed to delete conversation', 'error');
                return;
            }

            const data = await response.json();
            console.log('[deleteConversation] Response data:', data);

            if (data.success) {
                // Check if we're deleting the current conversation
                const isDeletingCurrent = currentConversation && currentConversation._id === conversationId;

                console.log('[deleteConversation] Is deleting current?', isDeletingCurrent);

                if (isDeletingCurrent) {
                    localStorage.removeItem('currentConversation');
                    currentConversation = null;
                }

                // Reload conversations list from server to get fresh data
                console.log('[deleteConversation] Reloading conversations...');
                await loadConversations();
                console.log('[deleteConversation] Conversations after reload:', conversations.length);

                // If we deleted the current conversation, load another or create new
                if (isDeletingCurrent) {
                    if (conversations.length > 0) {
                        console.log('[deleteConversation] Loading first conversation');
                        await loadConversation(conversations[0]._id);
                    } else {
                        console.log('[deleteConversation] Creating new conversation');
                        await createNewConversation();
                    }
                }

                showToast('Conversation deleted successfully', 'success');
            } else {
                console.error('[deleteConversation] Delete failed:', data.error);
                showToast(data.error || 'Failed to delete conversation', 'error');
            }
        }
    } catch (error) {
        console.error('Delete conversation error:', error);
        showToast('Failed to delete conversation', 'error');
    }
}


// Send message
async function handleSendMessage(event) {
    event.preventDefault();

    if (isLoading) return false;

    const input = document.getElementById('message-input');
    const question = input.value.trim();

    if (!question) return false;

    const mode = document.getElementById('mode-select').value;

    let reasoningEffort;
    let model;
    switch (mode) {
        case 'instant':
            model = 'gpt-5-nano';
            reasoningEffort = 'low';
            break;
        case 'normal':
            model = 'gpt-5-mini';
            reasoningEffort = 'low';
            break;
        case 'hard':
            model = 'gpt-5';
            reasoningEffort = 'high';
            break;
        case 'medium':
        default:
            model = 'gpt-5';
            reasoningEffort = 'medium';
            break;
    }

    // Clear input
    input.value = '';
    autoResizeTextarea(input);

    // Hide welcome message
    const welcomeMessage = document.getElementById('welcome-message');
    welcomeMessage.classList.add('hidden');

    // Add user message to UI
    const messagesContainer = document.getElementById('chat-messages');
    const userMsgEl = createMessageElement('user', escapeHtml(question), new Date());
    messagesContainer.appendChild(userMsgEl);

    // Add loading indicator
    const loadingEl = createLoadingMessage();
    messagesContainer.appendChild(loadingEl);

    // Scroll to bottom
    smoothScrollToBottom();

    // Disable send button
    isLoading = true;
    updateSendButton(true);

    try {
        const response = await fetch(`${API_BASE}/chat/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                conversation_id: currentConversation?._id,
                question: question,
                reasoning_effort: reasoningEffort,
                model,
                max_results: DEFAULT_MAX_RESULTS
            })
        });

        const data = await response.json();

        // Remove loading indicator
        loadingEl.remove();

        if (data.success) {
            // Update current conversation state if new one was created
            if (!currentConversation || currentConversation._id !== data.conversation_id) {
                // Just update the state, don't reload (to preserve UI messages)
                currentConversation = { _id: data.conversation_id };
                localStorage.setItem('currentConversation', JSON.stringify(currentConversation));
            }

            // Add assistant response
            const assistantMsg = createAssistantMessage(data.response);
            const assistantMsgEl = createMessageElement('assistant', assistantMsg, new Date());
            messagesContainer.appendChild(assistantMsgEl);

            // Initialize visualizations
            initializeVisualizations(assistantMsgEl);

            // Reload conversations to update title and highlight active conversation
            await loadConversations();
        } else {
            // Show error
            const errorMsg = `Error: ${data.error || 'Failed to process query'}`;
            const errorMsgEl = createMessageElement('assistant', errorMsg, new Date());
            messagesContainer.appendChild(errorMsgEl);
        }
    } catch (error) {
        console.error('Send message error:', error);
        loadingEl.remove();

        const errorMsg = 'Error: Failed to connect to server';
        const errorMsgEl = createMessageElement('assistant', errorMsg, new Date());
        messagesContainer.appendChild(errorMsgEl);
    } finally {
        isLoading = false;
        updateSendButton(false);
        smoothScrollToBottom();
    }

    return false;
}

// Create loading message
function createLoadingMessage() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.innerHTML = `
        <div class="message-avatar">AI</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-author">AI Assistant</span>
            </div>
            <div class="message-bubble">
                <div class="message-loading">
                    <span class="thinking-text">Thinking</span>
                    <div class="loading-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        </div>
    `;
    return loadingDiv;
}

// Update send button state
function updateSendButton(disabled) {
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = disabled;
}

// Update conversation title
function updateConversationTitle(title) {
    const titleEl = document.getElementById('conversation-title');
    if (titleEl) {
        titleEl.textContent = title || 'New Conversation';
    }
}

// Load user stats
async function loadUserStats() {
    try {
        const response = await fetch(`${API_BASE}/chat/stats`, {
            credentials: 'include'
        });

        const data = await response.json();
        if (data.success) {
            const stats = data.stats;
            const statsEl = document.getElementById('user-stats');
            if (statsEl) {
                statsEl.textContent = `${stats.total_conversations} conversation${stats.total_conversations !== 1 ? 's' : ''}`;
            }
        }
    } catch (error) {
        console.error('Load stats error:', error);
    }
}

// Set query from example
function setQuery(query) {
    const input = document.getElementById('message-input');
    input.value = query;
    autoResizeTextarea(input);
    input.focus();
}

// Handle textarea keydown
function handleInputKeydown(event) {
    const textarea = event.target;

    // Auto-resize
    autoResizeTextarea(textarea);

    // Submit on Enter (not Shift+Enter)
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        if (!isLoading && textarea.value.trim()) {
            handleSendMessage(event);
        }
    }
}

// Auto-resize textarea
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

// Scroll to bottom of messages
function scrollToBottom() {
    const messagesContainer = document.getElementById('chat-messages');
    setTimeout(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 100);
}

// Format timestamp
function formatTime(timestamp) {
    if (!timestamp) return '';

    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show toast notification
function showToast(message, type = 'error') {
    // Remove any existing toasts
    const existing = document.querySelector('.error-toast');
    if (existing) {
        existing.remove();
    }

    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.textContent = message;

    if (type === 'success') {
        toast.style.background = 'var(--success)';
    } else if (type === 'warning') {
        toast.style.background = 'var(--warning)';
    }

    document.body.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Show confirmation modal
function showConfirmModal(title, message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmation-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalMessage = document.getElementById('modal-message');
        const confirmBtn = document.getElementById('modal-confirm');
        const cancelBtn = document.getElementById('modal-cancel');

        // Set content
        modalTitle.textContent = title;
        modalMessage.textContent = message;

        // Show modal
        modal.classList.remove('hidden');

        // Handle confirm
        const handleConfirm = () => {
            cleanup();
            resolve(true);
        };

        // Handle cancel
        const handleCancel = () => {
            cleanup();
            resolve(false);
        };

        // Handle click outside modal
        const handleOverlayClick = (e) => {
            if (e.target === modal) {
                handleCancel();
            }
        };

        // Handle escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                handleCancel();
            }
        };

        // Cleanup function
        const cleanup = () => {
            modal.classList.add('hidden');
            confirmBtn.removeEventListener('click', handleConfirm);
            cancelBtn.removeEventListener('click', handleCancel);
            modal.removeEventListener('click', handleOverlayClick);
            document.removeEventListener('keydown', handleEscape);
        };

        // Add event listeners
        confirmBtn.addEventListener('click', handleConfirm);
        cancelBtn.addEventListener('click', handleCancel);
        modal.addEventListener('click', handleOverlayClick);
        document.addEventListener('keydown', handleEscape);
    });
}

// Improved scroll to bottom with smooth animation
function smoothScrollToBottom() {
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: 'smooth'
    });
}

// Initialize chat interface
async function initChat() {
    // Restore sidebar state
    restoreSidebarState();

    // Load conversations
    await loadConversations();

    // Try to restore last conversation
    const savedConversation = localStorage.getItem('currentConversation');
    if (savedConversation) {
        try {
            const conv = JSON.parse(savedConversation);
            await loadConversation(conv._id);
        } catch (error) {
            console.error('Error restoring conversation:', error);
            clearMessages();
        }
    } else {
        clearMessages();
    }

    // Set up event listeners
    setupEventListeners();

    // Focus input
    document.getElementById('message-input').focus();
}

// Set up all event listeners
function setupEventListeners() {
    console.log('[Chat] Setting up event listeners...');

    // Sidebar collapse button
    const sidebarCollapseBtn = document.getElementById('sidebar-collapse-btn');
    console.log('[Chat] Sidebar collapse button found:', !!sidebarCollapseBtn);
    if (sidebarCollapseBtn) {
        const newCollapseBtn = sidebarCollapseBtn.cloneNode(true);
        sidebarCollapseBtn.parentNode.replaceChild(newCollapseBtn, sidebarCollapseBtn);

        newCollapseBtn.addEventListener('click', (e) => {
            console.log('[Chat] Sidebar collapse button clicked!');
            e.preventDefault();
            e.stopPropagation();
            toggleSidebarCollapse();
        });

        console.log('[Chat] Sidebar collapse button listener attached');
    }

    // Edit history button (for collapsed state)
    const editHistoryBtn = document.querySelector('.edit-history-btn');
    console.log('[Chat] Edit history button found:', !!editHistoryBtn);
    if (editHistoryBtn) {
        editHistoryBtn.addEventListener('click', (e) => {
            console.log('[Chat] Edit history button clicked!');
            e.preventDefault();
            e.stopPropagation();
            toggleSidebarCollapse();
        });
    }

    // New chat button
    const newChatBtn = document.getElementById('new-chat-btn');
    console.log('[Chat] New chat button found:', !!newChatBtn);
    if (newChatBtn) {
        // Remove any existing listeners by cloning
        const newBtn = newChatBtn.cloneNode(true);
        newChatBtn.parentNode.replaceChild(newBtn, newChatBtn);

        newBtn.addEventListener('click', (e) => {
            console.log('[Chat] New chat button clicked!');
            e.preventDefault();
            e.stopPropagation();
            createNewConversation();
        });

        console.log('[Chat] New chat button listener attached');
    } else {
        console.error('[Chat] New chat button not found!');
    }

    // Clear chat button removed - now using delete buttons in sidebar

    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    console.log('[Chat] Logout button found:', !!logoutBtn);
    if (logoutBtn) {
        const newLogoutBtn = logoutBtn.cloneNode(true);
        logoutBtn.parentNode.replaceChild(newLogoutBtn, logoutBtn);

        newLogoutBtn.addEventListener('click', (e) => {
            console.log('[Chat] Logout button clicked!');
            e.preventDefault();
            e.stopPropagation();
            handleLogout();
        });
    }

    // Event delegation for conversation items
    const conversationsList = document.getElementById('conversations-list');
    console.log('[Chat] Conversations list found:', !!conversationsList);
    if (conversationsList) {
        conversationsList.addEventListener('click', (event) => {
            // Check if delete button was clicked
            const deleteBtn = event.target.closest('.conversation-delete-btn');
            if (deleteBtn) {
                event.stopPropagation();
                const conversationId = deleteBtn.dataset.conversationId;
                console.log('[Chat] Delete button clicked for conversation:', conversationId);
                if (conversationId) {
                    deleteConversation(conversationId);
                }
                return;
            }

            // Otherwise, load the conversation
            const conversationItem = event.target.closest('.conversation-item');
            if (conversationItem) {
                console.log('[Chat] Conversation item clicked:', conversationItem.dataset.conversationId);
                const conversationId = conversationItem.dataset.conversationId;
                if (conversationId) {
                    loadConversation(conversationId);
                }
            }
        });
    }

    console.log('[Chat] Event listeners setup complete');
}

export {
    initChat,
    setQuery,
    handleSendMessage,
    handleInputKeydown,
    toggleSidebar,
    toggleSidebarCollapse,
    autoResizeTextarea,
    restoreSidebarState,
    createNewConversation,
    loadConversation,
};
