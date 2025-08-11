# app/streamlit_app.py

import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
import uuid
from datetime import datetime

# --- MODIFIED: Import our refactored components ---
from planner import MealPlanner
from user_profile import UserProfile
from database import db_instance 
from tools import translate_text # --- NEW: Import the translation tool ---


# --- Page Config (with Dark Theme as default) ---
st.set_page_config(
    page_title="Swasth AI",
    page_icon="🥗",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Custom CSS (No changes here) ---
st.markdown("""
<style>
    /* Modern, clean font */
    html, body, [class*="st-"], [class*="css-"] {
        font-family: 'Inter', sans-serif;
    }
    /* Main app background */
    .stApp {
        background-color: #0E1117;
    }
    /* Hide Streamlit's default header and footer */
    header, footer {
        visibility: hidden;
    }
    /* Custom class for justification text in plan cards */
    .justification-text {
        font-size: 0.9rem;
        font-style: italic;
        color: #B0B3B8;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. SESSION STATE INITIALIZATION ---
# All session state variables should be initialized at the very top.
if 'user_id' not in st.session_state: st.session_state.user_id = str(uuid.uuid4())
if 'planner' not in st.session_state:
    try:
        st.session_state.planner = MealPlanner()
    except Exception as e:
        st.error(f"Initialization Failed: {e}. Please ensure your .env file is correct.")
        st.stop()
if "messages" not in st.session_state: st.session_state.messages = []
if "user_profile" not in st.session_state: st.session_state.user_profile = UserProfile()
if 'profile_loaded' not in st.session_state: st.session_state.profile_loaded = False
if "last_response" not in st.session_state: st.session_state.last_response = None
if 'needs_update' not in st.session_state: st.session_state.needs_update = False
if 'editing_profile' not in st.session_state: st.session_state.editing_profile = False # --- NEW ---

# --- 2. HELPER FUNCTIONS ---
# All helper functions are defined next. They don't execute until called.

# --- UI RENDERING HELPERS ---
def render_meal_plan(plan_data):
    user_language = st.session_state.user_profile.language
    
    english_greeting = plan_data.get('greeting', 'Here is your plan! 🍳')
    # translated_greeting = translate_text(english_greeting, user_language)
    translated_greeting = translate_text.invoke({
    "text_to_translate": english_greeting, 
    "target_language": user_language
})
    st.markdown(f"#### {translated_greeting}")
    
    plan_items = plan_data.get("plan", [])
    if plan_items:
        cols = st.columns(len(plan_items) if len(plan_items) <= 3 else 3)
        for i, item in enumerate(plan_items):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**{item.get('meal_time', '')}**")
                    st.markdown(f"##### {item.get('meal_name', '...')}")
                    
                    justification_en = item.get('justification', '')
                    # justification_translated = translate_text(justification_en, user_language)
                    justification_translated = translate_text.invoke({
                        "text_to_translate": justification_en, 
                        "target_language": user_language
                    })
                    st.markdown(f"<p class='justification-text'>✨ {justification_translated}</p>", unsafe_allow_html=True)
                    
                    # view_details_text = translate_text("View Details 🍲", user_language)
                    view_details_text = translate_text.invoke({
                        "text_to_translate": "View Details 🍲",
                        "target_language": user_language
                    })
                    if st.button(view_details_text, key=f"view_{item.get('meal_name', i).replace(' ', '_')}"):
                        show_item_dialog(item.get('meal_name'))
        st.divider()
        
        summary_en = plan_data.get('summary', 'Enjoy your meals!')
        # summary_translated = translate_text(summary_en, user_language)
        summary_translated = translate_text.invoke({
            "text_to_translate": summary_en,
            "target_language": user_language
        })

        st.success(f"**Plan Summary:** {summary_translated}")

        simple_plan = {item['meal_time']: item['meal_name'] for item in plan_items}
        # save_plan_text = translate_text("💾 Save This Plan", user_language)
        save_plan_text = translate_text.invoke({
            "text_to_translate": "💾 Save This Plan",
            "target_language": user_language
        })
        if st.button(save_plan_text, use_container_width=True, type="primary"):
            plan_name = f"Plan - {datetime.now().strftime('%b %d, %Y')}"
            db_instance.save_meal_plan(st.session_state.user_id, plan_name, simple_plan)
            st.toast("Plan saved!", icon="✅")

def render_item_details(item_data):
    st.subheader(f"✅ From my cookbook: **{item_data.get('item_name')}**")
    with st.container(border=True):
        show_item_dialog_content(item_data)
        if st.button("❤️ Add to My Favorites", key=f"fav_{item_data.get('item_name')}"):
            db_instance.save_favorite_item(st.session_state.user_id, item_data.get('item_name'), item_data)
            st.toast(f"'{item_data.get('item_name')}' saved to favorites!", icon="✅")
            st.rerun()

def render_web_recipe(item_data):
    st.subheader(f"🌐 Found on the web: **{item_data.get('item_name')}**")
    with st.container(border=True):
        st.markdown(item_data.get('summary', 'No summary available.'))
        yt_link = item_data.get('youtube_link')
        if yt_link and "youtube.com" in yt_link:
            st.video(yt_link)
        else:
            st.info("I couldn't find a suitable YouTube video for this recipe.")

def show_item_dialog_content(item):
    st.subheader(item.get('item_name', 'N/A'))
    if item.get('item_type', 'recipe') != 'recipe':
        st.info(item.get('nutritional_info_brief', 'No details available.'))
    else:
        col1, col2 = st.columns(2)
        col1.metric("Prep Time", item.get('preparation_time', 'N/A'))
        col2.metric("Cook Time", item.get('cooking_time', 'N/A'))
        st.caption(f"Cuisine: {item.get('cuisine_type', 'N/A')}")
        st.divider()
        st.markdown("#### Ingredients")
        ingredients = item.get('ingredients', [])
        if ingredients and isinstance(ingredients[0], list) and len(ingredients[0]) == 2:
            for ingredient, quantity in ingredients:
                st.markdown(f"- {ingredient} ({quantity})")
        st.divider()
        st.markdown("#### Preparation Steps")
        for i, step in enumerate(item.get('preparation_steps', [])):
            st.markdown(f"{i+1}. {step}")

@st.dialog("🍲 Item Details")
def show_item_dialog(item_name):
    item = db_instance.recipes_collection.find_one({"item_name": item_name}, {"_id": 0})
    if item:
        show_item_dialog_content(item)
    else:
        st.error(f"Could not retrieve details for {item_name}.")

# --- DATA LOADING & STATE MANAGEMENT HELPERS ---
def load_profile_from_db():
    profile_data = db_instance.get_user_profile(st.session_state.user_id)
    if profile_data:
        p = st.session_state.user_profile
        for key, value in profile_data.items():
            if key != '_id': setattr(p, key, value)
        if not hasattr(p, 'language') or not p.language:
            p.language = "English"
        p.calculate_metrics()
        st.session_state.needs_update = db_instance.check_needs_weight_update(st.session_state.user_id)
        return True
    return False




# --- 3. INITIAL DATA LOAD & PRE-UI LOGIC ---
# This block runs on every script rerun, ensuring data is fresh before drawing the UI.
if not st.session_state.profile_loaded:
    st.session_state.profile_loaded = load_profile_from_db()

# --- 4. DEFINE THE UI (SIDEBAR & MAIN PAGE) ---

# --- SIDEBAR UI ---
with st.sidebar:
    st.title("Swasth AI 🥗")
    st.markdown("Your Personal Food Buddy")
    
    if st.session_state.user_profile.is_complete() and not st.session_state.editing_profile:
        st.divider()
        st.header("✅ Your Profile")
        p = st.session_state.user_profile
        st.metric("Daily Calorie Target", f"~{int(p.daily_calories)} kcal")
        col1, col2 = st.columns(2)
        col1.metric("BMI", f"{p.bmi:.1f}")
        col2.metric("BMR", int(p.bmr))
        
        if st.button("✏️ Edit Full Profile"):
            st.session_state.editing_profile = True
            st.rerun()
    
    # st.divider()
    # saved_plans = db_instance.get_saved_plans(st.session_state.user_id)
    # if saved_plans:
    #     with st.expander("💾 My Saved Plans"):
    #         for plan_doc in saved_plans:
    #             st.write(f"**{plan_doc['name']}**")
    #             st.json(plan_doc['plan'])
    
    # favorites = db_instance.get_favorite_items(st.session_state.user_id)
    # if favorites:
    #     with st.expander("❤️ My Favorite Recipes", expanded=True):
    #         for fav in favorites:
    #             if st.button(fav['item_name'], key=f"show_fav_{fav['item_name']}", use_container_width=True):
    #                 st.session_state.last_response = {"type": "item_details", "data": fav['item_data']}
    #                 st.rerun()

# --- MAIN PAGE UI ---
# --- MODIFIED: Main logic now checks for editing_profile state ---
if not st.session_state.user_profile.is_complete() or st.session_state.editing_profile:
    # --- ONBOARDING / EDITING FORM ---
    st.title("Welcome! Let's set up your profile. 👋")
    p = st.session_state.user_profile

    with st.form("profile_form"):
        st.header("Tell me a little about yourself!")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Your Age", 10, 100, p.age or 25)
            weight = st.number_input("Your Weight (kg)", 30.0, 200.0, p.weight_kg or 60.0, 0.5)
        with col2:
            genders = ["Female", "Male"]
            gender = st.selectbox("Your Gender", genders, index=genders.index(p.gender) if p.gender in genders else 0)
            height = st.number_input("Your Height (cm)", 100.0, 250.0, p.height_cm or 165.0, 0.5)
        
        activities = ["Sedentary (office job)", "Lightly Active (walking 1-3 days/wk)", "Moderately Active (exercise 3-5 days/wk)", "Very Active (intense exercise 6-7 days/wk)"]
        activity = st.select_slider("Your Daily Activity Level", options=activities, value=p.activity_level or activities[1])
        goals = ["Lose Weight", "Maintain Weight", "Gain Muscle"]
        goal = st.selectbox("Your Primary Goal", goals, index=goals.index(p.goal) if p.goal in goals else 0)
        
        st.divider()
        st.header("Your Preferences")
        diet_options = ["Vegetarian", "Non-Vegetarian", "Any"]
        diet_preference = st.selectbox("Your Dietary Preference", diet_options, index=diet_options.index(p.diet_preference) if p.diet_preference in diet_options else 2)
        regions = ["North Indian", "South Indian", "East Indian", "West Indian", "Any"]
        region = st.selectbox("Which region's cuisine do you prefer?", regions, index=regions.index(p.region) if p.region in regions else 4)
        allergies = st.multiselect("Do you have any allergies?", options=["Peanuts", "Dairy", "Gluten", "Shellfish", "Soy", "Tree Nuts"], default=p.allergies)
        languages = ["English", "Hindi", "Spanish", "French"] # Add more languages as needed
        language = st.selectbox("Preferred App Language", languages, index=languages.index(p.language) if p.language in languages else 0)

        if st.form_submit_button("✨ Save Profile & Start Planning ✨", use_container_width=True, type="primary"):
            profile_data = {
                "age": age, "gender": gender, "weight_kg": weight, "height_cm": height, 
                "activity_level": activity, "goal": goal, "region": region, 
                "allergies": allergies, "diet_preference": diet_preference, "language": language
            }
            db_instance.save_user_profile(st.session_state.user_id, profile_data)
            st.session_state.editing_profile = False
            st.session_state.profile_loaded = False
            st.toast("Profile saved successfully!", icon="🎉")
            st.rerun()
else:
    # --- MAIN DASHBOARD UI ---
    if st.session_state.needs_update:
        st.warning("🗓️ It's been over 15 days! Please update your weight to keep your recommendations accurate.")
        with st.form("weight_update_form"):
            new_weight = st.number_input("Your Current Weight (kg)", 30.0, 200.0, st.session_state.user_profile.weight_kg, 0.5)
            if st.form_submit_button("Update My Weight"):
                profile_data = db_instance.get_user_profile(st.session_state.user_id)
                profile_data['weight_kg'] = new_weight
                db_instance.save_user_profile(st.session_state.user_id, profile_data)
                st.session_state.profile_loaded = False
                st.toast("Weight updated!", icon="💪")
                st.rerun()

    st.title("🥗 Your Daily Food Adventure!")
    
    if st.session_state.last_response:
        response_dict = st.session_state.last_response
        if response_dict.get("type") == "plan":
            render_meal_plan(response_dict.get("data", {}))
        elif response_dict.get("type") == "item_details":
            render_item_details(response_dict.get("data", {}))
        elif response_dict.get("type") == "web_recipe":
            render_web_recipe(response_dict.get("data", {}))
    
    st.markdown("---")
    
    # The Chat Interface
    user_language = st.session_state.user_profile.language
    if not st.session_state.messages:
        initial_greeting = "What's our first food mission today? Ask for a plan or about a specific food!"
        # translated_greeting = translate_text(initial_greeting, user_language)
        translated_greeting = translate_text.invoke({
    "text_to_translate": initial_greeting,
    "target_language": user_language
})
        st.session_state.messages.append({"role": "assistant", "content": translated_greeting})

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask for a plan, or a specific food..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Your food buddy is thinking... 🤓"):
                response_dict = st.session_state.planner.get_response(prompt, st.session_state.user_profile)
                st.session_state.last_response = response_dict
                
                response_type = response_dict.get("type")
                if response_type == "plan":
                    english_chat_text = response_dict["data"].get("greeting", "I've created a plan for you!")
                elif response_type == "item_details":
                    english_chat_text = f"You got it! I've pulled up the details for **{response_dict['data'].get('item_name')}**."
                elif response_type == "web_recipe":
                    english_chat_text = f"I couldn't find that in my cookbook, but I found this for you on the web: **{response_dict['data'].get('item_name')}**."
                else:
                    english_chat_text = response_dict.get("data", "Something went wrong.")
                
                # chat_text = translate_text(english_chat_text, user_language)
                chat_text = translate_text.invoke({
                    "text_to_translate": english_chat_text,
                    "target_language": user_language
                })
                
                st.markdown(chat_text)
                st.session_state.messages.append({"role": "assistant", "content": chat_text})
                st.rerun()