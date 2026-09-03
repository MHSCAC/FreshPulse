import datetime
import json
import math
import os
import random
import requests
from google import genai
from google.genai import types
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

# Prevent Accidental Refreshes and Alert User
components.html(
    """
    <script>
    window.addEventListener('beforeunload', function (e) {
        e.preventDefault();
        e.returnValue = '';
    });
    </script>
    """,
    height=0,
)

# ================= SESSION STATE & SIGN-IN MANAGEMENT =================

# Store mock user accounts database in session state
if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "guest": {
            "password": "guest",
            "profile": {
                "age": 25,
                "gender": "Male",
                "height_inches": 68,
                "weight_lbs": 160,
                "goal_weight": 150,
                "activity": "Moderately Active",
            },
            "inventory": [],
            "macros": [],
            "resetDate": datetime.date.today(),
        }
    }

if "current_user" not in st.session_state:
    st.session_state.current_user = None


# Helper function to initialize Gemini API Client
def get_gemini_client():
    apikey = os.environ.get("geminiApiKey") or os.environ.get("GEMINI_API_KEY")
    if not apikey:
        return None
    return genai.Client(api_key=apikey)


# Calculate Realistic Calorie & Macro Requirements
def calculate_goals(age, weight_lbs, height_inches, gender, activity, goal):
    weight_kg = weight_lbs * 0.453592
    height_cm = height_inches * 2.54

    # BMR Calculation (Mifflin-St Jeor)
    if gender == "Male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    # Activity Multipliers
    act_mult = {
        "Sedentary": 1.2,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725,
    }
    tdee = bmr * act_mult.get(activity, 1.2)

    # Calorie Adjustment Based on Goal
    if goal == "Lose Weight":
        calories = max(1200, tdee - 500)
    elif goal == "Gain Muscle":
        calories = tdee + 300
    else:
        calories = tdee

    # REALISTIC MACRO CALCULATIONS:
    # 1. Protein based on weight: 0.8g to 1.0g per lb of body weight (Capped between 60g and 180g)
    if goal == "Gain Muscle":
        protein_g = min(180, max(60, weight_lbs * 1.0))
    else:
        protein_g = min(160, max(50, weight_lbs * 0.8))

    # 2. Dietary Fat: ~25% to 30% of total daily calories (0.3g to 0.4g per lb)
    fat_g = max(40, (calories * 0.25) / 9)

    # 3. Carbohydrates: Fills remaining daily calorie allowance
    protein_calories = protein_g * 4
    fat_calories = fat_g * 9
    remaining_calories = max(0, calories - (protein_calories + fat_calories))
    carbs_g = max(50, remaining_calories / 4)

    return {
        "calories": int(calories),
        "protein": int(protein_g),
        "carbs": int(carbs_g),
        "fat": int(fat_g),
    }


# Macro Progress Ring SVG Helper
def create_ring_svg(label, current, goal, unit, color):
    percent = min(100, int((current / goal) * 100)) if goal > 0 else 0
    dashoffset = 226 - (226 * percent / 100)

    return f"""
    <div style="text-align: center; margin: 10px;">
        <svg width="100" height="100" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="36" stroke="#e6e6e6" stroke-width="8" fill="none"/>
            <circle cx="50" cy="50" r="36" stroke="{color}" stroke-width="8" fill="none"
                    stroke-dasharray="226" stroke-dashoffset="{dashoffset}"
                    stroke-linecap="round" transform="rotate(-90 50 50)"/>
            <text x="50%" y="45%" text-anchor="middle" font-size="14px" font-weight="bold" fill="#333">{percent}%</text>
            <text x="50%" y="62%" text-anchor="middle" font-size="9px" fill="#666">{int(current)}{unit}</text>
        </svg>
        <div style="font-weight: bold; font-size: 14px; margin-top: 2px;">{label}</div>
        <div style="font-size: 11px; color: #777;">Goal: {goal}{unit}</div>
    </div>
    """


