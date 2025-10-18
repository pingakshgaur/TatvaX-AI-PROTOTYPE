// TatvaX Fixed JavaScript with Markdown Support

// Application State
let currentState = 'landing';
let selectedSubject = '';
let selectedLanguage = 'en';
let currentChatMode = 'subjects'; // 'subjects' or 'institutional'
let messages = [];
let isListening = false;
let chatHistory = [];
let availableSubjects = {};
let supportedLanguages = {};

// DOM Elements
const landingPage = document.getElementById('landing-page');
const subjectsPage = document.getElementById('subjects-page');
const chatPage = document.getElementById('chat-page');

// Mode cards
const subjectsModeCard = document.getElementById('subjects-mode-card');
const institutionalModeCard = document.getElementById('institutional-mode-card');

// Navigation
const backToLandingButton = document.getElementById('back-to-landing');
const backToSubjectsButton = document.getElementById('back-to-subjects');

// Subject selection
const subjectsGrid = document.getElementById('subjects-grid');
const languageSelect = document.getElementById('languageSelect');

// Chat interface
const chatTitle = document.getElementById('chat-title');
const chatSubtitle = document.getElementById('chat-subtitle');
const messagesContainer = document.getElementById('messages-container');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const voiceBtn = document.getElementById('voice-btn');
const clearChatBtn = document.getElementById('clear-chat');
const scrollToBottomBtn = document.getElementById('scroll-to-bottom');

// Controls
const translateModeBtn = document.getElementById('translate-mode');
const currentLanguageSpan = document.getElementById('current-language');
const voiceIndicator = document.getElementById('voice-indicator');

// Modals
const feedbackButton = document.getElementById('feedback-button');
const feedbackModal = document.getElementById('feedback-modal');
const closeFeedbackButton = document.getElementById('close-feedback');
const cancelFeedbackButton = document.getElementById('cancel-feedback');
const feedbackForm = document.getElementById('feedback-form');

const translationModal = document.getElementById('translation-modal');
const closeTranslationButton = document.getElementById('close-translation');

// Loading and notifications
const loadingOverlay = document.getElementById('loading-overlay');
const notification = document.getElementById('notification');

// Language names mapping
const languageNames = {
    'en': 'English',
    'hi': 'हिंदी (Hindi)',
    'bn': 'বাংলা (Bengali)',
    'mr': 'मराठी (Marathi)',
    'te': 'తెలుగు (Telugu)',
    'ta': 'தமிழ் (Tamil)',
    'gu': 'ગુજરાતી (Gujarati)',
    'kn': 'ಕನ್ನಡ (Kannada)'
};


// Utility Functions
function showPage(pageId) {
    console.log(`📄 Switching to page: ${pageId}`);
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(pageId).classList.add('active');
    currentState = pageId.replace('-page', '');
}

function showLoading(message = 'TatvaX is processing...') {
    if (loadingOverlay) {
        loadingOverlay.querySelector('p').textContent = message;
        loadingOverlay.classList.add('active');
    }
}

function hideLoading() {
    if (loadingOverlay) {
        loadingOverlay.classList.remove('active');
    }
}

function showNotification(message, type = 'success') {
    if (notification) {
        const icon = type === 'success' ? 'fas fa-check-circle' : 'fas fa-exclamation-circle';
        notification.innerHTML = `
            <div class="notification-content">
                <i class="${icon}"></i>
                <span>${message}</span>
            </div>
        `;
        notification.classList.add('show');

        setTimeout(() => {
            notification.classList.remove('show');
        }, 3000);
    }
}

// Initialize Application
async function initializeApp() {
    console.log('🚀 Initializing TatvaX...');

    try {
        // Test backend connection
        const statusResponse = await fetch('/api/status');
        const statusData = await statusResponse.json();
        console.log('✅ Backend connected:', statusData);

        // Load supported languages
        await loadSupportedLanguages();

        // Load available subjects
        await loadAvailableSubjects();

        // Setup event listeners
        setupEventListeners();

        // Update language display
        updateLanguageDisplay();

        console.log('✅ TatvaX initialized successfully');

    } catch (error) {
        console.error('❌ Failed to initialize TatvaX:', error);
        showNotification('Failed to connect to TatvaX services', 'error');
    }
}

async function loadSupportedLanguages() {
    try {
        const response = await fetch('/api/languages');
        const data = await response.json();

        if (data.status === 'success') {
            supportedLanguages = data.languages;
            console.log('📚 Loaded supported languages:', Object.keys(supportedLanguages).length);
        }
    } catch (error) {
        console.error('❌ Failed to load languages:', error);
    }
}

