// Arrays to keep track of conversation components for navigation and updates
let responseBlocks = [];
let historyItems = [];
let messageMap = [];

// Configure Markdown rendering options
marked.setOptions({
  gfm: true,
  breaks: false
});

/* Get references to key UI elements: toggles, indicators, and document input/drop zone */
const googleToggle = document.getElementById('google-toggle');
const googleIndicator = document.getElementById('google-indicator');
const documentInput = document.getElementById('document');
const documentDropZone = document.getElementById('document-drop-zone');
const documentToggle = document.getElementById('document-toggle');
const documentIndicator = document.getElementById('document-indicator');


/* Event listener to update Google search indicator when toggle state changes */
googleToggle.addEventListener('change', () => {
    if (googleToggle.checked) {
        googleIndicator.textContent = "Search: ON";
        googleIndicator.classList.add('active');
    } else {
        googleIndicator.textContent = "Search: OFF";
        googleIndicator.classList.remove('active');
    }
});


/* Updates the conversation history UI by adding a new user message entry */
function updateHistory(userText, responseIndex) {
    // Get the conversation history container
    const historyDiv = document.getElementById('conversation-history');
    // Clear placeholder text if present
    if (historyDiv.querySelector('.text-muted')) {
        historyDiv.innerHTML = "";
    }

    // Create a new message element for the user's input
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('mb-2', 'p-2', 'rounded', 'conversation-item', 'bg-primary', 'text-white');
    messageDiv.textContent = `User: ${userText}`;
    messageDiv.dataset.index = historyItems.length;

    // Add click event to scroll to corresponding response and highlight the history item
    messageDiv.addEventListener('click', () => {
        if (responseBlocks[responseIndex]) {
            responseBlocks[responseIndex].scrollIntoView({ behavior: 'smooth', block: 'start' });
            highlightHistoryItem(messageDiv);
        }
    });

    // Append new message to history and update tracking arrays
    historyDiv.appendChild(messageDiv);
    historyDiv.scrollTop = historyDiv.scrollHeight;
    historyItems.push(messageDiv);
    messageMap.push(responseIndex);
}

/* Highlights the selected conversation item by applying an active style and removing it from others */
function highlightHistoryItem(activeItem) {
    // Remove active highlight from all conversation items
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.remove('active-history');
    });
    // Apply active highlight to the clicked conversation item
    activeItem.classList.add('active-history');
}

/* Creates a new response block for the assistant's reply and adds it to the response container */
function addResponseBlock() {
    // Get the main response container element
    const responseContainer = document.getElementById('response');

    // Create a new block element for the assistant's response
    const block = document.createElement('div');
    block.classList.add('assistant-response', 'p-2', 'mb-2', 'bg-dark', 'text-light', 'rounded');

     // Append the new block to the container and track it in the responseBlocks array
    responseContainer.appendChild(block);
    responseBlocks.push(block);

    // Return the newly created response block
    return block;
}

