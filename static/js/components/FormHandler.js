export class FormHandler {
    constructor() {
        this.imageUpload = document.getElementById('imageUpload');
        this.imagePreview = document.getElementById('imagePreview');
        this.previewImage = document.getElementById('previewImage');
        this.removeImage = document.getElementById('removeImage');
        this.userinputform = document.getElementById('userinputform');
        this.textarea = document.getElementById('userinput');
    }

    initialize() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.userinputform.addEventListener('submit', (event) => {
            event.preventDefault();
            this.formsubmitted();
        });

        this.imageUpload.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.previewImage.src = e.target.result;
                    this.imagePreview.style.display = 'flex';
                }
                reader.readAsDataURL(file);
            }
        });

        this.removeImage.addEventListener('click', () => {
            this.imageUpload.value = '';
            this.imagePreview.style.display = 'none';
            this.previewImage.src = '';
        });

        this.textarea.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.userinputform.requestSubmit();
            }
        });
    }

    async formsubmitted() {
        let userinput = this.textarea.value.trim();
        let sendbtn = document.getElementById('sendbtn');
        let userinputarea = this.textarea;
        let upperdiv = document.getElementById('upperid');
        let file = this.imageUpload.files[0];
    
        if (!userinput && !file) {
            alert('Please enter a message or select an image.');
            return;
        }
    
        sendbtn.disabled = true;
        userinputarea.disabled = true;
    
        // Add user message to chat
        if (userinput) {
            upperdiv.innerHTML += `
                <div class="message">
                    <div class="usermessagediv">
                        <div class="usermessage">${userinput}</div>
                    </div>
                </div>`;
        }
    
        // If there's an image, add it to the chat
        if (file) {
            upperdiv.innerHTML += `
                <div class="message">
                    <div class="usermessagediv">
                        <div class="message-image-container rounded-lg">
                            <img src="${URL.createObjectURL(file)}" alt="Uploaded Image">
                        </div>
                    </div>
                </div>`;
        }
    
        // Add simple loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message';
        loadingDiv.innerHTML = '<div class="simple-loader"></div>';
        upperdiv.appendChild(loadingDiv);
    
        this.scrollToBottom();
    
        userinputarea.value = "";
        userinputarea.placeholder = "Wait . . .";
    
        // Clear image preview above chat input
        this.imageUpload.value = '';
        this.imagePreview.style.display = 'none';
        this.previewImage.src = '';
    
        const formData = new FormData();
        if (userinput) formData.append('data', userinput);
        if (file) formData.append('file', file);
    
        try {
            const response = await fetch("/chatbot", {
                method: 'POST',
                body: formData
            });
            const json = await response.json();
    
            // Remove loading indicator
            loadingDiv.remove();
    
            userinputarea.placeholder = "Your message...";
    
            if (json.response) {
                let message = json.message.trim();
                message = message.toString();
    
                upperdiv.innerHTML += `
                <div class="message">
                    <div class="appmessagediv">
                        <div class="appmessage" id="temp"></div>
                    </div>
                </div>`;
    
                let temp = document.getElementById('temp');
                let index = 0;
                const displayNextLetter = () => {
                    this.scrollToBottom();
                    if (index < message.length) {
                        let currentChar = message[index];
                        
                        if (currentChar === '*' && message[index + 1] === '*') {
                            let boldEnd = message.indexOf('**', index + 2);
                            if (boldEnd !== -1) {
                                let boldText = message.substring(index + 2, boldEnd);
                                temp.innerHTML += `<strong>${boldText}</strong>`;
                                index = boldEnd + 2;
                            } else {
                                temp.innerHTML += currentChar;
                                index++;
                            }
                        } else if (message[index] === '\n') {
                            temp.innerHTML += '<br>';
                            index++;
                        } else if (currentChar === '<') {
                            let tagEnd = message.indexOf('>', index);
                            if (tagEnd !== -1) {
                                index = tagEnd + 1;
                            } else {
                                index++;
                            }
                        } else {
                            temp.innerHTML += currentChar;
                            index++;
                        }
                        setTimeout(displayNextLetter, 5);
                    } else {
                        temp.removeAttribute('id');
                        sendbtn.disabled = false;
                        userinputarea.disabled = false;
                        
                        // Add audio button after the message is fully displayed
                        const audioButton = document.createElement('button');
                        audioButton.className = 'audio-btn';
                        audioButton.innerHTML = `
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                            </svg>
                        `;
                        audioButton.onclick = () => playAudio(message);
                        temp.parentElement.appendChild(audioButton);
                        localStorage.setItem('chatHistory', upperdiv.innerHTML);
                    }
                };
                displayNextLetter();
            } else {
                let message = json.message;
                upperdiv.innerHTML += `
                <div class="message">
                    <div class="appmessagediv">
                        <div class="appmessage" style="border: 1px solid red;">
                            ${message}
                        </div>
                    </div>
                </div>`;
                sendbtn.disabled = false;
                userinputarea.disabled = false;
                localStorage.setItem('chatHistory', upperdiv.innerHTML);
            }
        } catch (error) {
            console.error('Error:', error);
            loadingDiv.remove();
            upperdiv.innerHTML += `
            <div class="message">
                <div class="appmessagediv">
                    <div class="appmessage" style="border: 1px solid red;">
                        Error: Unable to get response
                    </div>
                </div>
            </div>`;
            sendbtn.disabled = false;
            userinputarea.disabled = false;
            localStorage.setItem('chatHistory', upperdiv.innerHTML);
        }
    
        this.scrollToBottom();
    }

    scrollToBottom() {
        const div = document.getElementById("upperid");
        div.scrollTop = div.scrollHeight;
    }
}