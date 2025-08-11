Swasth AI: A Fundamentals-Focused AI Nutritionist
Welcome to Swasth AI, a technical demonstration of a Retrieval-Augmented Generation (RAG) system for a friendly AI nutritionist. This project is built using Streamlit, LangChain, LangGraph, and MongoDB Atlas.

1. Prerequisites
Before you begin, ensure you have the following software and accounts set up:

Python 3.9+ installed on your system.

A MongoDB Atlas account for your database.

A Google AI Studio API key for the Gemini model.

A Tavily Search API key for external information retrieval (optional but recommended).

2. Project Setup
Follow these steps to set up the project environment and dependencies.

Step 2.1: Create a Virtual Environment
It is highly recommended to use a virtual environment to manage project dependencies. This isolates the project's packages from your system's global Python packages.

# Create the virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

Step 2.2: Install Dependencies
With your virtual environment active, install the required Python packages. If a requirements.txt file is available, use that. Otherwise, install them manually.

# Install from requirements.txt (if available)
pip install -r requirements.txt

# Or, install manually if you don't have a requirements.txt
pip install streamlit langchain langchain-google-genai langchain_community pydantic python-dotenv pymongo

Step 2.3: Configure the .env File
Create a file named .env in the root directory of your project. This file will store your sensitive API keys and database connection string. Replace the placeholder values with your actual credentials.

MONGO_URI="your_mongodb_atlas_connection_string"
GOOGLE_API_KEY="your_google_ai_studio_api_key"
TAVILY_API_KEY="your_tavily_search_api_key"

Step 2.4: Set up the MongoDB Vector Search Index
For the RAG system to work, you must create a vector search index in your MongoDB Atlas cluster. This index allows for efficient semantic searches on the embedding vectors.

Create a new search index on your recipes_and_foods collection using the following JSON definition:

{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": {
        "dimensions": 768,
        "similarity": "cosine",
        "type": "knnVector"
      }
    }
  }
}

3. Running the Project
Once the setup is complete, you can start the application using Streamlit.

# Make sure your virtual environment is active
# Navigate to the correct directory to run the main file
cd app

# Run the Streamlit application
streamlit run main.py