# AI Receipt Processing
def aircpt(image):
    client = get_gemini_client()
    if not client:
        st.error("Missing Gemini API key! Please configure geminiApiKey environment variable.")
        return []

    aiprompt = (
        "Analyze this grocery receipt image. Extract all food items, considering brand names when available. "
        "For each item, estimate/extract the following: "
        "item name, emoji, shelf life in days (integer), and calories per standard serving (number). "
        "Provide nutrition values PER ONE STANDARD SERVING of that item, choosing the serving unit that fits the food type: "
        "for solid foods use one typical portion or 100 grams; "
        "for liquids (milk, juice, soda, etc.) use 1 cup (240 mL); "
        "for countable items (eggs, bananas, sausage links, slices of bread) use 1 piece/unit. "
        "For that one serving, give: calories (number), carbohydrates in grams (number), protein in grams (number), "
        "fat in grams (number), and sodium in milligrams (number). "
        "Also include a short 'serving' description of the serving size you assumed (for example '1 link', '1 cup', '100g', '1 egg'). "
        "Return ONLY a JSON list where each item has these keys: "
        "'name', 'emoji', 'life', 'serving', 'calories', 'carbs', 'protein', 'fat', 'sodium'."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[aiprompt, image],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        cleanText = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleanText)
    except Exception as e:
        st.error(f"Error Processing Receipt: {e}")
        return []


# AI Barcode & Nutritional Info Extraction
def barcode_ai(image):
    client = get_gemini_client()
    if not client:
        st.sidebar.error("Missing Gemini API Key.")
        return None

    bcprompt = (
        "Look at this product image or barcode photo. Identify the exact food item and brand. "
        "Extract/estimate its nutritional content and shelf life details. "
        "Return ONLY a JSON object with the following keys: "
        "'name' (string), 'emoji' (string emoji), 'serving' (string e.g. '1 container'), "
        "'life' (integer shelf life in days), 'calories' (number per serving), "
        "'carbs' (grams per serving number), 'protein' (grams per serving number), "
        "'fat' (grams per serving number), 'sodium' (milligrams per serving number)."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[bcprompt, image],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        cleanText = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleanText)

        return {
            "Name": data.get("name", "Scanned Item"),
            "Emoji": data.get("emoji", "📦"),
            "Serving": data.get("serving", "1 serving"),
            "Date Added": datetime.date.today(),
            "Expires": datetime.date.today() + datetime.timedelta(days=int(data.get("life", 7))),
            "Calories": float(data.get("calories", 0)),
            "Carbs": float(data.get("carbs", 0)),
            "Protein": float(data.get("protein", 0)),
            "Fat": float(data.get("fat", 0)),
            "Sodium": float(data.get("sodium", 0)),
        }
    except Exception as e:
        st.sidebar.error(f"Error scanning barcode: {e}")
        return None


