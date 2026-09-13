
#Section 1:Tools/Packages for web app

#This allows us to import the tools needed for our app, so basically like gen ai from google allows us to use Gemini for image processing, streamlit allows us to build our ferontend using only python, etc."
import math
import random
#Streamlit==st, easier to write st rather that streamlit every time
import streamlit as st
import streamlit.components.v1 as components
#datetime=python tool for tracking dates, in this case, expiration dates
import datetime
import requests
#Allows AI to see and read the uploaded image from the user
from PIL import Image
import json
from google import genai
from google.genai import types #Keep this import line, significance is that wihtout types, data formatting won't work with gemini model
import os


#Notes

#Comments near st.rerun()-This makes the web app re-run and update the page after the user adds an item to their inventory, so they can see the item they just added

#Add advanced API to make processing images and creating recipes faster and easier.





#Prevent Accidental Refreshes and To Alert User

#Did use AI for this part
components.html(
    """
    <script>
    window.addEventListener('beforeunload', function (e) {
        e.preventDefault();
        // Chrome wants returnValue to be set
        e.returnValue = '';
    });
    </script>
    """,
    height=0,
)




#Section 2:Functions-Remember/make sure all function are in this section
#Remember-Only Top Down Orgnization of Code, so all functions are in this section, and all other code is below this section

#API Key Helper Function
#Helper: builds Gemini connection in one place 
def get_gemini_client():
    apikey = os.environ.get("geminiApiKey") or os.environ.get("GEMINI_API_KEY")
    if not apikey:
        return None
    return genai.Client(api_key=apikey)


#Section 2a:AI Proccessed Screenshots/Receipts

#We did use AI to help us to code this part. We have never used API keys or imported AI in a web app before, so we got AI to teach us how to code something like that.
def aircpt(image):
    client = get_gemini_client()#variable is basically a messenger which allows the web app to communicate with google AI
    if not client:
        st.error("Missing geminiApiKey!")
        return []
    #I did ask AI to create the prompt. My wording is kind of messy and confusing, so I told AI what I wanted the prompt to say and then the AI fixed and created the more neat prompt. Also figured that since this prmpt is for AI, then AI should prob creat the prompt
    aiprompt = (
        "Analyze this grocery receipt image. Extract all food items, considering brand names when available. "
        "For each item, estimate/extract the following: "
        "item name, emoji, and shelf life in days (integer). "
        "Provide nutrition values PER ONE STANDARD SERVING of that item, choosing the serving unit that fits the food type: "
        "for solid foods use one typical portion or 100 grams; "
        "for liquids (milk, juice, soda, etc.) use 1 cup (240 mL); "
        "for countable items (eggs, bananas, sausage links, slices of bread) use 1 piece/unit. "
        "For that one serving, give: carbohydrates in grams (number), protein in grams (number), "
        "fat in grams (number), and sodium in milligrams (number). "
        "Also include a short 'serving' description of the serving size you assumed (for example '1 link', '1 cup', '100g', '1 egg'). "
        "Return ONLY a JSON list where each item has these keys: "
        "'name', 'emoji', 'life', 'serving','calories', 'carbs', 'protein', 'fat', 'sodium'."
    )

    #Basically asked AI to give the app the item name, a deisgnated emoji, a lifetime, the carbs, the protein, the fat, and sodium, of each item on the user's receipt
    
    try:
        response = client.models.generate_content(
        model='gemini-3.6-flash', #Cant use 2.5 flash, google retired it for new users
        contents=[aiprompt,image],#This makes the code send the user's image and our prompt to Gemini
config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        #CleanText Function will break if everything is not in one line, adding lines will overide and revert back to the original text given by the AI
        cleanText = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleanText)#This returns and makes the java text that Gemini gives us into python text, so the web app can read and use it.
    except Exception as e:
        st.error(f"Error Processing Receipt:{e}")
        return []

