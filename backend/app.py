import time
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware # Make sure to add CORS
import kuzu
from pydantic import BaseModel, Field
import openai
from dotenv import load_dotenv
import io
from main_kuzu import app as kuzu_app  # Import the Kuzu app if needed
from main import app as sqlite_app  # Import the sqlite app if needed
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from gtts import gTTS
import base64
from langchain_openai import ChatOpenAI

load_dotenv()

# Initialize the FastAPI app
app = FastAPI(
    title="Conversational AI API",
    description="A RESTful API for transcription, chat, text-to-speech, and RAG.",
    version="1.0.0"
)

# IMPORTANT: Add CORS middleware to allow requests from your React app
origins = [
    "http://localhost:3000", # Default for Create React App
    "http://localhost:5173", # Default for Vite
    "http://192.168.1.171:5173"
    # Add the actual origin of your React app if it's different
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
]

client = openai.OpenAI()

llm = ChatOpenAI(model="gpt-4.1-mini-2025-04-14", temperature=0)  # Using a powerful model is good for following complex instructions

# --- Pydantic Models for Data Validation ---

class TranscribeResponse(BaseModel):
    """Response model for the /transcribe endpoint."""
    text: str = Field(..., example="Hello, world.")
    stt_time: float = Field(..., example=0.5)

class ChatRequest(BaseModel):
    """Request model for the /chat endpoint."""
    conversation: List[Dict[str, str]] = Field(..., example=[{"role": "user", "content": "Hello"}])
    new_message: str = Field(..., example="What can you do?")
    context: Dict[str, Any] = Field({}, example={"user_id": "123"})

class ChatResponse(BaseModel):
    """Response model for the /chat endpoint."""
    response: str = Field(..., example="I can answer your questions.")

class SpeakRequest(BaseModel):
    """Request model for the /speak endpoint."""
    text: str = Field(..., example="This is a test.")

class SpeakResponse(BaseModel):
    """Response model for the /speak endpoint."""
    audio_url: str = Field(..., example="/audio/response.wav")
    tts_time: float = Field(..., example=0.8)

class ConverseResponse(BaseModel):
    """Response model for the /converse endpoint."""
    response_text: str = Field(..., example="Here is the information you requested.")
    response_audio_url: str = Field(..., example="/audio/converse_response.wav")
    total_time: float = Field(..., example=2.5)

class ResetResponse(BaseModel):
    """Response model for the /reset endpoint."""
    message: str = Field(..., example="Conversation memory has been cleared.")

class UploadDocsResponse(BaseModel):
    """Response model for the /upload_rag_docs endpoint."""
    message: str = Field(..., example="Successfully uploaded 2 documents.")
    filenames: List[str] = Field(..., example=["doc1.pdf", "doc2.txt"])


# --- API Endpoints ---

