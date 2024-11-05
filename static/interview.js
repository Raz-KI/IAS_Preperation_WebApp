// Capture video feed
document.addEventListener("DOMContentLoaded", () => {
    navigator.mediaDevices.getUserMedia({ video: true })
        .then((stream) => {
            document.getElementById('videoFeed').srcObject = stream;

            const videoElement = document.getElementById('videoFeed');
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');

            // Ensure the canvas matches the video feed's dimensions
            videoElement.addEventListener('loadedmetadata', () => {
                canvas.width = videoElement.videoWidth;
                canvas.height = videoElement.videoHeight;
            });

            // Capture frames at regular intervals
            setInterval(() => {
                context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
                
                // Get image data from canvas
                canvas.toBlob((blob) => {

                    
                    if (blob) {  // Ensure blob is valid
                        const formData = new FormData();
                        formData.append('frame', blob, 'frame.png');

                        // Send the frame to the backend for analysis
                        fetch('/api/analyze_frame', {
                            method: 'POST',
                            body: formData
                        })
                        .then(response => response.json())
                        .then(data => {
                            
                        })
                        .catch(error => console.error('Error processing frame:', error));
                    }
                }, 'image/png');
            }, 2000);  // Send frame every 2 seconds
        })
        .catch((error) => {
            console.error('Error accessing the video feed: ', error);
        });
});










// Speech recognition setup (Web Speech API)
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();

// Set interim results to true to get results while the user is speaking
recognition.interimResults = false; 

// Start the interview with the first AI question: "Introduce yourself"
window.onload = () => {
    // startInterview();
    setTimeout(startInterview, 1000);
};

// Function to speak text using Web Speech API
function speakText(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
}

function startInterview() {
    fetch('/api/start_interview')
        .then(response => response.json())
        .then(data => {
            document.getElementById('ai-question').innerHTML = data.question;
            setTimeout(() => {
                speakText(data.question); // Speak the question after 3 seconds
            }, 1000); // 3000 milliseconds = 3 seconds
            addToHistory('AI', data.question);
        });
}

let followUpCount = 0;
// Start microphone and process speech input
function startMicrophone() {
    recognition.start();
    
    // Notify user that mic is recording
    document.getElementById('user-answer').innerHTML = 'Listening...';

    recognition.onresult = (event) => {
        const userResponse = event.results[0][0].transcript; // Get the transcribed speech text
        document.getElementById('user-answer').innerHTML = `You said: ${userResponse}`;
        
        // Add to history
        addToHistory('User', userResponse);

        // Send user response to the server for AI follow-up question
        fetch('/api/answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ answer: userResponse, follow_up_count: followUpCount })
        })
        .then(response => response.json())
        .then(data => {
            const aiQuestion = data.follow_up;
            document.getElementById('ai-question').innerHTML = aiQuestion;

            speakText(aiQuestion);
    
            // Update history with AI's question
            addToHistory('AI', aiQuestion);
    
            followUpCount++;
        });
    };

    recognition.onerror = (event) => {
        document.getElementById('user-answer').innerHTML = 'Error: ' + event.error;
    };

    recognition.onend = () => {
        document.getElementById('user-answer').innerHTML = 'You can click the button to speak again.';
    };
}

// Function to update history panel with conversation
function addToHistory(speaker, text) {
    const historyDiv = document.getElementById('history');
    const newEntry = document.createElement('p');
    newEntry.textContent = `${speaker}: ${text}`;
    historyDiv.appendChild(newEntry);
    historyDiv.scrollTop = historyDiv.scrollHeight;  // Auto-scroll to the bottom
}

// Function to end the interview and get overall feedbackf
document.getElementById('stopInterviewBtn').addEventListener('click', () => {
    fetch('/api/end_interview')
        .then(response => response.text())
        .then(data => {
            // Load the results page
            document.body.innerHTML = data;
        });
});

// Function to stop the microphone
function stopMicrophone() {
  recognition.stop();  // Stop listening
  document.getElementById('user-answer').innerHTML = 'Microphone stopped. You can click the button or hold the space bar to speak again.';
}

// Add event listeners for the start button (Hold to Talk)
const startListeningBtn = document.getElementById('micButton');

startListeningBtn.addEventListener('mousedown', startMicrophone); // Start on mouse down
startListeningBtn.addEventListener('mouseup', stopMicrophone);    // Stop on mouse up

// Add space bar control
document.addEventListener('keydown', (event) => {
    if (event.code === 'Space') {
        event.preventDefault(); // Prevent scrolling when space is pressed
        startMicrophone(); // Start listening when space is pressed
    }
});

document.addEventListener('keyup', (event) => {
    if (event.code === 'Space') {
        stopMicrophone(); // Stop listening when space is released
    }
});