async function loadAvailableSubjects() {
    try {
        const response = await fetch('/api/subjects');
        const data = await response.json();

        if (data.status === 'success') {
            availableSubjects = data.subjects;
            renderSubjects();
            console.log('📚 Loaded subjects:', Object.keys(availableSubjects).length);
        }
    } catch (error) {
        console.error('❌ Failed to load subjects:', error);
    }
}

function renderSubjects() {
    if (!subjectsGrid || !availableSubjects) return;

    subjectsGrid.innerHTML = '';

    Object.entries(availableSubjects).forEach(([key, subject]) => {
        const subjectCard = document.createElement('div');
        subjectCard.className = 'subject-card';
        subjectCard.setAttribute('data-subject', key);

        subjectCard.innerHTML = `
            <div class="subject-icon" style="background: ${subject.color}">
                <i class="${subject.icon}"></i>
            </div>
            <h3>${subject.name}</h3>
            <p>${subject.description}</p>
        `;

        subjectCard.addEventListener('click', () => startSubjectChat(key, subject));
        subjectsGrid.appendChild(subjectCard);
    });
}

// Event Listeners Setup
function setupEventListeners() {
    // Mode selection
    if (subjectsModeCard) {
        subjectsModeCard.addEventListener('click', () => {
            currentChatMode = 'subjects';
            showPage('subjects-page');
        });
    }

    if (institutionalModeCard) {
        institutionalModeCard.addEventListener('click', () => {
            currentChatMode = 'institutional';
            startInstitutionalChat();
        });
    }

    // Navigation
    if (backToLandingButton) {
        backToLandingButton.addEventListener('click', () => {
            showPage('landing-page');
            resetChat();
        });
    }

    if (backToSubjectsButton) {
        backToSubjectsButton.addEventListener('click', () => {
            if (currentChatMode === 'subjects') {
                showPage('subjects-page');
            } else {
                showPage('landing-page');
            }
            resetChat();
        });
    }

    // Language selection
    if (languageSelect) {
        languageSelect.addEventListener('change', (e) => {
            selectedLanguage = e.target.value;
            updateLanguageDisplay();
            console.log('🌐 Language changed to:', selectedLanguage);
        });
    }

    // Chat interface
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }

    if (messageInput) {
        messageInput.addEventListener('input', updateSendButton);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    if (voiceBtn) {
        voiceBtn.addEventListener('click', toggleVoiceInput);
    }

    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', clearChat);
    }

    if (scrollToBottomBtn) {
        scrollToBottomBtn.addEventListener('click', () => scrollToBottom(true));
    }

    if (translateModeBtn) {
        translateModeBtn.addEventListener('click', showTranslationModal);
    }

    // Scroll detection for messages
    if (messagesContainer) {
        messagesContainer.addEventListener('scroll', checkScrollPosition);
    }

    // Feedback system
    setupFeedbackSystem();

    // Translation modal
    setupTranslationModal();

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

function updateLanguageDisplay() {
    if (currentLanguageSpan && languageNames[selectedLanguage]) {
        currentLanguageSpan.textContent = languageNames[selectedLanguage];
    }

    // Update placeholder text
    if (messageInput) {
        const placeholders = {
            'en': 'Ask me anything...',
            'hi': 'मुझसे कुछ भी पूछें...',
            'bn': 'আমাকে কিছু জিজ্ঞাসা করুন...',
            'mr': 'मला काही विचारा...',
            'te': 'నన్ను ఏదైనా అడగండి...',
            'ta': 'என்னிடம் எதையும் கேளுங்கள்...',
            'gu': 'મને કંઈપણ પૂછો...',
            'kn': 'ನನ್ನನ್ನು ಏನಾದರೂ ಕೇಳಿ...'
        };

        messageInput.placeholder = placeholders[selectedLanguage] || placeholders['en'];
    }
}

function handleKeyboardShortcuts(e) {
    // Ctrl/Cmd + K for quick translate
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        showTranslationModal();
    }

    // Escape to close modals
    if (e.key === 'Escape') {
        closeFeedbackModal();
        closeTranslationModal();
    }
}

// Chat Functions
function startSubjectChat(subjectKey, subject) {
    selectedSubject = subjectKey;
    currentChatMode = 'subjects';

    if (chatTitle) chatTitle.textContent = subject.name;
    if (chatSubtitle) chatSubtitle.textContent = 'Subject Learning Mode';

    showPage('chat-page');
    resetChat();

    // Add welcome message
    const welcomeMessage = getWelcomeMessage(subject.name, selectedLanguage);
    addMessage(welcomeMessage, 'bot');

    console.log('📚 Started subject chat:', subject.name);
}

