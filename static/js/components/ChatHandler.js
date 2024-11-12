export class ChatHandler {
    constructor(landingContainer, chatView, landingInput, landingSearchBtn, featureCards) {
        this.landingContainer = landingContainer;
        this.chatView = chatView;
        this.landingInput = landingInput;
        this.landingSearchBtn = landingSearchBtn;
        this.featureCards = featureCards;
    }

    initialize() {
        this.setupEventListeners();
    }

    showChat(query = '') {
        this.landingContainer.classList.add('fade-out');
        setTimeout(() => {
            this.landingContainer.classList.add('hidden');
            this.chatView.classList.remove('hidden');
            this.chatView.classList.add('slide-up-enter');
            
            if (query) {
                const chatInput = document.querySelector('#userinputform textarea');
                if (chatInput) {
                    chatInput.value = query;
                    chatInput.form.dispatchEvent(new Event('submit'));
                }
            }
        }, 300);
    }

    setupEventListeners() {
        // Handle search button click
        this.landingSearchBtn.addEventListener('click', () => {
            const query = this.landingInput.value.trim();
            this.showChat(query);
        });

        // Handle enter key in search input
        this.landingInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = this.landingInput.value.trim();
                this.showChat(query);
            }
        });

        // Handle feature card clicks
        this.featureCards.forEach(card => {
            card.addEventListener('click', () => {
                const query = card.dataset.query;
                this.showChat(query);
            });
        });
    }

    static clearChat() {
        const upperdiv = document.getElementById('upperid');
        upperdiv.innerHTML = '';
        localStorage.removeItem('chatHistory');
        
        // Make a request to the backend to reset the session
        fetch('/reset-session', {
            method: 'POST'
        }).then(response => response.json())
        .then(data => console.log('Session reset:', data))
        .catch(error => console.error('Error resetting session:', error));
    }
}

// Make clearChat available globally
window.clearChat = ChatHandler.clearChat;