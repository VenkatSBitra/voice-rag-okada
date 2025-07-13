# AI-Powered Real Estate RAG API

This repository contains the complete backend for an advanced conversational AI system. It leverages a Kuzu graph database, a LangGraph-powered agent for complex querying, and a FastAPI server to expose a robust API for real estate data interaction. The system can understand natural language questions, perform semantic searches on property data, and generate spoken responses.

-----

## Architecture Overview

The backend is composed of three main components:

1.  **Database Builder (`build_kuzu_db.py`)**: A script that reads a CSV file, cleans the data, generates vector embeddings for property addresses using the OpenAI API, and builds a Kuzu graph database to store the structured and vectorized data.
2.  **RAG Agent (`main_kuzu.py`)**: A sophisticated agent built with LangChain and LangGraph. It uses a large language model (LLM) to interpret user questions, perform either semantic or structured queries against the Kuzu database, and formulate a precise answer.
3.  **API Server (`app.py`)**: A FastAPI application that serves the entire functionality through a set of well-defined RESTful endpoints. It handles audio transcription (Speech-to-Text), chat interactions with the RAG agent, and audio generation (Text-to-Speech).

-----

## Features

### Core Backend

  - **Graph Database**: Uses **Kuzu**, a fast, embeddable graph database, to store and query interconnected real estate data (Brokers, Listings, Associates).
  - **Hybrid Data Storage**: Stores both the original text data (e.g., "$5,000") and cleaned, numeric versions (e.g., 5000.0) for flexible querying.
  - **Vector Embeddings**: Generates embeddings for property addresses using **OpenAI's `text-embedding-3-small` model** to enable powerful semantic search.

### Intelligent RAG Agent

  - **LangGraph Implementation**: Orchestrates complex logic using a stateful graph, allowing for more reliable and multi-step reasoning.
  - **Dynamic Query Generation**: The agent dynamically generates Cypher queries based on the user's natural language question and the database schema.
  - **Smart Query Routing**: An internal LLM-based router intelligently determines whether a user's question is a general query or a specific address search, optimizing the query strategy.
  - **Semantic Search**: For address-related questions, it performs a vector similarity search to find the most relevant property, even if the user's query has typos or variations.

### High-Performance API

  - **FastAPI Framework**: Provides a modern, high-performance, and asynchronous API server.
  - **CORS Enabled**: Pre-configured with Cross-Origin Resource Sharing (CORS) middleware to allow requests from your frontend application.
  - **Speech-to-Text**: Integrates with **OpenAI's Whisper-1** model for fast and accurate audio transcription.
  - **Text-to-Speech**: Uses **Google Text-to-Speech (gTTS)** to convert the agent's text responses into audible speech, returning a base64-encoded audio string for easy frontend integration.
  - **Clear API Schema**: Uses Pydantic models for robust data validation and automatic generation of interactive API documentation (via `/docs`).

-----

## Setup and Installation

Follow these steps to set up and run the backend system. A `requirements.txt` file is required.

### Step 1: Create and Activate a Virtual Environment

It is highly recommended to use a virtual environment to manage dependencies and avoid conflicts.

```bash
# Create a virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### Step 2: Install Dependencies

With your virtual environment activated, install all the necessary Python packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### Step 3: Set Up Environment Variables

This project requires an API key from OpenAI. Create a file named `.env` in the root directory of the project.

```text
# .env file
OPENAI_API_KEY="your-openai-api-key-here"
```

### Step 4: Prepare Your Data

Place your source data file, `HackathonInternalKnowledgeBase.csv`, inside a `data` directory in the project's root. The file path should be `data/HackathonInternalKnowledgeBase.csv`.

### Step 5: Build the Kuzu Graph Database

Run the `build_kuzu_db.py` script. This will read the CSV, process the data, generate embeddings, and create the `kuzu_real_estate_db` directory containing the database files.

```bash
python build_kuzu_db.py
```

You only need to run this script once, or whenever your source CSV data changes.

### Step 6: Run the FastAPI Server

Now, you can start the API server.

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

  - `--host 0.0.0.0` makes the server accessible on your local network.
  - `--port 8000` is the port your frontend will connect to.
  - `--reload` automatically restarts the server when you make changes to the code.

The API is now running and ready to accept requests from your React frontend.

-----

## API Endpoints

The server provides the following endpoints, which are designed to be used by the frontend application:

#### `POST /transcribe`

  - **Description**: Receives an audio file, transcribes it to text using Whisper.
  - **Request Body**: `multipart/form-data` with an `audio` file.
  - **Response**: `{"text": "Transcribed text", "stt_time": 1.2}`

#### `POST /chat`

  - **Description**: The main interaction endpoint. Takes the conversation history and a new message, passes it to the LangGraph agent, and returns the agent's text response.
  - **Request Body**: `{"conversation": [...], "new_message": "...", "context": {}}`
  - **Response**: `{"response": "The agent's answer based on the database."}`

#### `POST /speak`

  - **Description**: Converts text into speech.
  - **Request Body**: `{"text": "Some text to convert to audio."}`
  - **Response**: `{"audio_url": "base64-encoded-audio-string", "tts_time": 0.9}`

#### `POST /reset`

  - **Description**: Clears the conversation history on the server.
  - **Response**: `{"message": "Conversation memory has been cleared."}`