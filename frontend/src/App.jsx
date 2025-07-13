import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

// --- Helper Components ---

// Icon components for better UI. Using SVG for self-containment.
const MicIcon = ({ className }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
        <line x1="12" x2="12" y1="19" y2="22"></line>
    </svg>
);

const StopCircleIcon = ({ className }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <rect width="6" height="6" x="9" y="9"></rect>
    </svg>
);

const SendIcon = ({ className }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m22 2-7 20-4-9-9-4Z"></path>
        <path d="M22 2 11 13"></path>
    </svg>
);

const BotIcon = ({ className }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 8V4H8"></path>
        <rect width="16" height="12" x="4" y="8" rx="2"></rect>
        <path d="M2 14h2"></path><path d="M20 14h2"></path>
        <path d="M15 13v2"></path><path d="M9 13v2"></path>
    </svg>
);

const UserIcon = ({ className }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
        <circle cx="12" cy="7" r="4"></circle>
    </svg>
);

const RefreshCwIcon = ({ className }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path>
        <path d="M21 3v5h-5"></path>
        <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path>
        <path d="M3 21v-5h5"></path>
    </svg>
);

// --- Main Application Component ---

export default function App() {
    // --- State Management ---
    const [messages, setMessages] = useState([
        { role: "assistant", content: "Hello! How can I help you today?" }
    ]);
    const [isRecording, setIsRecording] = useState(false);
    const [audioBlob, setAudioBlob] = useState(null);
    const [audioUrl, setAudioUrl] = useState(null);
    const [status, setStatus] = useState('idle'); // idle, recording, transcribing, thinking, speaking
    const [error, setError] = useState(null);
    const [inputText, setInputText] = useState('');
    const [transcribeTime, setTranscribeTime] = useState(null);
    const [speakTime, setSpeakTime] = useState(null);

    // --- Refs for Media and DOM Elements ---
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const chatEndRef = useRef(null);

    // --- API Configuration ---
    const API_BASE_URL = "http://127.0.0.1:8000";
    // const API_BASE_URL = "http://192.168.1.171:8000";
    const TRANSCRIBE_URL = `${API_BASE_URL}/transcribe`;
    const CHAT_URL = `${API_BASE_URL}/chat`;
    const SPEAK_URL = `${API_BASE_URL}/speak`;
    const RESET_URL = `${API_BASE_URL}/reset`;

    // --- Effects ---
    // Effect to scroll to the latest message
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, status]);

    // --- Core Logic Functions ---

    /**
     * Handles the entire chat flow from user text to assistant's audio response.
     * @param {string} text - The user's message.
     * @param {Blob} audioBlob - The audio blob to be sent for processing.
     */
    const processChat = async (text, audioBlob = null) => {
        if (!text.trim()) return;

        // Add user message to chat immediately for better UX
        let userMessage = { role: "user", content: text };
        if (audioBlob) {
            const audioBase64 = await audioBlob.arrayBuffer();
            const audioSrc = `data:audio/wav;base64,${btoa(String.fromCharCode(...new Uint8Array(audioBase64)))}`;

            userMessage = { role: "user", content: text, audio: audioSrc };
        }
        setMessages(prev => [...prev, userMessage]);
        setError(null);

        try {
            // 1. Get assistant's text response
            setStatus('thinking');
            const history = [...messages, userMessage].filter(msg => !msg.audio);
            const chatResponse = await axios.post(CHAT_URL, {
                conversation: history,
                new_message: text
            });
            const assistantText = chatResponse.data.response;
            if (!assistantText) throw new Error("No response from assistant.");

            // 2. Get assistant's audio response
            setStatus('speaking');
            const speakResponse = await axios.post(SPEAK_URL, { text: assistantText });
            const audioBase64 = speakResponse.data.audio_url;
            const speakDuration = speakResponse.data.tts_time;
            setSpeakTime(speakDuration);
            const audioSrc = `data:audio/wav;base64,${audioBase64}`;

            // 3. Add assistant's full response to chat
            setMessages(prev => [...prev, { role: "assistant", content: assistantText, audio: audioSrc }]);

        } catch (err) {
            console.error("Chat processing error:", err);
            setError("Sorry, I encountered an error. Please try again.");
            // Add an error message to the chat
            setMessages(prev => [...prev, { role: "assistant", content: "I seem to have run into a problem. Could you try that again?" }]);
        } finally {
            setStatus('idle');
        }
    };

    /**
     * Handles text input submission.
     */
    const handleTextSubmit = (e) => {
        e.preventDefault();
        processChat(inputText);
        setInputText('');
    };

    /**
     * Starts the audio recording process.
     */
    const startRecording = async () => {
        setError(null);
        setAudioBlob(null);
        if (audioUrl) URL.revokeObjectURL(audioUrl);
        setAudioUrl(null);

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorderRef.current = new MediaRecorder(stream);
            audioChunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (event) => {
                audioChunksRef.current.push(event.data);
            };

            mediaRecorderRef.current.onstop = () => {
                const blob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
                setAudioBlob(blob);
                const url = URL.createObjectURL(blob);
                setAudioUrl(url);
                // Stop all media tracks to turn off the mic indicator
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorderRef.current.start();
            setIsRecording(true);
            setStatus('recording');
        } catch (err) {
            console.error("Error starting recording:", err);
            setError("Could not start recording. Please grant microphone permission.");
            setStatus('idle');
        }
    };

    /**
     * Stops the audio recording.
     */
    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            setStatus('idle');
        }
    };

    /**
     * Sends the recorded audio for transcription and processing.
     */
    const sendRecording = async () => {
        if (!audioBlob) return;

        setStatus('transcribing');
        setError(null);

        const formData = new FormData();
        formData.append('audio', audioBlob, 'audio.wav');

        try {
            const transcribeResponse = await axios.post(TRANSCRIBE_URL, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            const transcribedText = transcribeResponse.data.text;
            const duration = transcribeResponse.data.stt_time;
            setTranscribeTime(duration);
            if (transcribedText) {
                await processChat(transcribedText, audioBlob);
            } else {
                setError("Transcription failed. Please try recording again.");
            }
        } catch (err) {
            console.error("Transcription error:", err);
            setError("Failed to transcribe audio. Please try again.");
        } finally {
            setStatus('idle');
            setAudioBlob(null);
            if (audioUrl) URL.revokeObjectURL(audioUrl);
            setAudioUrl(null);
        }
    };

    /**
     * Resets the entire conversation state.
     */
    const resetConversation = async () => {
        try {
            await axios.post(RESET_URL);
            setMessages([{ role: "assistant", content: "Conversation reset. How can I help?" }]);
            setError(null);
            setStatus('idle');
            setAudioBlob(null);
            if (audioUrl) URL.revokeObjectURL(audioUrl);
            setAudioUrl(null);
            setIsRecording(false);
            if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
                mediaRecorderRef.current.stop();
            }
        } catch (err) {
            console.error("Reset error:", err);
            setError("Failed to reset conversation on the server.");
        }
    };

    // --- Render Logic ---

    const getStatusMessage = () => {
        switch (status) {
            case 'recording': return "Recording...";
            case 'transcribing': return "Transcribing audio...";
            case 'thinking': return "Assistant is thinking...";
            case 'speaking': return "Generating audio response...";
            default: return null;
        }
    };

    return (
        <div className="font-sans bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col md:flex-row h-screen">
            {/* --- Control Panel (Sidebar) --- */}
            <aside className="w-full md:w-80 lg:w-96 bg-white dark:bg-gray-800/50 border-b md:border-r border-gray-200 dark:border-gray-700 p-6 flex flex-col space-y-6">
                <div className="flex items-center space-x-3">
                    <BotIcon className="w-8 h-8 text-indigo-500" />
                    <h1 className="text-2xl font-bold">AI Voice Chat</h1>
                </div>
                <p className="text-gray-600 dark:text-gray-400">
                    Interact with the assistant by typing or recording your voice.
                </p>

                <div className="flex-grow space-y-6">
                    {/* Audio Recorder Section */}
                    <div className="space-y-4">
                        <h2 className="text-lg font-semibold">Voice Input</h2>
                        <div className="p-4 bg-gray-100 dark:bg-gray-900/50 rounded-lg space-y-4">
                            {!isRecording ? (
                                <button
                                    onClick={startRecording}
                                    disabled={status !== 'idle'}
                                    className="w-full flex items-center justify-center px-4 py-2 bg-indigo-600 text-white rounded-lg shadow-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 dark:disabled:bg-gray-600 transition-colors"
                                >
                                    <MicIcon className="w-5 h-5 mr-2" />
                                    Start Recording
                                </button>
                            ) : (
                                <button
                                    onClick={stopRecording}
                                    className="w-full flex items-center justify-center px-4 py-2 bg-red-600 text-white rounded-lg shadow-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                >
                                    <StopCircleIcon className="w-5 h-5 mr-2" />
                                    Stop Recording
                                </button>
                            )}

                            {audioUrl && (
                                <div className="space-y-3">
                                    <p className="text-sm font-medium">Your recording:</p>
                                    <audio src={audioUrl} controls className="w-full h-10" />
                                    <button
                                        onClick={sendRecording}
                                        disabled={!audioBlob || status !== 'idle'}
                                        className="w-full flex items-center justify-center px-4 py-2 bg-green-600 text-white rounded-lg shadow-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-gray-400 dark:disabled:bg-gray-600 transition-colors"
                                    >
                                        <SendIcon className="w-5 h-5 mr-2" />
                                        Send Recording
                                    </button>
                                </div>
                            )}

                            {transcribeTime && (
                                <div className="text-sm text-gray-500 dark:text-gray-400">
                                    <p>Transcription took: <strong>{transcribeTime.toFixed(2)} seconds</strong></p>
                                </div>
                            )}

                            {speakTime && (
                                <div className="text-sm text-gray-500 dark:text-gray-400">
                                    <p>Speech synthesis took: <strong>{speakTime.toFixed(2) } seconds</strong></p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Controls Section */}
                    <div className="space-y-4">
                        <h2 className="text-lg font-semibold">Controls</h2>
                        <button
                            onClick={resetConversation}
                            className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                        >
                            <RefreshCwIcon className="w-5 h-5 mr-2" />
                            Reset Conversation
                        </button>
                    </div>
                </div>

                {error && <div className="p-3 bg-red-100 dark:bg-red-900/50 border border-red-400 text-red-700 dark:text-red-300 rounded-lg">{error}</div>}
            </aside>

            {/* --- Chat Interface --- */}
            <main className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-800">
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {messages.map((msg, index) => (
                        <div key={index} className={`flex items-end gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {msg.role === 'assistant' && <BotIcon className="w-8 h-8 p-1.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 flex-shrink-1" />}
                            <div className={`max-w-lg lg:max-w-2xl px-4 py-3 rounded-2xl shadow-sm ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200 rounded-bl-none'}`}>
                                <p className="whitespace-pre-wrap">{msg.content}</p>
                                {msg.audio && <audio src={msg.audio} controls autoPlay={index === messages.length - 1} className="w-full mt-3 h-10" />}
                            </div>
                            {msg.role === 'user' && <UserIcon className="w-8 h-8 p-1.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 flex-shrink-1" />}
                        </div>
                    ))}
                    <div ref={chatEndRef} />
                </div>

                {/* Status Indicator */}
                {status !== 'idle' && status !== 'recording' && (
                    <div className="px-6 pb-3 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-500 mr-2"></div>
                        {getStatusMessage()}
                    </div>
                )}

                {/* Message Input Form */}
                <div className="p-4 bg-white dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700">
                    <form onSubmit={handleTextSubmit} className="flex items-center space-x-4">
                        <input
                            type="text"
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            placeholder="What would you like to say?"
                            disabled={status !== 'idle'}
                            className="flex-1 p-3 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                        <button
                            type="submit"
                            disabled={status !== 'idle' || !inputText.trim()}
                            className="p-3 bg-indigo-600 text-white rounded-full shadow-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition-all"
                        >
                            <SendIcon className="w-6 h-6" />
                        </button>
                    </form>
                </div>
            </main>
        </div>
    );
}