/* Sends user input (text, audio, image, and optional document context) to the server and updates the UI with the response */
async function sendMessage() {
    // Prepare form data and gather user input
    const formData = new FormData();
    const userText = document.getElementById('text').value.trim();
    const audioFile = document.getElementById('audio').files[0];
    const imageFile = document.getElementById('image').files[0];

    if (userText) formData.append('text', userText);
    if (audioFile) formData.append('audio', audioFile);
    if (imageFile) formData.append('image', imageFile);

    /// Append toggle states for Google Search and Document Interaction
    formData.append('google_search', googleToggle.checked ? 'true' : 'false');
    // Append user preference for interacting with the uploaded document (true/false)
    formData.append('document_interaction', documentToggle.checked ? 'true' : 'false');

    // If Document Interaction is enabled, include the document summary (truncated if too long)
    if (documentToggle.checked) {
        const summaryElement = document.getElementById('document-summary');
        let summaryText = summaryElement ? summaryElement.innerText.trim() : "";
        if (summaryText.length > 1500) {
            summaryText = summaryText.substring(0, 1500) + "...[truncated]";
        }
        if (summaryText) {
            formData.append('document_context', summaryText);
        }
    }

    // Exit early if no input is provided
    if (!userText && !audioFile && !imageFile) return;

    // Show typing indicator while waiting for the response
    document.querySelector('.typing-indicator').style.display = 'block';

    try {
        // Add a new response block and update conversation history
        const responseBlock = addResponseBlock();
        updateHistory(userText || '[Media Uploaded]', responseBlocks.length - 1);

        // Send request to the server and handle response
        const response = await fetch('/stream', { method: 'POST', body: formData });
        if (!response.ok) throw new Error(`Server error: ${response.status}`);

        const result = await response.json();

        // Display error or render Markdown response
        if (result.error) {
            responseBlock.innerHTML = `<p class="text-danger">${result.error}</p>`;
        } else {
            const markdownHTML = marked.parse(result.response);
            responseBlock.innerHTML = DOMPurify.sanitize(markdownHTML);

            // Append Google search results if available
            if (result.search_results && result.search_results.length > 0) {
                const searchSection = document.createElement('div');
                searchSection.classList.add('search-results');
                searchSection.innerHTML = `<h5>Search Results:</h5><ul>` +
                    result.search_results.map(url => `<li><a href="${url}" target="_blank">${url}</a></li>`).join('') +
                    `</ul>`;
                responseBlock.appendChild(searchSection);
            }

            // Apply syntax highlighting to code blocks
            hljs.highlightAll();
        }

        // Add copy buttons to code blocks in the response
        responseBlock.querySelectorAll('pre code').forEach((codeBlock) => {
            const button = document.createElement('button');
            button.textContent = 'Copy';
            button.className = 'copy-btn';

            // Position the copy button inside the code block
            button.addEventListener('click', () => {
                navigator.clipboard.writeText(codeBlock.innerText).then(() => {
                    button.textContent = 'Copied!';
                    setTimeout(() => (button.textContent = 'Copy'), 2000);
                });
            });

            const pre = codeBlock.parentNode;
            pre.style.position = 'relative';
            pre.appendChild(button);
        });

    } catch (error) {
        // Log and show error notification
        console.error('Error:', error);
        showToast(`Error: ${error.message}`);
    } finally {
        // Hide typing indicator once processing is complete
        document.querySelector('.typing-indicator').style.display = 'none';
    }
}

/* Displays a temporary toast notification at the bottom center of the screen */
function showToast(message) {
    // Create the toast container with Bootstrap-compatible classes
    const toast = document.createElement('div');
    toast.className = "toast align-items-center text-bg-dark border-0 show position-fixed bottom-0 start-50 translate-middle-x mb-3";
    toast.style.zIndex = '1050';

    // Insert the message inside the toast body
    toast.innerHTML = `<div class="d-flex"><div class="toast-body">${message}</div></div>`;

    // Append toast to the document body
    document.body.appendChild(toast);

    // Remove the toast after 2 seconds
    setTimeout(() => toast.remove(), 2000);
}

/* ---------------- Event Listeners ---------------- */
/* Handles chat form submission by preventing default behavior and sending the message */
document.getElementById('chat-form').addEventListener('submit', function(e) {
    e.preventDefault();
    sendMessage();
});

/* Clears the text input and sends a request to the server to reset stored text */
document.getElementById('clear-text-btn').addEventListener('click', function() {
    document.getElementById('text').value = "";
    fetch('/clear_text', { method: 'POST' })
        .then(res => res.json())
        .then(data => showToast(data.message));
});

/* Clears all user inputs, resets the UI, and notifies the backend to clear session data */
document.getElementById('clear-all-btn').addEventListener('click', function() {
    // Reset text, audio, image inputs, and response area
    document.getElementById('text').value = "";
    document.getElementById('audio').value = "";
    document.getElementById('image').value = "";
    document.getElementById('response').innerHTML = "";
    responseBlocks = [];
    historyItems = [];
    messageMap = [];

    // Reset conversation history display
    const historyDiv = document.getElementById('conversation-history');
    historyDiv.innerHTML = '<p class="text-muted">No messages yet...</p>';

    // Reset document context, summary, and toggle state
    document.getElementById('document').value = "";
    document.getElementById('document-summary').innerHTML = '<p class="text-muted">No document uploaded...</p>';
    documentToggle.checked = false;
    documentIndicator.textContent = "Doc: OFF";
    documentIndicator.classList.remove('active');

    // Inform backend to clear conversation
    fetch('/clear', { method: 'POST' })
        .then(res => res.json())
        .then(data => showToast(data.message));

    // Inform backend to clear uploaded document context
    fetch('/clear_document', { method: 'POST' })
        .then(res => res.json())
        .then(data => showToast(data.message));
});

