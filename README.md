

 # mongodb (vector search index)
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


# .env
MONGO_URI="your_mongodb_atlas_connection_string"
GOOGLE_API_KEY="your_google_ai_studio_api_key"
TAVILY_API_KEY="your_tavily_search_api_key"

# project start 
cd app
streamlit run main.py


 # to run the project 
 streamlit run app/main.py