#Section 2b: Rings for Macro Stats-Did use AI for this part, way too complicated for me
def create_ring_svg(label, current, goal, unit, color, goal_label="Goal"):
    percent = min(100, int((current / goal) * 100)) if goal > 0 else 0
    # SVG circle circumference math (r=36 -> C ≈ 226)
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
                <div style="font-size: 11px; color: #777;">{goal_label}: {goal}{unit}</div>

    </div>
    """


#Section 2c: User Barcoede Scanner Function
def barcode(image):
    client = get_gemini_client()
    if not client:
        st.sidebar.error("Missing/Error with API Key")
        return None
    bcprompt=(
        "Look closely at this image to find a barcode (UPC/EAN). "
        "Extract ONLY the raw digits of the barcode as a single string of numbers with no spaces or symbols. "
        "If no barcode is visible, return 'NONE'."
    )
    try:
        response=client.models.generate_content(
        model='gemini-3.6-flash',
        contents=[bcprompt,image] 
    )
        barcodeNum=response.text.strip().replace(" ", "") #Don't need to stip backticks or spaces at front or end, not necessary for this one
        if barcodeNum and barcodeNum.isdigit():
            url=f"https://world.openfoodfacts.org/api/v2/product/{barcodeNum}.json" #Function of this-sends the barcode number that we cleaned from the ai, puts it into an API web that finds stats and macros of the barcode item that you put into it
            calling={"User-Agent": "FreshPulse/1.0"} #When using the Open Food Facts API, the API needs to know who is using it, so we gave them our name "FreshPulse"
            res=requests.get(url,timeout=15, headers=calling).json()
            if (res.get("status")==1): #If it does get the product and it equals 1 or true, then the if statement will run
                product=res.get("product",{})
                nutriments=product.get("nutriments",{})
                name=product.get("product_name") or product.get("product_name_en") or "Scanned Product" #-Both names are missing, defaults to Scanned Product
                brand=product.get("brands", "")
                fullName = f"{brand} {name}".strip() if brand else name
                #i made a dictionary so the app can just look into it, find everything and get it for the output-easier way
                return {    #Did get AI to help imagine how the dictionary should be-Never used a dictionary before
                    "Name": fullName,
                    "Emoji": "📦",
                    "Serving": product.get("serving_size", "1 serving"),
                    "Date Added": datetime.date.today(),
                    "Expires": datetime.date.today() + datetime.timedelta(days=7),
                    "Carbs": round(float(nutriments.get("carbohydrates_100g", 0)), 1),
                    "Protein": round(float(nutriments.get("proteins_100g", 0)), 1),
                    "Fat": round(float(nutriments.get("fat_100g", 0)), 1),
                    "Sodium": round(float(nutriments.get("sodium_100g", 0)) * 1000, 1),
                    "Calories": round(float(nutriments.get("energy-kcal_100g", 0)), 1),
}

    except Exception as e: #If the code can't do any of this, then it will show error message to user
        st.sidebar.error(f"Error with the barcode scanner: {e}")
    return None

#Section 2d: Turns User's Body Stats into Caloris/Macro Goals,-Uses Mifflin St. Jeor Equation=====================================================================================================================================================================Under Review
def calculate_goals(age, weight_lbs, height_inches, gender, activity, goal):
    weight_kg = weight_lbs * 0.453592
    height_cm = height_inches * 2.54

    if gender == "Male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    act_mult = {"Sedentary": 1.2, "Lightly Active": 1.375, "Moderately Active": 1.55, "Very Active": 1.725}
    tdee = bmr * act_mult.get(activity, 1.2)

    if goal == "Lose Weight":
        calories = max(1200, tdee - 500)
    elif goal == "Gain Muscle":
        calories = tdee + 300
    else:
        calories = tdee

    if goal == "Gain Muscle":
        protein_g = min(180, max(60, weight_lbs * 1.0))
    else:
        protein_g = min(160, max(50, weight_lbs * 0.8))
    fat_g = max(40, (calories * 0.25) / 9)
    remaining_calories = max(0, calories - (protein_g * 4 + fat_g * 9))
    carbs_g = max(50, remaining_calories / 4)

    return {"calories": int(calories), "protein": int(protein_g), "carbs": int(carbs_g), "fat": int(fat_g)}


#Section 2e: Recipe Generator Function-Uses AI to make recipes based on whatever the user has in their current inventory=================================================================================================================================================================================Under Review
def generate_recipes(inventory, user_macro_goals):
    client = get_gemini_client()
    if not client:
        st.error("Missing Gemini API Key.")
        return ""
    if not inventory:
        return "Your inventory is empty! Add items to get recipe suggestions."

    items_list = [item["Name"] for item in inventory]
    recipe_prompt = f"""
    You are an expert culinary AI nutritionist.
    The user has these ingredients: {', '.join(items_list)}.
    Their daily targets: {user_macro_goals.get('calories')} kcal, {user_macro_goals.get('protein')}g protein,
    {user_macro_goals.get('carbs')}g carbs, {user_macro_goals.get('fat')}g fat.
    Give 2-3 recipes using mostly their ingredients, list any missing items, show estimated nutrition
    per recipe, and add a 'Health Impact' note for each. Format neatly in Markdown.
    Start each recipe title with a food emoji that matches the dish, written as a Markdown heading,
    for example: "## 🍝 Recipe 1: Garlic Butter Pasta". Format the whole response neatly in Markdown.
    """
    try:
        response = client.models.generate_content(model='gemini-3.6-flash', contents=recipe_prompt)
        return response.text
    except Exception as e:
        return f"Error generating recipes: {e}"



#Section 3:Accounts & Memory for the web app==============================================================================================================================================================================================================================Under Review

if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "guest": {"password": "guest",
                  "profile": {"age": 25, "gender": "Male", "height_inches": 68,
                              "weight_lbs": 160, "goal_weight": 150, "activity": "Moderately Active"},
                  "inventory": [], "macros": [], "resetDate": datetime.date.today()}
    }
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if not st.session_state.current_user:
    st.title("🥗 FreshPulse - Sign In")
    auth_mode = st.radio("Choose Action", ["Sign In", "Register New Account"])
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")

    if auth_mode == "Sign In":
        if st.button("Log In"):
            u = st.session_state.users_db.get(username_input)
            if u and u["password"] == password_input:
                st.session_state.current_user = username_input
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
                    "profile": {"age": 25, "gender": "Male", "height_inches": 68,
                                "weight_lbs": 160, "goal_weight": 150, "activity": "Moderately Active"},
                    "inventory": [], "macros": [], "resetDate": datetime.date.today()}
                st.session_state.current_user = username_input
                st.rerun()
            else:
                st.error("Please enter both a username and password.")
    st.stop()

user = st.session_state.current_user
user_data = st.session_state.users_db[user]
user_prof = user_data["profile"]

if user_data["resetDate"] < datetime.date.today():
    user_data["macros"] = []
    user_data["resetDate"] = datetime.date.today()





#Section 4:Entering Item By Barcode Sidebar

st.sidebar.title(f"⚙️ Your Profile, {user}") #This tells streamlit(makes our UI) to include a sidebar in our web app

#Section 4a/Header 1-User Profile Settings==========================================================================================================================================================================================================================Under Review
st.sidebar.header("👤 Body & Goal Profile")
with st.sidebar.form("profile_form"):
    age_input = st.number_input("Age", min_value=10, max_value=120, value=int(user_prof["age"]))
    gender_input = st.selectbox("Gender", ["Male", "Female"], index=0 if user_prof["gender"] == "Male" else 1)
    height_input = st.number_input("Height (inches)", min_value=36, max_value=96, value=int(user_prof["height_inches"]))
    weight_input = st.number_input("Current Weight (lbs)", min_value=50, max_value=500, value=int(user_prof["weight_lbs"]))
    goal_weight_input = st.number_input("Goal Weight (lbs)", min_value=50, max_value=500, value=int(user_prof["goal_weight"]))
    activity_options = ["Sedentary", "Lightly Active", "Moderately Active", "Very Active"]
    activity_input = st.selectbox("Activity Level", activity_options,
                                  index=activity_options.index(user_prof.get("activity", "Moderately Active")))
    profile_submitted = st.form_submit_button("💾 Save Profile & Update Goals")

if profile_submitted:
    user_prof.update({"age": age_input, "gender": gender_input, "height_inches": height_input,
                      "weight_lbs": weight_input, "goal_weight": goal_weight_input, "activity": activity_input})
    st.sidebar.success("Profile saved!")
    st.rerun()

if user_prof["goal_weight"] < user_prof["weight_lbs"]:
    goal_type = "Lose Weight"
elif user_prof["goal_weight"] > user_prof["weight_lbs"]:
    goal_type = "Gain Muscle"
else:
    goal_type = "Maintain Weight"
calculated_goals = calculate_goals(user_prof["age"], user_prof["weight_lbs"], user_prof["height_inches"],
                                   user_prof["gender"], user_prof["activity"], goal_type)
#Pick the label word based on the user's goal: gaining = a Goal to hit, losing = a Limit to stay under
if goal_type == "Gain Muscle":
    goal_word = "Goal"
elif goal_type == "Lose Weight":
    goal_word = "Limit"
else:
    goal_word = "Target"
st.sidebar.markdown(f"**Target Plan:** `{goal_type}` | **Calories:** `{calculated_goals['calories']} kcal`")
st.sidebar.divider()

#Section 4b/Header 2-Manual Item Entering-Now changed to Barcode Scanner
st.sidebar.header("Scan your Barcode Here")
allowedtypes={"png", "jpg", "jpeg"}
barcodePicture=st.sidebar.file_uploader("Upload or Scan Barcode:", type=allowedtypes, key="barcode_uploader")
if barcodePicture and st.sidebar.button("🔍 Process Barcode Photo"): #If user uploads and clicks button then this
    barcodeImg=Image.open(barcodePicture)
    with st.spinner("AI is Processing Your Image..."):
        scannedBC=barcode(barcodeImg)
    #Purpose of the next block-If scannedBC is true, then it will append the stats of the item to the inventory which allows the user to see the stats on their dashboard
    #After, they also get a success message and the app also re-runs immediatley to update everything 
    #However, if the program failed to scan the barcode due to some errors, user will get message saying that the program couldn't scan the barcode properly
    if (scannedBC):
        user_data["inventory"].append(scannedBC)
        st.sidebar.success(f"Added {scannedBC['Name']}")
        st.rerun()
    else:
        st.sidebar.error("Couldn't properly scan the barcode, please try again later.")
st.sidebar.divider()

#Section 4c/Header 3-Manual Item Entering==========================================================================================================================================================================================================================Under Review
st.sidebar.header("➕ Manually Add Item")
handName = st.sidebar.text_input("Enter Item Name Here: ")
handEmoji = st.sidebar.text_input("Emoji", value="🍽️")
handDays = st.sidebar.number_input("Item Life (in days): ", min_value=1, value=7)
handCals = st.sidebar.number_input("Calories (kcal):", min_value=0, value=100)
handCarbs = st.sidebar.number_input("Carbs (g):", min_value=0, value=10)
handProtein = st.sidebar.number_input("Protein (g):", min_value=0, value=5)
handFat = st.sidebar.number_input("Fat (g):", min_value=0, value=2)
if st.sidebar.button("Add Item Manually"):
    if handName and handDays:
        addItem = {"Name": handName,
                   "Emoji": handEmoji,
                   "Date Added": datetime.date.today(),
                   "Expires": datetime.date.today() + datetime.timedelta(days=handDays),
                   "Calories": float(handCals), "Carbs": float(handCarbs),
                   "Protein": float(handProtein), "Fat": float(handFat),
                   "Sodium": 0.0, "Serving": "1 serving"}
        user_data["inventory"].append(addItem)
        st.sidebar.success("Added " + handName + " successfully!")
        st.rerun()
st.sidebar.divider()

#Section 4d/Header 4-Limit/Goal Settings
st.sidebar.header("🎯 Daily Nutrition Limits/Goals")
#Option for user to allow certain food trackers
#They have to check the box if they want to track a specific macro
#Must choose at least a gram-Future plans is to add other unit of measurement
carbstracker=st.sidebar.checkbox("Track Carbohydrates?", value=True)
carbslimit=st.sidebar.number_input("Carb Goal/Limit(grams)", min_value=1, value=calculated_goals["carbs"]) if carbstracker else 0#=====================================================================================================================================================================Under Review
proteintracker=st.sidebar.checkbox("Track Protein?", value=True)
proteingoal=st.sidebar.number_input("Protein Goal (grams)", min_value=1, value=calculated_goals["protein"]) if proteintracker else 0#==================================================================================================================================================================Under Review
fattracker=st.sidebar.checkbox("Fat Tracker?", value=True)
fatlimit=st.sidebar.number_input("Fat Limit/Goal(grams)", min_value=1, value=calculated_goals["fat"]) if fattracker else 0#=========================================================================================================================================================================Under Review
sodiumtracker=st.sidebar.checkbox("Sodium Tracker?", value=True)
sodiumlimit=st.sidebar.number_input("Sodium Limit/Goal (milligrams)", min_value=1, value=2300) if sodiumtracker else 0#=============================================================================================================================================================================Under Review

#Section 4e/Header 5-Log Out Button
if st.sidebar.button("🚪 Log Out"):
    st.session_state.current_user = None
    st.rerun()


#Section 5:Entering Pic for AI Processing

#This part of the code allows the user to input pics of their grocery receipt or list 
#which then gets sent to AI to process and return the keys to the code

st.title("🥗 FreshPulse")#THIS IS THE NAME OF THE APP
st.write("Keep Track of Your Food to Help Stop Grocery Waste!")

tab1, tab2 = st.tabs(["📊 Inventory & Dashboard", "🍳 AI Recipes"])#=======================================================================================================================================================================================================================================Under Review

with tab1:
    eatenCarbs = sum(item.get("Carbs", 0) for item in user_data["macros"])
    eatenProtein = sum(item.get("Protein", 0) for item in user_data["macros"])
    eatenFat = sum(item.get("Fat", 0) for item in user_data["macros"])
    eatenSodium = sum(item.get("Sodium", 0) for item in user_data["macros"])

    # Display active goal rings in columns-Used AI for this part connected to Rings Function(2b)
    st.markdown("### 🎯 Your Daily Nutrition Rings (Eaten Progress)")

    cols = st.columns(4)
    active_idx = 0

    if carbstracker and active_idx < 4:
        with cols[active_idx]:
            st.markdown(create_ring_svg("Carbs", eatenCarbs, carbslimit, "g", "#FF4B4B", goal_word), unsafe_allow_html=True)
        active_idx += 1

    if proteintracker and active_idx < 4:
        with cols[active_idx]:
            st.markdown(create_ring_svg("Protein", eatenProtein, proteingoal, "g", "#00C04D", goal_word), unsafe_allow_html=True)
        active_idx += 1

    if fattracker and active_idx < 4:
        with cols[active_idx]:
            st.markdown(create_ring_svg("Fat", eatenFat, fatlimit, "g", "#FFA500", goal_word), unsafe_allow_html=True)
        active_idx += 1

    if (sodiumtracker and active_idx < 4):
        with cols[active_idx]:
            st.markdown(create_ring_svg("Sodium", eatenSodium, sodiumlimit, "mg", "#29B6F6", goal_word), unsafe_allow_html=True)
        active_idx += 1

    st.divider()

    fileUpload=st.file_uploader("Enter A Pic of your Grocery Receipt or List Here:", type=allowedtypes)
    analyzeBtn=st.button("🔍 Analyze With AI")#Button that allows user to analyze
    if(fileUpload and analyzeBtn): #Makes the uplaoding file part and pressing the button part requried for the user to analyze their reciept or list
        img=Image.open(fileUpload).convert("RGB")
        #The next lines we used AI help for because we needed to pass the image to AI for the Gemini to analyze it-We have never done this before
        with st.spinner("AI Is Processing Your Image"):#Loading Screen
            prcsdItems = aircpt(img)
        for item in prcsdItems: #Item is named here, code checks over each item AI proccessed one at a time
            life=int(item.get("life",6))#Defaults to 6 if AI doesn't give a item shelf life-IMPORTANT TO CHECK-Remember
            user_data["inventory"].append(
            { #This statement of code takes in the life variable righ above,  the item variable(each item AI processed), and the life of each item which the AI returned as "life"
                "Name": item.get("name", "Unknown"),
                "Emoji": item.get("emoji", "🍽️"),
                "Serving": item.get("serving", "1 serving"),
                "Date Added": datetime.date.today(),
                "Expires": datetime.date.today()+datetime.timedelta(days=life),
                "Carbs": float(item.get("carbs",0)),
                "Protein": float(item.get("protein",0)),
                "Fat": float(item.get("fat",0)),
                "Sodium":float(item.get("sodium",0))
            })
        st.success("Items Extracted and Saved Successfully") #What should be outputted is the name, emoji, and remaining life of each item the user had on their receipt/list in a organized way
        st.rerun()


#Section 6:Homepage/Dashboard and Expiration Grouping/Countdowns

with tab1:
    #The purpose of this part of the code is to provide the user with the stats of 
    #their food, grouping of their food, notifications about their food, and their inventory.
    if (len(user_data["inventory"])>0):
        st.header("Your Cart's Nutritional Summary:") #Purpose is to show user the total stats of all macros for each item in the user's inventory
        ttlcarbs=sum(item.get("Carbs", 0) for item in user_data["inventory"]) #Gets each item, pulls each item's carbs stats from inventory list, and adds them to one big sum, does same thing for every other macro sum
        ttlprotein=sum(item.get("Protein", 0) for item in user_data["inventory"])
        ttlfat=sum(item.get("Fat", 0) for item in user_data["inventory"])
        ttlsodium=sum(item.get("Sodium", 0) for item in user_data["inventory"])

        m_col1, m_col2, m_col3, m_col4=st.columns(4)

        if(carbstracker):
            with m_col1:
                st.metric("Carbs", f"{ttlcarbs:.1f}g", f"{goal_word}:{carbslimit}g") #.1fg rounds decimal place to the tenth, ASK FOR USER WANTS WITH THIS ONE
                st.progress(min(1.0, ttlcarbs / carbslimit) if carbslimit > 0 else 0.0) #Purpose of this is to find out if the user has reached their carb limit or not
                if(ttlcarbs>carbslimit):
                    st.error("Carb Limit Reached! Come on Bro")

        if(proteintracker):
            with m_col2:
                st.metric("Protein", f"{ttlprotein:.1f}g", f"{goal_word}:{proteingoal}g")
                st.progress(min(1.0, ttlprotein/proteingoal) if proteingoal>0 else 0.0) # the if statement makes sure that if the user never check marked the goals or tracker, then no error would occur
                if (ttlprotein>proteingoal):
                    st.success("Protein Goal Hit! Yessir")#Maybe make the phrases and bad phrases random?

        if(fattracker):
            with m_col3:
                st.metric("Fat", f"{ttlfat:.1f}g", f"{goal_word}:{fatlimit}g" ) #Not incluidng commas will show Goal/Limit on columns
                st.progress(min(1.0,ttlfat/fatlimit) if fatlimit>0 else 0.0)
                if(ttlfat>fatlimit):
                    st.error("Fat Limit Hit! Are We Serious?") #Make random phrases in a list which index pos is picked at random and then added?

        if(sodiumtracker):
            with m_col4:
                st.metric("Sodium", f"{ttlsodium:.1f}mg",f"{goal_word}: {sodiumlimit}mg")
                st.progress(min(1.0,ttlsodium/sodiumlimit) if sodiumlimit>0 else 0.0)
                if(ttlsodium>sodiumlimit):
                    st.error("You Reached Your Sodium Limit! Come On")

    st.divider()
    st.header("🛒 Your Grocery Cart")
    today=datetime.date.today()#Expiration Date-Today's Date will equal the countdown time, that is why we need to add this line, IMPORTANT
    if (len(user_data["inventory"])<1):
        st.info("No items are currently in your inventory. Please upload your receipts/lists or add items by hand.")
    else:
        for index, item in enumerate(user_data["inventory"]):
            remainLife=(item["Expires"]-today).days
            totalLife=(item["Expires"]-item["Date Added"]).days

            #Warning Math: int(totalLife*0.25) calculates and returns the number that is 25% of the item's shelf life in days. Then the code makes 
            #sure that the app doesn't trigger a warning earlier than 5 days before expiration. This is because if the totalLife was 365, taht means the notification will trigger 91 days before expiration.
            #The user will probably be annoyed and this won't be productive. The max() is there because it makes sure that the user gets at least a 2 day notice because if min gives like 0.8, it gives no time for the
            #user to cook or use the item, so max makes sure that the user has at least a 2 day head start.

            warning=max(2, min(5, int(totalLife*0.25)))
            if(remainLife<1):
                status="🔴 EXPIRED"
            elif(remainLife<=warning):
                status=f"🟡 EXPIRING SOON ({remainLife} Days Left!)"
            else:
                status=f"🟢 Fresh ({remainLife} Days Left)"
            dateFormat=item["Expires"].strftime("%m/%d/%Y")
            #Used AI for the column code, didn't know how to make individual columns for each individual data
            col1, col2=st.columns([3,1])
            with col1:
                st.markdown(f"{item['Emoji']} {item['Name']}")
                st.write(f"Status: **{status}** | Expires On: **{dateFormat}**")
                #Nutrional Facts Dropdown Menu/Bar
                with st.expander("Nutrition Facts/Detials"): #Creates That dropdown thing you can click which drops down a tab for each item with its macro stats

                    st.caption(f"📏 **Serving Size:** {item.get('Serving', '1 serving')}")

                    n_col1, n_col2=st.columns(2)
                    with n_col1:
                        st.write(f"*Carbs* {item.get('Carbs', 0)}g") #Defaults to 0 if AI didn't process or user didn't check
                        st.write(f"*Protein* {item.get('Protein',0)}g")
                    with n_col2:
                        st.write(f"*Fat* {item.get('Fat', 0)}g")
                        st.write(f"*Sodium* {item.get('Sodium',0)}mg")
                #If the item's lifetime is still greater than 0, so if it didn't expire yet and if the item did get the warning message, then the user will get a warning notification
                if(remainLife>0 and remainLife<=warning):
                    st.warning(f"⚠️ ACTION NEEDED! Use, cook, or eat {item['Name']} within {remainLife} days!")
            with col2:
                if (st.button("Mark as Eaten", key=f"btn_{index}")):
                    #If the User clicks the "Mark As Eaten" button, then that item they marked as eaten will affect their macro goals/limits and also get out of their inventory
                    #However, if the user marks things as eaten on the next day, it first activates the reset macros function before they can mark items as eaten, so the item doesn't go into the before day's macros
                    if user_data["resetDate"] < datetime.date.today():
                        user_data["macros"] = []
                        user_data["resetDate"] = datetime.date.today()
                    #Remember to pop before apend, appending before popping will mess up index pos
                    eaten=user_data["inventory"].pop(index)#Takes index position to delwte related item in list
                    user_data["macros"].append(eaten)
                    st.rerun()
with tab2:#====================================================================================================================================================================================================================================================================================Under Review
    st.header("🍳 AI Recipe Generator")
    st.write("Generate recipes from what's in your inventory!")
    user_goals = {"calories": calculated_goals["calories"], "protein": proteingoal,
                  "carbs": carbslimit, "fat": fatlimit}
    if st.button("✨ Generate Recipes from My Inventory"):
        with st.spinner("Crafting recipes..."):
            st.markdown(generate_recipes(user_data["inventory"], user_goals))

st.divider()
st.caption("Created By Sai Belde and Aarnav Vurputoor")
