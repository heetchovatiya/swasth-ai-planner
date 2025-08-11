import os
import json
import logging
from pydantic import BaseModel, Field

from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_community.embeddings import HuggingFaceBgeEmbeddings

from database import db_instance

# --- Pydantic Schemas ---
class MealItem(BaseModel):
    meal_time: str = Field(description="The time of day for the meal, e.g., 'Breakfast', 'Lunch', 'Dinner'.")
    meal_name: str = Field(description="The name of the recommended dish.")
    justification: str = Field(description="A brief, friendly reason why this meal was chosen for the user.")

class MealPlan(BaseModel):
    greeting: str = Field(description="A friendly, encouraging opening message for the user.")
    plan: list[MealItem] = Field(description="A list of meal items for the day.")
    summary: str = Field(description="A concluding summary of the meal plan.")

# --- Initialize Tools and Chains ---
try:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.5)
    tavily_tool = TavilySearchResults(max_results=3)
    embeddings = HuggingFaceBgeEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        encode_kwargs={'normalize_embeddings': True}
    )
    vector_store = MongoDBAtlasVectorSearch(
        collection=db_instance.recipes_collection,
        embedding=embeddings,
        index_name="vector_search_index"
    )
except Exception as e:
    logging.error(f"Failed to initialize tools/chains. Check API keys and DB connection. Error: {e}")
    llm = None

# --- NEW: Multi-language Translation Tool ---
@tool
def translate_text(text_to_translate: str, target_language: str) -> str:
    """
    Translates a given text into the specified target language using an LLM.
    If the target language is English, it returns the text without calling the LLM.
    """
    if target_language.lower() == 'english':
        return text_to_translate
    if not llm:
        return f"(Translation unavailable) {text_to_translate}"

    try:
        prompt = PromptTemplate.from_template(
            "You are a professional translator. Translate the following text into {language}. "
            "Preserve the original formatting (like markdown for lists or bold text) and tone as much as possible.\n\n"
            "TEXT TO TRANSLATE:\n---\n{text}\n---\n\n"
            "TRANSLATED TEXT:"
        )
        chain = prompt | llm
        translated_text = chain.invoke({
            "text": text_to_translate,
            "language": target_language
        }).content
        return translated_text
    except Exception as e:
        logging.error(f"Translation failed: {e}")
        return f"(Translation failed) {text_to_translate}"

# --- MODIFIED: Meal Planner now correctly filters your existing database schema ---
@tool
def create_meal_plan(user_request: str, profile_summary: str, allergies: str, diet_preference: str) -> str:
    """
    Creates a personalized, full-day meal plan. Use this when the user asks for a plan,
    suggestions, or ideas for what to eat. This tool will retrieve relevant recipes
    from the database and generate a structured plan.
    """
    if not llm or not vector_store: # --- MODIFIED: Check for vector_store, not retriever
        return json.dumps({"error": "Planning tool is not available due to an initialization error."})

    try:
        # --- STEP 1: RETRIEVE BROADLY (No pre-filter) ---
        contextual_query = f"{user_request} suitable for a person with this profile: {profile_summary}. Must not contain: {allergies}"
        
        # --- THE FIX: Create a new retriever instance with the desired settings ---
        # This avoids the NameError by not trying to modify a global variable.
        local_retriever = vector_store.as_retriever(search_kwargs={"k": 30})
        
        # Use the newly created local_retriever
        docs = local_retriever.get_relevant_documents(contextual_query)


        # --- STEP 2: FILTER IN-MEMORY (The Post-Filter Logic) ---
        # This part of the logic is correct and remains unchanged.
        filtered_docs = []
        if diet_preference.lower() == "any":
            filtered_docs = docs
        else:
            for doc in docs:
                doc_diet_tags = doc.metadata.get("dietary_tags", [])
                is_veg = "Vegetarian" in doc_diet_tags

                if diet_preference.lower() == "vegetarian" and is_veg:
                    filtered_docs.append(doc)
                elif diet_preference.lower() == "non-vegetarian" and not is_veg:
                    filtered_docs.append(doc)

        # --- STEP 3: PROCEED WITH THE FILTERED LIST ---
        if not filtered_docs:
            error_msg = "I couldn't find any matching recipes in my cookbook for your request after applying your dietary preference."
            return json.dumps({"error": error_msg})

        meal_options_text = "\n".join([f"- {doc.metadata.get('item_name', '')}: {doc.page_content}" for doc in filtered_docs])
        
        parser = JsonOutputParser(pydantic_object=MealPlan)
        prompt = PromptTemplate(
            template="You are 'Swa-Swa', a friendly food buddy. Create a personalized, full-day meal plan based on the user's profile and the provided meal options.\n{format_instructions}\n\nUSER PROFILE: {profile_summary}\n\nUSER'S REQUEST: {request}\n\nAVAILABLE MEAL OPTIONS:\n{meal_options}\n\nYOUR JSON RESPONSE:",
            input_variables=["request", "profile_summary", "meal_options"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        chain = prompt | llm | parser
        
        result = chain.invoke({
            "request": user_request,
            "profile_summary": profile_summary,
            "meal_options": meal_options_text
        })
        return json.dumps(result)
        
    except Exception as e:
        logging.error(f"Error in create_meal_plan tool: {e}")
        return json.dumps({"error": "I had trouble creating your plan. Please try asking in a different way."})

# --- TOOL 2: SMART, COMBINED RECIPE DETAILS GETTER (No changes needed) ---
@tool
def get_recipe_details(item_name: str) -> str:
    """
    Retrieves all available details for a SINGLE food item. It first checks the local
    database, then ALWAYS searches the web for a YouTube video link. Use this tool whenever a
    user asks for details, instructions, or how to make a specific item like 'dhokla'.
    """
    db_details = db_instance.recipes_collection.find_one(
        {"item_name": {"$regex": f"^{item_name}$", "$options": "i"}},
        {"_id": 0}
    )
    
    yt_link = "Not found"
    web_summary = ""
    try:
        search_results = tavily_tool.invoke({
            "query": f"What is the best YouTube video recipe for {item_name}? Also provide a brief summary of the dish."
        })
        for res in search_results:
            if "youtube.com" in res.get('url', '') and yt_link == "Not found":
                yt_link = res['url']
            if not web_summary:
                web_summary = res.get('content', '')

    except Exception as e:
        logging.error(f"Tavily search failed for '{item_name}': {e}")
        yt_link = "Search failed"
        web_summary = "Could not search online for more details."
        
    if not db_details:
        return json.dumps({
            "status": "WEB_ONLY",
            "item_name": item_name,
            "summary": web_summary or "I don't have this in my cookbook, but here is some information I found online.",
            "youtube_link": yt_link
        })
    else:
        return json.dumps({
            "status": "FOUND_IN_DB",
            "db_data": db_details,
            "youtube_link": yt_link
        })