# AI Recipe Generator
def generate_recipes(inventory, user_macro_goals):
    client = get_gemini_client()
    if not client:
        st.error("Missing Gemini API Key.")
        return ""

    if not inventory:
        return "Your inventory is currently empty! Add items to generate recipe suggestions."

    items_list = [item["Name"] for item in inventory]

    recipe_prompt = f"""
    You are an expert culinary AI nutritionist.
    The user currently has these food items in their inventory: {', '.join(items_list)}.

    User's Daily Targets:
    - Target Calories: {user_macro_goals.get('calories', 'N/A')} kcal
    - Target Protein: {user_macro_goals.get('protein', 'N/A')} g
    - Target Carbs: {user_macro_goals.get('carbs', 'N/A')} g
    - Target Fat: {user_macro_goals.get('fat', 'N/A')} g

    Task:
    1. Provide 2-3 recipes that can be fully or almost fully made using the user's available ingredients.
    2. Indicate missing ingredients if any.
    3. For each recipe, provide estimated nutritional facts (Calories, Carbs, Protein, Fat).
    4. Provide a 'Health Impact' section for each recipe explaining how it helps or impacts their daily health goals.
    Format your response neatly in Markdown.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=recipe_prompt,
        )
        return response.text
    except Exception as e:
        return f"Error generating recipes: {e}"


# ================= SIGN-IN SCREEN =================
if not st.session_state.current_user:
    st.title("🥗 FreshPulse - Sign In")

    auth_mode = st.radio("Choose Action", ["Sign In", "Register New Account"])

    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")

    if auth_mode == "Sign In":
        if st.button("Log In"):
            user_data = st.session_state.users_db.get(username_input)
            if user_data and user_data["password"] == password_input:
                st.session_state.current_user = username_input
                st.success(f"Welcome back, {username_input}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
    else:
        if st.button("Create Account"):
            if username_input in st.session_state.users_db:
                st.error("Username already exists!")
            elif username_input and password_input:
                st.session_state.users_db[username_input] = {
                    "password": password_input,
                    "profile": {
                        "age": 25,
                        "gender": "Male",
                        "height_inches": 68,
                        "weight_lbs": 160,
                        "goal_weight": 150,
                        "activity": "Moderately Active",
                    },
                    "inventory": [],
                    "macros": [],
                    "resetDate": datetime.date.today(),
                }
                st.session_state.current_user = username_input
                st.success("Account created successfully!")
                st.rerun()
            else:
                st.error("Please enter both a username and password.")

    st.stop()

# Sync user data to session state
user = st.session_state.current_user
user_data = st.session_state.users_db[user]
user_prof = user_data["profile"]

if user_data["resetDate"] < datetime.date.today():
    user_data["macros"] = []
    user_data["resetDate"] = datetime.date.today()

# ================= SIDEBAR =================
st.sidebar.title(f"⚙️ Profile ({user})")
if st.sidebar.button("🚪 Log Out"):
    st.session_state.current_user = None
    st.rerun()

# Client-Side Form: User Information
st.sidebar.header("👤 Body & Goal Profile")

with st.sidebar.form("profile_form"):
    st.write("Fill out your stats and save to send to server:")
    age_input = st.number_input("Age", min_value=10, max_value=120, value=int(user_prof["age"]))
    gender_input = st.selectbox("Gender", ["Male", "Female"], index=0 if user_prof["gender"] == "Male" else 1)
    height_input = st.number_input("Height (inches)", min_value=36, max_value=96, value=int(user_prof["height_inches"]))
    weight_input = st.number_input("Current Weight (lbs)", min_value=50, max_value=500, value=int(user_prof["weight_lbs"]))
    goal_weight_input = st.number_input("Goal Weight (lbs)", min_value=50, max_value=500, value=int(user_prof["goal_weight"]))

    activity_options = ["Sedentary", "Lightly Active", "Moderately Active", "Very Active"]
    activity_input = st.selectbox(
        "Activity Level",
        activity_options,
        index=activity_options.index(user_prof.get("activity", "Moderately Active"))
    )

    profile_submitted = st.form_submit_button("💾 Save Profile & Update Goals")

if profile_submitted:
    user_prof.update({
        "age": age_input,
        "gender": gender_input,
        "height_inches": height_input,
        "weight_lbs": weight_input,
        "goal_weight": goal_weight_input,
        "activity": activity_input,
    })
    st.sidebar.success("Profile saved and server goals updated!")
    st.rerun()

# Determine goal type & dynamically compute realistic targets based on saved profile
if user_prof["goal_weight"] < user_prof["weight_lbs"]:
    goal_type = "Lose Weight"
elif user_prof["goal_weight"] > user_prof["weight_lbs"]:
    goal_type = "Gain Muscle"
else:
    goal_type = "Maintain Weight"

calculated_goals = calculate_goals(
    user_prof["age"],
    user_prof["weight_lbs"],
    user_prof["height_inches"],
    user_prof["gender"],
    user_prof["activity"],
    goal_type
)

st.sidebar.markdown(f"**Target Plan:** `{goal_type}`")
st.sidebar.markdown(f"**Target Calories:** `{calculated_goals['calories']} kcal`")

# Macro Limits Customization
st.sidebar.header("🎯 Active Macro Targets")
carbstracker = st.sidebar.checkbox("Track Carbohydrates?", value=True)
carbslimit = st.sidebar.number_input(
    "Carb Target (g)", min_value=1, value=calculated_goals["carbs"]
) if carbstracker else 0

proteintracker = st.sidebar.checkbox("Track Protein?", value=True)
proteingoal = st.sidebar.number_input(
    "Protein Target (g)", min_value=1, value=calculated_goals["protein"]
) if proteintracker else 0

fattracker = st.sidebar.checkbox("Track Fat?", value=True)
fatlimit = st.sidebar.number_input(
    "Fat Target (g)", min_value=1, value=calculated_goals["fat"]
) if fattracker else 0

sodiumtracker = st.sidebar.checkbox("Track Sodium?", value=True)
sodiumlimit = st.sidebar.number_input("Sodium Limit (mg)", min_value=1, value=2300) if sodiumtracker else 0

st.sidebar.divider()

# Sidebar - AI Barcode Scanner
st.sidebar.header("🔍 Scan Product / Barcode")
allowedtypes = {"png", "jpg", "jpeg"}
barcodePicture = st.sidebar.file_uploader("Upload Product or Barcode Image:", type=allowedtypes, key="barcode_uploader")

if barcodePicture and st.sidebar.button("Process Product Photo"):
    barcodeImg = Image.open(barcodePicture)
    with st.spinner("AI is determining product & nutrition info..."):
        scannedBC = barcode_ai(barcodeImg)

    if scannedBC:
        user_data["inventory"].append(scannedBC)
        st.sidebar.success(f"Added {scannedBC['Name']}")
        st.rerun()

st.sidebar.divider()

# Sidebar - Manual Entry
st.sidebar.header("➕ Add Item Manually")
handName = st.sidebar.text_input("Item Name:")
handEmoji = st.sidebar.text_input("Emoji", value="🍽️")
handDays = st.sidebar.number_input("Shelf Life (days):", min_value=1, value=7)
handCals = st.sidebar.number_input("Calories (kcal):", min_value=0, value=100)
handCarbs = st.sidebar.number_input("Carbs (g):", min_value=0, value=10)
handProtein = st.sidebar.number_input("Protein (g):", min_value=0, value=5)
handFat = st.sidebar.number_input("Fat (g):", min_value=0, value=2)

if st.sidebar.button("Add Item Manually"):
    if handName and handDays:
        addItem = {
            "Name": handName,
            "Emoji": handEmoji,
            "Date Added": datetime.date.today(),
            "Expires": datetime.date.today() + datetime.timedelta(days=handDays),
            "Calories": float(handCals),
            "Carbs": float(handCarbs),
            "Protein": float(handProtein),
            "Fat": float(handFat),
            "Sodium": 0.0,
            "Serving": "1 serving",
        }
        user_data["inventory"].append(addItem)
        st.sidebar.success(f"Added {handName} successfully!")
        st.rerun()


# ================= MAIN PAGE UI =================
st.title("🥗 FreshPulse")
st.write(f"Logged in as **{user}** | Track inventory and manage health goals.")

tab1, tab2 = st.tabs(["📊 Inventory & Dashboard", "🍳 AI Recipes & Health Suggestions"])

# ---------------- TAB 1: DASHBOARD & INVENTORY ----------------
with tab1:
    eatenCarbs = sum(item.get("Carbs", 0) for item in user_data["macros"])
    eatenProtein = sum(item.get("Protein", 0) for item in user_data["macros"])
    eatenFat = sum(item.get("Fat", 0) for item in user_data["macros"])
    eatenSodium = sum(item.get("Sodium", 0) for item in user_data["macros"])

    st.markdown("### 🎯 Your Daily Nutrition Progress")

    cols = st.columns(4)
    active_idx = 0

    if carbstracker and active_idx < 4:
        with cols[active_idx]:
            st.markdown(create_ring_svg("Carbs", eatenCarbs, carbslimit, "g", "#FF4B4B"), unsafe_allow_html=True)
        active_idx += 1

    if proteintracker and active_idx < 4:
        with cols[active_idx]:
            st.markdown(create_ring_svg("Protein", eatenProtein, proteingoal, "g", "#00C04D"), unsafe_allow_html=True)
        active_idx += 1

    if fattracker and active_idx < 4:
        with cols[active_idx]:
            st.markdown(create_ring_svg("Fat", eatenFat, fatlimit, "g", "#FFA500"), unsafe_allow_html=True)
        active_idx += 1

    if sodiumtracker and active_idx < 4:
        with cols[active_idx]:
            st.markdown(create_ring_svg("Sodium", eatenSodium, sodiumlimit, "mg", "#29B6F6"), unsafe_allow_html=True)
        active_idx += 1

    st.divider()

    st.subheader("🧾 Upload Receipt to Scan Multiple Items")
    fileUpload = st.file_uploader("Upload Grocery Receipt:", type=allowedtypes)
    analyzeBtn = st.button("🔍 Analyze Receipt with AI")

    if fileUpload and analyzeBtn:
        img = Image.open(fileUpload).convert("RGB")
        with st.spinner("AI Is Processing Your Image..."):
            prcsdItems = aircpt(img)
        for item in prcsdItems:
            life = int(item.get("life", 6))
            user_data["inventory"].append(
                {
                    "Name": item.get("name", "Unknown"),
                    "Emoji": item.get("emoji", "🍽️"),
                    "Serving": item.get("serving", "1 serving"),
                    "Date Added": datetime.date.today(),
                    "Expires": datetime.date.today() + datetime.timedelta(days=life),
                    "Calories": float(item.get("calories", 0)),
                    "Carbs": float(item.get("carbs", 0)),
                    "Protein": float(item.get("protein", 0)),
                    "Fat": float(item.get("fat", 0)),
                    "Sodium": float(item.get("sodium", 0)),
                }
            )
        st.success("Items Extracted and Saved Successfully!")
        st.rerun()

    st.divider()

    # Grocery Inventory Display
    st.header("🛒 Your Grocery Cart")
    today = datetime.date.today()

    if len(user_data["inventory"]) < 1:
        st.info("No items in your inventory. Add items using the sidebar or upload a receipt!")
    else:
        for index, item in enumerate(user_data["inventory"]):
            remainLife = (item["Expires"] - today).days
            totalLife = (item["Expires"] - item["Date Added"]).days

            warning = max(2, min(5, int(totalLife * 0.25)))
            if remainLife < 1:
                status = "🔴 EXPIRED"
            elif remainLife <= warning:
                status = f"🟡 EXPIRING SOON ({remainLife} Days Left!)"
            else:
                status = f"🟢 Fresh ({remainLife} Days Left)"

            dateFormat = item["Expires"].strftime("%m/%d/%Y")

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"### {item['Emoji']} {item['Name']}")
                st.write(f"Status: **{status}** | Expires On: **{dateFormat}**")
                with st.expander("Nutrition Facts & Details"):
                    st.caption(f"📏 **Serving Size:** {item.get('Serving', '1 serving')}")
                    n_col1, n_col2 = st.columns(2)
                    with n_col1:
                        st.write(f"*Calories:* {item.get('Calories', 0)} kcal")
                        st.write(f"*Carbs:* {item.get('Carbs', 0)}g")
                        st.write(f"*Protein:* {item.get('Protein', 0)}g")
                    with n_col2:
                        st.write(f"*Fat:* {item.get('Fat', 0)}g")
                        st.write(f"*Sodium:* {item.get('Sodium', 0)}mg")

                if 0 < remainLife <= warning:
                    st.warning(f"⚠️ ACTION NEEDED! Use or cook {item['Name']} within {remainLife} days!")

            with col2:
                if st.button("Mark as Eaten", key=f"btn_{index}"):
                    if user_data["resetDate"] < datetime.date.today():
                        user_data["macros"] = []
                        user_data["resetDate"] = datetime.date.today()
                    eaten = user_data["inventory"].pop(index)
                    user_data["macros"].append(eaten)
                    st.rerun()

# ---------------- TAB 2: AI RECIPES & HEALTH ----------------
with tab2:
    st.header("🍳 AI Recipe Generator & Health Analysis")
    st.write("Generate custom recipes based on ingredients currently in your inventory!")

    user_goals = {
        "calories": calculated_goals["calories"],
        "protein": proteingoal,
        "carbs": carbslimit,
        "fat": fatlimit,
    }

    if st.button("✨ Generate Recipes from My Inventory"):
        with st.spinner("Analyzing ingredients and crafting personalized recipes..."):
            recipe_output = generate_recipes(user_data["inventory"], user_goals)
            st.markdown(recipe_output)

st.divider()
st.caption("Created By Sai Belde and Aarnav Vurputoor")
