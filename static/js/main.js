document.addEventListener('DOMContentLoaded', function() {
    // Initialize carousel
    const carousel = new LanguageCarousel();
    carousel.start();

    const landingContainer = document.getElementById('landing-container');
    const chatView = document.getElementById('chat-view');
    const landingInput = document.getElementById('landing-input');
    const landingSearchBtn = document.getElementById('landing-search-btn');
    const featureCards = document.querySelectorAll('.feature-card');
    const chatContainer = document.querySelector('#upperid');
    window.audioPlayer = null;

    // Initialize handlers
    const chatHandler = new ChatHandler(landingContainer, chatView, landingInput, landingSearchBtn, featureCards);
    chatHandler.initialize();

    const audioHandler = new AudioHandler();
    audioHandler.initialize();

    const formHandler = new FormHandler();
    formHandler.initialize();

    // Load chat history
    loadChatHistory();

    // Add event delegation for audio buttons
    chatContainer.addEventListener('click', function(e) {
        if (e.target.closest('.audio-btn')) {
            const messageDiv = e.target.closest('.appmessagediv');
            if (messageDiv) {
                const messageText = messageDiv.querySelector('.appmessage').textContent;
                audioHandler.playAudio(messageText);
            }
        }
    });

    function loadChatHistory() {
        const chatHistory = localStorage.getItem('chatHistory');
        if (chatHistory) {
            chatContainer.innerHTML = chatHistory;
            scrollToBottom();
        }
    }

    function scrollToBottom() {
        var div = document.getElementById("upperid");
        div.scrollTop = div.scrollHeight;
    }
});

import { LanguageCarousel } from './components/LanguageCarousel.js';
import { ChatHandler } from './components/ChatHandler.js';
import { AudioHandler } from './components/AudioHandler.js';
import { FormHandler } from './components/FormHandler.js';