/* Clears the audio/video input and notifies the backend to remove related data */
document.getElementById('clear-audio-video-btn').addEventListener('click', function() {
    document.getElementById('audio').value = "";
    fetch('/clear_audio_video', { method: 'POST' })
        .then(res => res.json())
        .then(data => showToast(data.message));
});

/* Clears the image input and sends a request to the backend to reset stored image data */
document.getElementById('clear-image-btn').addEventListener('click', function() {
    document.getElementById('image').value = "";
    fetch('/clear_image', { method: 'POST' })
        .then(res => res.json())
        .then(data => showToast(data.message));
});

/* Handles drag-over event on the document drop zone to provide visual feedback */
documentDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    documentDropZone.classList.add('drag-over');
});

/* Removes the visual drag-over effect when the dragged file leaves the drop zone */
documentDropZone.addEventListener('dragleave', () => {
    documentDropZone.classList.remove('drag-over');
});

/* Handles file drop on the document drop zone: removes drag effect and uploads the dropped file */
documentDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    documentDropZone.classList.remove('drag-over');

    // If files are dropped, assign them to the input and trigger upload
    if (e.dataTransfer.files.length > 0) {
        documentInput.files = e.dataTransfer.files;
        uploadDocument(e.dataTransfer.files[0]);
    }
});

/* Allows clicking on the drop zone to open the file picker for document upload */
documentDropZone.addEventListener('click', () => {
    documentInput.click();
});

/* Triggers document upload when a file is selected through the input field */
documentInput.addEventListener('change', () => {
    if (documentInput.files.length > 0) {
        uploadDocument(documentInput.files[0]);
    }
});

/* Uploads a selected document to the server and displays the extracted summary in the UI */
async function uploadDocument(file) {
    // Prepare form data and append the document file
    const formData = new FormData();
    formData.append('document', file);

    try {
        // Send the file to the backend for processing
        const response = await fetch('/upload_document', { method: 'POST', body: formData });
        if (!response.ok) throw new Error(`Upload failed: ${response.status}`);

        // Parse response and display the sanitized summary in the UI
        const result = await response.json();
        const summaryDiv = document.getElementById('document-summary');
        summaryDiv.innerHTML = `<pre>${DOMPurify.sanitize(result.summary)}</pre>`;
    } catch (error) {
        // Log error and show a toast notification
        console.error('Document upload error:', error);
        showToast(`Error: ${error.message}`);
    }
}

/* Updates the document interaction indicator based on toggle state */
documentToggle.addEventListener('change', () => {
    if (documentToggle.checked) {
        documentIndicator.textContent = "Doc: ON";
        documentIndicator.classList.add('active');
    } else {
        documentIndicator.textContent = "Doc: OFF";
        documentIndicator.classList.remove('active');
    }
});

/* Clears the uploaded document, resets UI elements, and informs the backend to remove document context */
document.getElementById('clear-document-btn').addEventListener('click', function() {
    // Reset document input and summary display
    document.getElementById('document').value = ""; 
    document.getElementById('document-summary').innerHTML = '<p class="text-muted">No document uploaded...</p>'; 

    // Disable document interaction toggle and reset its indicator
    documentToggle.checked = false; 
    documentIndicator.textContent = "Doc: OFF";
    documentIndicator.classList.remove('active');

    // Notify backend to clear document context and show confirmation
    fetch('/clear_document', { method: 'POST' })
        .then(res => res.json())
        .then(data => showToast(data.message))
        .catch(() => showToast("Document cleared locally."));
});

// When toggle is turned OFF, clear context
documentToggle.addEventListener('change', () => {
    if (documentToggle.checked) {
        documentIndicator.textContent = "Doc: ON";
        documentIndicator.classList.add('active');
    } else {
        documentIndicator.textContent = "Doc: OFF";
        documentIndicator.classList.remove('active');

        // Do NOT clear summary or call /clear_document.
        // Just inform user that doc interaction is OFF.
        showToast("Document interaction disabled. Document remains uploaded.");
    }
});