@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Accepts an audio file and returns the transcribed text and processing time.
    """
    audio_bytes = await audio.read()

    audio_file_like_object = io.BytesIO(audio_bytes)
    audio_file_like_object.name = audio.filename # Important for some libraries

    start_time = time.time()
    transcribed_text = client.audio.transcriptions.create(
        file=audio_file_like_object,
        model="whisper-1"
    ).text
    stt_time = time.time() - start_time
    return {"text": transcribed_text, "stt_time": stt_time}

@app.post("/chat", response_model=ChatResponse)
async def chat_with_llm(request: ChatRequest):
    """
    Accepts conversation history, a new message, and context to return a response from the LLM.
    """
    # Placeholder for actual chat logic
    messages = []
    for msg in request.conversation[1:]:
        if msg['role'] == 'user':
            messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            messages.append(AIMessage(content=msg['content']))
    try:
        kuzu_events = kuzu_app.stream({"messages": messages}, {'recursion_limit': 10})  # Call the Kuzu app if needed
        for event in kuzu_events:
            if "agent" in event:
                print(event["agent"]["messages"][-1])
            if "execute_tool" in event:
                print(event["execute_tool"]["messages"][-1])
        kuzu_final_state = kuzu_app.invoke({"messages": messages})
        kuzu_response = kuzu_final_state['messages'][-1].content if kuzu_final_state['messages'] else "No response generated."

        sqlite_events = sqlite_app.stream({"messages": messages}, {'recursion_limit': 10})  # Call the SQLite app if needed
        for event in sqlite_events:
            if "agent" in event:
                print(event["agent"]["messages"][-1])
            if "execute_tool" in event:
                print(event["execute_tool"]["messages"][-1])
        sqlite_final_state = sqlite_app.invoke({"messages": messages})
        sqlite_response = sqlite_final_state['messages'][-1].content if sqlite_final_state['messages'] else "No response generated."
        query = f'''Answer {request.new_message} using the following context generated from two models. Using Kuzu DB, the response is: {kuzu_response} and using SQLite DB, the response is: {sqlite_response}. Compile the answers and return a single response. '''

        result = llm.invoke(messages + [HumanMessage(content=query)])
        response = result.content.strip()
    except Exception as e:
        return {"response": f"Error occurred: {e}"}
    return {"response": response}

@app.post("/speak", response_model=SpeakResponse)
async def text_to_speech(request: SpeakRequest):
    """
    Accepts text and returns an audio representation and processing time.
    """
    start_time = time.time()

    if not request.text.strip():
        # Handle empty text case
        return {"audio_url": "", "tts_time": 0}

    try:
        # 1. Create the TTS object with the text
        tts = gTTS(text=request.text, lang='en')

        # 2. Save the audio to an in-memory file (BytesIO)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0) # Rewind the file pointer to the beginning

        # 3. Read the bytes and encode them to base64
        audio_bytes = audio_fp.read()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        tts_time = time.time() - start_time

        # 4. Return the response in the format the frontend expects
        return {"audio_url": audio_base64, "tts_time": tts_time}

    except Exception as e:
        print(f"Error during TTS: {e}")
        # Return an empty response or an error message if something goes wrong
        return {"audio_url": "", "tts_time": time.time() - start_time}

@app.post("/converse", response_model=ConverseResponse)
async def end_to_end_conversation(audio: UploadFile = File(...)):
    """
    End-to-end pipeline that takes a voice query and returns a spoken response.
    """
    start_time = time.time()
    # This would chain the /transcribe, /chat, and /speak logic
    # 1. Transcribe audio to text
    # 2. Use transcribed text to chat with LLM (with RAG)
    # 3. Convert LLM text response back to speech
    response_text = f"Full pipeline response for {audio.filename}"
    response_audio_url = "/audio/end_to_end_response.wav"
    total_time = time.time() - start_time
    return {
        "response_text": response_text,
        "response_audio_url": response_audio_url,
        "total_time": total_time,
    }

@app.post("/reset", response_model=ResetResponse)
async def reset_conversation():
    """
    Clears the conversation memory for the user session.
    """
    # Placeholder for clearing conversation history logic
    messages.clear()
    messages.append({"role": "system", "content": "You are a helpful assistant."})
    # Return a confirmation message
    return ResetResponse(message="Conversation memory has been cleared.")

@app.post("/upload_rag_docs", response_model=UploadDocsResponse)
async def upload_rag_documents(files: List[UploadFile] = File(...)):
    """
    Uploads a list of documents (PDF, TXT, CSV, JSON) to the RAG knowledge base.
    """
    allowed_extensions = {"pdf", "txt", "csv", "json"}
    uploaded_filenames = []

    for file in files:
        extension = file.filename.split(".")[-1]
        if extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{extension}' not supported. Please upload PDF, TXT, CSV, or JSON."
            )
        # Placeholder for actual file processing and storage logic
        # For example, save the file to a specific directory:
        # with open(f"rag_documents/{file.filename}", "wb") as buffer:
        #     buffer.write(await file.read())
        uploaded_filenames.append(file.filename)

    return {
        "message": f"Successfully uploaded {len(uploaded_filenames)} documents.",
        "filenames": uploaded_filenames
    }

# To run this app, save it as `main.py` and run `uvicorn main:app --reload`

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")