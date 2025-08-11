class UserProfile:
    """
    A class to store and manage a user's profile data and health metrics.
    """
    def __init__(self):
        # --- MODIFIED: Added diet_preference and language ---
        self.age, self.gender, self.weight_kg, self.height_cm, self.activity_level, self.goal, self.region = [None] * 7
        self.diet_preference = None
        self.language = "English" # Default language
        self.allergies = []
        self.bmi, self.bmr, self.daily_calories = [None] * 3

    def is_complete(self):
        """Checks if all essential profile information has been gathered."""
        # --- MODIFIED: Added diet_preference to the check ---
        return all([self.age, self.gender, self.weight_kg, self.height_cm, self.activity_level, self.goal, self.region, self.diet_preference])

    def calculate_metrics(self):
        """Calculates BMI, BMR, and Daily Calorie needs based on the profile."""
        if not self.is_complete(): return

        height_m = self.height_cm / 100
        self.bmi = round(self.weight_kg / (height_m ** 2), 2)
        
        if self.gender.lower() == 'male':
            self.bmr = (10 * self.weight_kg) + (6.25 * self.height_cm) - (5 * self.age) + 5
        else:
            self.bmr = (10 * self.weight_kg) + (6.25 * self.height_cm) - (5 * self.age) - 161
        
        activity_multipliers = {
            "sedentary (office job)": 1.2,
            "lightly active (walking 1-3 days/wk)": 1.375,
            "moderately active (exercise 3-5 days/wk)": 1.55,
            "very active (intense exercise 6-7 days/wk)": 1.725
        }
        multiplier = activity_multipliers.get(self.activity_level.lower(), 1.2)
        tdee = self.bmr * multiplier

        if self.goal.lower() == 'lose weight': self.daily_calories = round(tdee - 500)
        elif self.goal.lower() == 'gain muscle': self.daily_calories = round(tdee + 300)
        else: self.daily_calories = round(tdee)
            
    def get_summary(self):
        """Returns a user-friendly, formatted summary of the profile for display."""
        if not self.is_complete(): return "Profile not set."
        
        if self.bmi < 18.5: bmi_category = "Underweight"
        elif 18.5 <= self.bmi < 24.9: bmi_category = "Normal"
        elif 25 <= self.bmi < 29.9: bmi_category = "Overweight"
        else: bmi_category = "Obesity"

        # --- MODIFIED: Added preferences to the summary for better AI context ---
        summary = (
            f"**Goal:** {self.goal}\n"
            f"**Dietary Preference:** {self.diet_preference}\n"
            f"**Preferred Cuisine:** {self.region}\n\n"
            f"**Target:** ~{int(self.daily_calories)} kcal\n"
            f"**BMI:** {self.bmi} ({bmi_category})"
        )
        if self.allergies:
            summary += f"\n\n**⚠️ Allergies:** {', '.join(self.allergies)}"
        
        return summary