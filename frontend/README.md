# AI Voice Chat Frontend

This is a feature-rich, responsive frontend for an AI voice chat application built with React. It allows users to interact with an AI assistant through either text or voice, providing a seamless and interactive conversational experience.



---

## Features

This application comes with a comprehensive set of features designed for a modern voice-first AI experience:

### 🗣️ Dual Interaction Modes
-   **Text Input**: A classic chat input field for typing messages.
-   **Voice Input**: Record your voice directly in the browser. The app captures the audio, allows for playback, and sends it for transcription.

### 🔊 Core Audio Functionality
-   **In-Browser Recording**: Uses the `MediaRecorder` API to capture microphone input securely.
-   **Audio Playback**: Both the user's recorded audio and the AI's generated response can be played back directly in the chat interface.
-   **Automatic Playback**: The latest AI audio response plays automatically for a hands-free experience.

### ⚙️ Seamless API Integration
-   **Transcription**: Sends recorded audio to a backend for Speech-to-Text (STT) conversion.
-   **Chat Logic**: Sends user messages (text or transcribed) and conversation history to a backend to get an intelligent response.
-   **Speech Synthesis**: Sends the AI's text response to a backend for Text-to-Speech (TTS) conversion, receiving audio data back.

### ✨ Modern User Experience
-   **Real-time Status Updates**: The UI displays the current status of the application, such as "Recording...", "Transcribing...", "Assistant is thinking...", keeping the user informed.
-   **Performance Metrics**: Displays the time taken for both transcription and speech synthesis, offering insights into system performance.
-   **Dynamic Chat History**: A clean, auto-scrolling chat window that displays the conversation in a familiar, organized way.
-   **Error Handling**: Gracefully handles and displays errors, such as microphone permission denial or API failures.
-   **Conversation Reset**: A simple one-click button to clear the current conversation and start fresh on both the client and server.

### 🎨 Sleek & Responsive Design
-   **Tailwind CSS**: Styled with Tailwind CSS for a modern, utility-first design.
-   **SVG Icons**: Includes a set of clean, self-contained SVG icons for a polished look and feel.
-   **Responsive Layout**: The interface is optimized for both desktop and mobile devices.

---

## Setup and Installation

To run this frontend, you need to have a compatible backend server running and have Node.js and `npm` (or `yarn`) installed.

### 1. Backend Server Requirements

This frontend is designed to communicate with a backend that exposes the following API endpoints:

-   **`POST /transcribe`**:
    -   **Request**: `multipart/form-data` with an `audio` file (`audio.wav`).
    -   **Response**: JSON `{"text": "transcribed user text", "stt_time": 0.5}`.
-   **`POST /chat`**:
    -   **Request**: JSON `{"conversation": [...history], "new_message": "user's latest message"}`.
    -   **Response**: JSON `{"response": "The AI assistant's text response"}`.
-   **`POST /speak`**:
    -   **Request**: JSON `{"text": "The AI assistant's text response"}`.
    -   **Response**: JSON `{"audio_url": "base64-encoded-wav-string", "tts_time": 0.8}`.
-   **`POST /reset`**:
    -   **Request**: No body required.
    -   **Response**: A success status code (e.g., 200 OK).

### 2. Frontend Setup

Follow these steps to get the React application running:

**Step 1: Clone the Repository**
```bash
git clone <your-repository-url>
cd <repository-folder>
```

**Step 2: Install Dependencies**
```bash
npm install
# or
yarn install
```

**Step 3: Configure API Base URL**
Open `src/App.jsx` and set the `API_BASE_URL` to point to your backend server:
```javascript
const API_BASE_URL = "http://your-backend-server:8000";
```

**Step 4: Start the Development Server**
```bash
npm run dev
# or
yarn dev
```

This will start the Vite development server, and you can access the application at `http://localhost:5173` (or the specified host).

## Usage Instructions

### Prerequisites
- Ensure your browser supports the `MediaRecorder` API (most modern browsers do).
- Allow microphone access when prompted by your browser.

### User Interface Overview
- **Chat Window**: Displays the conversation history with both user and assistant messages.
- **Input Area**: Contains a text input field and a button to start voice recording.
- **Recording Controls**: Buttons to start and stop recording, and to send the recorded audio.
- **Status Display**: Shows the current status of the application (e.g., "Recording...").

### Recording and Sending Messages
- **To Record Voice**:
  1. Click the microphone icon to start recording.
  2. Speak your message clearly.
  3. Click the stop button to finish recording.
  4. The app will automatically transcribe the audio and send it to the backend.    

- **To Send Text**:
  1. Type your message in the text input field.
  2. Press Enter or click the send button to submit.

### Listening to Responses
- The AI's response will be played automatically after it is received.
- You can also click the play button next to the assistant's message to replay the audio.
