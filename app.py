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

# Initialize Session States
if "inventory" not in st.session_state:
    st.session_state.inventory = []

if "macros" not in st.session_state:
    st.session_state.macros = []

if "resetDate" not in st.session_state:
    st.session_state["resetDate"] = datetime.date.today()

if st.session_state["resetDate"] < datetime.date.today():
    st.session_state["macros"] = []
    st.session_state["resetDate"] = datetime.date.today()


# Helper function to initialize Gemini API Client
def get_gemini_client():
    apikey = os.environ.get("geminiApiKey") or os.environ.get("GEMINI_API_KEY")
    if not apikey:
        return None
    return genai.Client(api_key=apikey)


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


# Calculate Calorie & Macro Requirements using Mifflin-St Jeor Formula
def calculate_goals(age, weight_lbs, height_inches, gender, activity, goal):
    weight_kg = weight_lbs * 0.453592
    height_cm = height_inches * 2.54

    # Base BMR
    if gender == "Male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    # Activity Multiplier
    act_mult = {
        "Sedentary": 1.2,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725,
    }
    tdee = bmr * act_mult.get(activity, 1.2)

    # Goal Adjustment
    if goal == "Lose Weight":
        calories = tdee - 500
    elif goal == "Gain Muscle":
        calories = tdee + 300
    else:
        calories = tdee

    # Macro distribution: ~30% Protein, 40% Carbs, 30% Fat
    protein_g = (calories * 0.30) / 4
    carbs_g = (calories * 0.40) / 4
    fat_g = (calories * 0.30) / 9

    return {
        "calories": max(1200, int(calories)),
        "protein": max(50, int(protein_g)),
        "carbs": max(50, int(carbs_g)),
        "fat": max(30, int(fat_g)),
    }


# ================= SIDEBAR =================
st.sidebar.title("⚙️ Settings & User Profile")

# Sidebar - User Health Profile & Calculated Targets
st.sidebar.header("👤 Your Profile & Goals")
age = st.sidebar.number_input("Age", min_value=10, max_value=120, value=25)
gender = st.sidebar.selectbox("Gender", ["Male", "Female"])
height_inches = st.sidebar.number_input("Height (inches)", min_value=36, max_value=96, value=68)
weight_lbs = st.sidebar.number_input("Current Weight (lbs)", min_value=50, max_value=500, value=150)
goal_weight = st.sidebar.number_input("Goal Weight (lbs)", min_value=50, max_value=500, value=140)
activity = st.sidebar.selectbox(
    "Activity Level", ["Sedentary", "Lightly Active", "Moderately Active", "Very Active"]
)

if goal_weight < weight_lbs:
    goal_type = "Lose Weight"
elif goal_weight > weight_lbs:
    goal_type = "Gain Muscle"
else:
    goal_type = "Maintain Weight"

calculated_goals = calculate_goals(age, weight_lbs, height_inches, gender, activity, goal_type)

st.sidebar.markdown(f"**Target Plan:** {goal_type}")

# Macro Limits Customization
st.sidebar.header("🎯 Daily Nutrition Targets")
carbstracker = st.sidebar.checkbox("Track Carbohydrates?", value=True)
carbslimit = st.sidebar.number_input(
    "Carb Limit (g)", min_value=1, value=calculated_goals["carbs"]
) if carbstracker else 0

proteintracker = st.sidebar.checkbox("Track Protein?", value=True)
proteingoal = st.sidebar.number_input(
    "Protein Goal (g)", min_value=1, value=calculated_goals["protein"]
) if proteintracker else 0

fattracker = st.sidebar.checkbox("Track Fat?", value=True)
fatlimit = st.sidebar.number_input(
    "Fat Limit (g)", min_value=1, value=calculated_goals["fat"]
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
        st.session_state["inventory"].append(scannedBC)
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
        st.session_state["inventory"].append(addItem)
        st.sidebar.success(f"Added {handName} successfully!")
        st.rerun()


# ================= MAIN PAGE UI =================
st.title("🥗 FreshPulse")
st.write("Keep Track of Your Food to Help Stop Grocery Waste!")

tab1, tab2 = st.tabs(["📊 Inventory & Dashboard", "🍳 AI Recipes & Health Suggestions"])

# ---------------- TAB 1: DASHBOARD & INVENTORY ----------------
with tab1:
    eatenCarbs = sum(item.get("Carbs", 0) for item in st.session_state["macros"])
    eatenProtein = sum(item.get("Protein", 0) for item in st.session_state["macros"])
    eatenFat = sum(item.get("Fat", 0) for item in st.session_state["macros"])
    eatenSodium = sum(item.get("Sodium", 0) for item in st.session_state["macros"])

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
            st.session_state["inventory"].append(
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

    if len(st.session_state["inventory"]) < 1:
        st.info("No items in your inventory. Add items using the sidebar or upload a receipt!")
    else:
        for index, item in enumerate(st.session_state["inventory"]):
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
                    if st.session_state["resetDate"] < datetime.date.today():
                        st.session_state["macros"] = []
                        st.session_state["resetDate"] = datetime.date.today()
                    eaten = st.session_state["inventory"].pop(index)
                    st.session_state["macros"].append(eaten)
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
            recipe_output = generate_recipes(st.session_state["inventory"], user_goals)
            st.markdown(recipe_output)

st.divider()
st.caption("Created By Sai Belde and Aarnav Vurputoor")
