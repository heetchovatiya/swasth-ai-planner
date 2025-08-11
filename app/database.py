# app/database.py

import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

class Database:
    """
    Handles all interactions with the MongoDB database for user profiles,
    meal plans, and favorite recipes.
    """
    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI not found in environment variables.")
        
        client = MongoClient(mongo_uri)
        # Main DB for recipes
        self.recipes_collection = client["swasth_dashboard_db"]["recipes_and_foods"]
        # DB for user-specific data
        user_db = client["swasth_user_data"]
        self.profiles_collection = user_db["profiles"]
        # self.plans_collection = user_db["saved_plans"]
        # self.favorites_collection = user_db["favorites"]

    # --- Profile Methods ---
    def get_user_profile(self, user_id: str):
        return self.profiles_collection.find_one({"_id": user_id})

    def save_user_profile(self, user_id: str, profile_data: dict):
        profile_data['last_weight_update'] = datetime.utcnow()
        self.profiles_collection.update_one(
            {"_id": user_id},
            {"$set": profile_data},
            upsert=True
        )
    
    def check_needs_weight_update(self, user_id: str) -> bool:
        """Checks if it has been more than 15 days since the last weight update."""
        profile = self.get_user_profile(user_id)
        if not profile or 'last_weight_update' not in profile:
            return True # If no record, they need to update
        
        last_update = profile['last_weight_update']
        if datetime.utcnow() - last_update > timedelta(days=15):
            return True
        return False

    # --- Saved Plan Methods ---
    def save_meal_plan(self, user_id: str, plan_name: str, plan_data: dict):
        self.plans_collection.update_one(
            {"user_id": user_id, "name": plan_name},
            {"$set": {"plan": plan_data, "saved_at": datetime.utcnow()}},
            upsert=True
        )

    # def get_saved_plans(self, user_id: str):
    #     return list(self.plans_collection.find({"user_id": user_id}).sort("saved_at", -1))
    
    # # --- Favorites Methods ---
    # def save_favorite_item(self, user_id: str, item_name: str, item_data: dict):
    #     self.favorites_collection.update_one(
    #         {"user_id": user_id, "item_name": item_name},
    #         {"$set": {"item_data": item_data, "saved_at": datetime.utcnow()}},
    #         upsert=True
    #     )

    # def get_favorite_items(self, user_id: str):
    #     return list(self.favorites_collection.find({"user_id": user_id}).sort("saved_at", -1))

# Create a single, reusable instance for the app
db_instance = Database()