function startInstitutionalChat() {
    selectedSubject = '';
    currentChatMode = 'institutional';

    if (chatTitle) chatTitle.textContent = 'Institutional Assistant';
    if (chatSubtitle) chatSubtitle.textContent = 'FAQ & Information';

    showPage('chat-page');
    resetChat();

    // Add welcome message
    const welcomeMessage = getInstitutionalWelcomeMessage(selectedLanguage);
    addMessage(welcomeMessage, 'bot');

    console.log('🏫 Started institutional chat');
}

function getWelcomeMessage(subjectName, language) {
    const messages = {
        'en': `Hello! 👋\n\nI'm your ${subjectName} learning assistant. I can help you understand concepts, solve problems, and answer questions about ${subjectName}.\n\nWhat would you like to learn today?`,
        'hi': `नमस्ते! 👋\n\nमैं आपका ${subjectName} शिक्षण सहायक हूं। मैं आपको अवधारणाओं को समझने, समस्याओं को हल करने और ${subjectName} के बारे में प्रश्नों के उत्तर देने में मदद कर सकता हूं।\n\nआज आप क्या सीखना चाहते हैं?`
    };

    return messages[language] || messages['en'];
}

function getInstitutionalWelcomeMessage(language) {
    const messages = {
        'en': `Welcome to Institutional Support! 🏫\n\nI can help you with:\n• Admission procedures\n• Fee information\n• Exam schedules\n• Academic calendar\n• School policies\n• And much more!\n\nWhat would you like to know?`,

        'hi': `संस्थागत सहायता में आपका स्वागत है! 🏫\n\nमैं आपकी इनमें मदद कर सकता हूं:\n• प्रवेश प्रक्रिया\n• शुल्क जानकारी\n• परीक्षा कार्यक्रम\n• शैक्षणिक कैलेंडर\n• स्कूल नीतियां\n• और भी बहुत कुछ!\n\nआप क्या जानना चाहते हैं?`
    };

    return messages[language] || messages['en'];
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    console.log(`💬 Sending ${currentChatMode} message:`, message);

    // Add user message
    addMessage(message, 'user');
    messageInput.value = '';
    updateSendButton();

    // Show typing indicator
    showTypingIndicator();

    try {
        const requestData = {
            message: message,
            mode: currentChatMode,
            language: selectedLanguage,
            subject: selectedSubject
        };

        const response = await fetch('/api/chat/text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();
        hideTypingIndicator();

        if (data.status === 'success') {
            addMessage(data.response, 'bot', data.audio_file);

            // Store in chat history
            chatHistory.push({
                query: message,
                response: data.response,
                mode: currentChatMode,
                subject: selectedSubject,
                language: selectedLanguage,
                timestamp: new Date()
            });

        } else {
            addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }

    } catch (error) {
        hideTypingIndicator();
        console.error('❌ Chat error:', error);
        addMessage('Sorry, I could not process your request. Please check your connection.', 'bot');
    }
}

async function toggleVoiceInput() {
    if (isListening) {
        // Stop listening
        isListening = false;
        voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        voiceBtn.style.background = '';
        voiceIndicator.classList.remove('active');
        return;
    }

    // Start listening
    isListening = true;
    voiceBtn.innerHTML = '<i class="fas fa-stop"></i>';
    voiceBtn.style.background = 'var(--color-2)';
    voiceIndicator.classList.add('active');

    showTypingIndicator('Listening...');

    try {
        const requestData = {
            mode: currentChatMode,
            language: selectedLanguage,
            subject: selectedSubject
        };

        const response = await fetch('/api/chat/voice', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();
        hideTypingIndicator();

        if (data.status === 'success') {
            // Add the recognized text as user message
            if (data.original_query) {
                addMessage(data.original_query, 'user');
            }

            // Add bot response
            addMessage(data.response, 'bot', data.audio_file);

        } else {
            addMessage('Sorry, I could not understand your voice. Please try again.', 'bot');
        }

    } catch (error) {
        hideTypingIndicator();
        console.error('âŒ Voice input error:', error);
        addMessage('Voice recognition failed. Please try typing your message.', 'bot');

    } finally {
        // Reset voice button state
        isListening = false;
        voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        voiceBtn.style.background = '';
        voiceIndicator.classList.remove('active');
    }
}

function addMessage(content, sender, audioFile = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';

    // FIXED: Use Markdown rendering for bot messages
    if (sender === 'bot') {
        messageContent.innerHTML = formatMarkdownMessage(content);
    } else {
        messageContent.innerHTML = formatMessage(content);
    }

    // Add audio controls for bot messages
    if (audioFile && sender === 'bot') {
        const audioControls = document.createElement('div');
        audioControls.className = 'audio-controls';

        const playBtn = document.createElement('button');
        playBtn.className = 'audio-btn';
        playBtn.innerHTML = '<i class="fas fa-play"></i> Play Audio';
        playBtn.onclick = () => playAudioFile(audioFile, playBtn);
        audioControls.appendChild(playBtn);

        const stopBtn = document.createElement('button');
        stopBtn.className = 'audio-btn stop-btn';
        stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop';
        stopBtn.onclick = () => stopAudio();
        audioControls.appendChild(stopBtn);

        messageContent.appendChild(audioControls);
    }

    messageDiv.appendChild(messageContent);
    messagesContainer.appendChild(messageDiv);

    // Auto-scroll to bottom
    setTimeout(() => scrollToBottom(true), 100);

    // Update scroll button visibility
    setTimeout(() => checkScrollPosition(), 200);
}

// FIXED: Markdown message formatting like ChatGPT
function formatMarkdownMessage(text) {
    if (!text) return '';

    try {
        // Use marked.js to parse markdown
        if (typeof marked !== 'undefined') {
            const renderer = new marked.Renderer();

            // Custom rendering for better styling
            renderer.paragraph = function (text) {
                return `<p style="margin-bottom: 1rem; line-height: 1.6;">${text}</p>`;
            };

            renderer.list = function (body, ordered) {
                const type = ordered ? 'ol' : 'ul';
                return `<${type} style="margin: 1rem 0; padding-left: 1.5rem; line-height: 1.8;">${body}</${type}>`;
            };

            renderer.listitem = function (text) {
                return `<li style="margin-bottom: 0.5rem;">${text}</li>`;
            };

            renderer.strong = function (text) {
                return `<strong style="color: var(--text-primary); font-weight: 600;">${text}</strong>`;
            };

            renderer.em = function (text) {
                return `<em style="color: var(--text-secondary); font-style: italic;">${text}</em>`;
            };

            renderer.code = function (code) {
                return `<code style="background: var(--bg-primary); padding: 0.2rem 0.4rem; border-radius: 4px; font-family: monospace; font-size: 0.9em;">${code}</code>`;
            };

            renderer.codespan = function (code) {
                return `<code style="background: var(--bg-primary); padding: 0.2rem 0.4rem; border-radius: 4px; font-family: monospace; font-size: 0.9em;">${code}</code>`;
            };

            renderer.blockquote = function (quote) {
                return `<blockquote style="border-left: 4px solid var(--accent-color); padding-left: 1rem; margin: 1rem 0; font-style: italic; color: var(--text-secondary);">${quote}</blockquote>`;
            };

            // Set options
            marked.setOptions({
                renderer: renderer,
                breaks: true,
                gfm: true
            });

            return marked(text);
        }
    } catch (error) {
        console.error('Markdown parsing error:', error);
    }

    // Fallback to basic formatting
    return formatMessage(text);
}

function formatMessage(text) {
    if (!text) return '';

    let formatted = text.replace(/\n/g, '<br>');

    // Format bullet points
    formatted = formatted.replace(/â€¢ (.+)/g, '<span style="color: var(--accent-color);">â€¢</span> <em>$1</em>');

    // Format numbered lists
    formatted = formatted.replace(/(\d+)\. (.+)/g, '<strong style="color: var(--text-primary);">$1.</strong> $2');

    // Format important sections
    formatted = formatted.replace(/Important:/g, '<strong style="color: var(--accent-color);">Important:</strong>');
    formatted = formatted.replace(/Note:/g, '<strong style="color: var(--text-secondary);">Note:</strong>');

    return formatted;
}

function showTypingIndicator(customText = 'TatvaX is thinking...') {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = 'typing-indicator';

    const typingContent = document.createElement('div');
    typingContent.className = 'typing-indicator';
    typingContent.innerHTML = `
        <span>${customText}</span>
        <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;

    typingDiv.appendChild(typingContent);
    messagesContainer.appendChild(typingDiv);
    scrollToBottom(true);
}

function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Audio Functions
async function playAudioFile(filename, buttonElement) {
    if (!filename) {
        console.log('No audio file available');
        return;
    }

    try {
        resetAudioButtons();
        buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        buttonElement.disabled = true;

        const response = await fetch(`/api/audio/play/${filename}`);
        const data = await response.json();

        if (data.status === 'success') {
            buttonElement.innerHTML = '<i class="fas fa-pause"></i> Playing...';

            // Monitor audio status
            const checkStatus = setInterval(async () => {
                try {
                    const statusResponse = await fetch('/api/status');
                    const statusData = await statusResponse.json();

                    if (!statusData.audio_playing) {
                        clearInterval(checkStatus);
                        resetAudioButtons();
                    }
                } catch (error) {
                    clearInterval(checkStatus);
                    resetAudioButtons();
                }
            }, 1000);

            // Timeout after 30 seconds
            setTimeout(() => {
                clearInterval(checkStatus);
                resetAudioButtons();
            }, 30000);

        } else {
            throw new Error(data.error || 'Failed to play audio');
        }
    } catch (error) {
        console.error('âŒ Audio playback error:', error);
        buttonElement.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
        setTimeout(() => resetAudioButtons(), 2000);
    }
}

async function stopAudio() {
    try {
        const response = await fetch('/api/audio/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();
        if (data.status === 'success') {
            resetAudioButtons();
        }
    } catch (error) {
        console.error('❌ Stop audio error:', error);
    }
}

function resetAudioButtons() {
    const audioButtons = document.querySelectorAll('.audio-btn:not(.stop-btn)');
    audioButtons.forEach(btn => {
        btn.innerHTML = '<i class="fas fa-play"></i> Play Audio';
        btn.disabled = false;
    });
}

// Utility Functions
function updateSendButton() {
    const hasContent = messageInput.value.trim().length > 0;
    sendButton.disabled = !hasContent;
}

function checkScrollPosition() {
    const container = messagesContainer;
    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;

    const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;

    if (isAtBottom) {
        scrollToBottomBtn.classList.remove('visible');
    } else {
        scrollToBottomBtn.classList.add('visible');
    }
}

function scrollToBottom(smooth = true) {
    messagesContainer.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
    });
}

async function clearChat() {
    try {
        const response = await fetch('/api/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (response.ok) {
            resetChat();
            showNotification('Chat cleared successfully');

            // Add welcome message again
            if (currentChatMode === 'subjects' && selectedSubject && availableSubjects[selectedSubject]) {
                const welcomeMessage = getWelcomeMessage(availableSubjects[selectedSubject].name, selectedLanguage);
                addMessage(welcomeMessage, 'bot');
            } else if (currentChatMode === 'institutional') {
                const welcomeMessage = getInstitutionalWelcomeMessage(selectedLanguage);
                addMessage(welcomeMessage, 'bot');
            }
        }
    } catch (error) {
        console.error('❌ Clear chat error:', error);
        showNotification('Failed to clear chat', 'error');
    }
}

function resetChat() {
    messagesContainer.innerHTML = '';
    chatHistory = [];
    scrollToBottomBtn.classList.remove('visible');
}

// Feedback System
function setupFeedbackSystem() {
    if (feedbackButton) {
        feedbackButton.addEventListener('click', showFeedbackModal);
    }

    if (closeFeedbackButton) {
        closeFeedbackButton.addEventListener('click', closeFeedbackModal);
    }

    if (cancelFeedbackButton) {
        cancelFeedbackButton.addEventListener('click', closeFeedbackModal);
    }

    if (feedbackForm) {
        feedbackForm.addEventListener('submit', submitFeedback);
    }

    // Close modal when clicking outside
    if (feedbackModal) {
        feedbackModal.addEventListener('click', (e) => {
            if (e.target === feedbackModal) {
                closeFeedbackModal();
            }
        });
    }
}

function showFeedbackModal() {
    if (feedbackModal) {
        feedbackModal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeFeedbackModal() {
    if (feedbackModal) {
        feedbackModal.classList.remove('active');
        document.body.style.overflow = '';
        resetFeedbackForm();
    }
}

function resetFeedbackForm() {
    if (feedbackForm) {
        feedbackForm.reset();
        document.querySelectorAll('.star-rating input').forEach(input => {
            input.checked = false;
        });
    }
}

async function submitFeedback(event) {
    event.preventDefault();

    const submitBtn = document.querySelector('.submit-btn');
    const originalText = submitBtn.innerHTML;

    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';

        const formData = {
            rating: document.querySelector('input[name="rating"]:checked')?.value || 'Not rated',
            name: document.getElementById('feedback-name').value.trim() || 'Anonymous',
            email: document.getElementById('feedback-email').value.trim() || 'Not provided',
            message: document.getElementById('feedback-message').value.trim(),
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            currentPage: currentState,
            chatMode: currentChatMode,
            selectedLanguage: selectedLanguage
        };

        if (!formData.message) {
            throw new Error('Please enter your feedback message');
        }

        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (result.status === 'success') {
            showFeedbackSuccess();
            setTimeout(() => {
                closeFeedbackModal();
                showNotification('Thank you for your feedback!');
            }, 2000);
        } else {
            throw new Error(result.message || 'Failed to submit feedback');
        }

    } catch (error) {
        console.error('âŒ Feedback submission error:', error);
        showNotification('Failed to submit feedback: ' + error.message, 'error');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

function showFeedbackSuccess() {
    const modalContent = document.querySelector('.feedback-modal-content');
    modalContent.innerHTML = `
        <div class="feedback-success" style="text-align: center; padding: 2rem; color: var(--text-primary);">
            <i class="fas fa-check-circle" style="font-size: 3rem; color: var(--accent-color); margin-bottom: 1rem;"></i>
            <h3 style="color: var(--text-primary); margin-bottom: 0.5rem;">Thank You!</h3>
            <p>Your feedback has been submitted successfully.</p>
            <p>We appreciate your input for improving TatvaX!</p>
        </div>
    `;
}

// Translation Modal
function setupTranslationModal() {
    if (closeTranslationButton) {
        closeTranslationButton.addEventListener('click', closeTranslationModal);
    }

    if (translationModal) {
        translationModal.addEventListener('click', (e) => {
            if (e.target === translationModal) {
                closeTranslationModal();
            }
        });
    }

    const translateBtn = document.getElementById('translate-btn');
    if (translateBtn) {
        translateBtn.addEventListener('click', performTranslation);
    }

    const swapBtn = document.getElementById('swap-languages');
    if (swapBtn) {
        swapBtn.addEventListener('click', swapTranslationLanguages);
    }
}

function showTranslationModal() {
    if (translationModal) {
        translationModal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeTranslationModal() {
    if (translationModal) {
        translationModal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function swapTranslationLanguages() {
    const sourceSelect = document.getElementById('source-language');
    const targetSelect = document.getElementById('target-language');

    if (sourceSelect && targetSelect) {
        const temp = sourceSelect.value;
        sourceSelect.value = targetSelect.value;
        targetSelect.value = temp;
    }
}

async function performTranslation() {
    const translateInput = document.getElementById('translate-input');
    const sourceLanguage = document.getElementById('source-language');
    const targetLanguage = document.getElementById('target-language');
    const resultDiv = document.getElementById('translation-result');
    const translateBtn = document.getElementById('translate-btn');

    if (!translateInput || !sourceLanguage || !targetLanguage || !resultDiv) return;

    const text = translateInput.value.trim();
    if (!text) {
        showNotification('Please enter text to translate', 'error');
        return;
    }

    const originalText = translateBtn.innerHTML;

    try {
        translateBtn.disabled = true;
        translateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Translating...';

        const response = await fetch('/api/translate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                source_language: sourceLanguage.value,
                target_language: targetLanguage.value
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            resultDiv.innerHTML = `
                <div class="translation-output" style="margin-top: 1rem; padding: 1rem; background: var(--bg-primary); border-radius: var(--radius-md); border: 1px solid var(--border-color);">
                    <div class="translation-text" style="font-size: 1rem; line-height: 1.6; color: var(--text-primary); margin-bottom: 0.5rem;">${data.translated_text}</div>
                    <div class="translation-meta" style="font-size: 0.8rem; color: var(--text-muted);">
                        Translated to ${languageNames[data.target_language] || data.target_language}
                    </div>
                </div>
            `;
        } else {
            throw new Error(data.error || 'Translation failed');
        }

    } catch (error) {
        console.error('âŒ Translation error:', error);
        resultDiv.innerHTML = `
            <div class="translation-error" style="margin-top: 1rem; padding: 1rem; background: var(--color-2); border-radius: var(--radius-md); text-align: center; color: var(--text-primary);">
                <i class="fas fa-exclamation-triangle"></i>
                Translation failed. Please try again.
            </div>
        `;
    } finally {
        translateBtn.disabled = false;
        translateBtn.innerHTML = originalText;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌟 TatvaX Loading...');
    initializeApp();
});