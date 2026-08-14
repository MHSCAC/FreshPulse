
#Section 1:Tools/Packages for web app

#This allows us to import the tools needed for our app, so basically like gen ai from google allows us to use Gemini for image processing, streamlit allows us to build our ferontend using only python, etc."
import math
import random
#Streamlit==st, easier to write st rather that streamlit every time
import streamlit as st
import streamlit.components.v1 as components
#datetime=python tool for tracking dates, in this case, expiration dates
import datetime
#Allows AI to see and read the uploaded image from the user
from PIL import Image
import json
from google import genai

#Prevent Accidental Refreshes and To Alert User

#Did use AI for this part
components.html(
    """
    <script>
    window.addEventListener('beforeunload', function (e) {
        // Cancel the event to trigger the browser prompt
        e.preventDefault();
        // Chrome requires returnValue to be set
        e.returnValue = '';
    });
    </script>
    """,
    height=0,
)




#Section 2:Functions-Remember to tell Aarnav to make sure all function are in this section
#Remember-Only Top Down Code

#Section 2a:AI Proccessed Screenshots/Receipts

#We did use AI to help us to code this part. We have never used API keys or imported AI in a web app before, so we got AI to teach us how to code something like that.
def aircpt(image):
    apikey = st.secrets.get("geminiApiKey")
    if not apikey:
        st.error("Missing geminiApiKey in Streamlit Secrets!")
        return []
    client=genai.Client(api_key=apikey) #variable is basically a messenger which allows the web app to communicate with google AI
    #I did ask AI to create the prompt. My wording is kind of messy and confusing, so I told AI what I wanted the prompt to say and then the AI fixed and created the more neat prompt. Also figured that since this prmpt is for AI, then AI should prob creat the prompt
    aiprompt = (
    "Analyze this grocery receipt image. Extract all food items considering brand names when available. "
    "For each item, estimate/extract: item name, emoji, shelf life in days (integer), "
    "carbohydrates in grams (number), protein in grams (number), fat in grams (number), "
    "and sodium in milligrams (number). "
    "Return ONLY a JSON list with keys: 'name', 'emoji', 'life', 'carbs', 'protein', 'fat', 'sodium'."
    #Basically asked AI to give the app the item name, a deisgnated emoji, a lifetime, the carbs, the protein, the fat, and sodium, of each item on the user's receipt
)    
    response = client.models.generate_content(
    model='gemini-flash-latest', #Cant use 2.5 flash, google retired it for new users
    contents=[aiprompt, image],#This makes the code send the user's image and our prompt to Gemini
    config={'response_mime_type': 'application/json'}
)
    #CleanText Function will break if everything is not in one line, adding lines will overide and revert back to the original text given by the AI
    cleanText = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(cleanText)#This returns and makes the java text that Gemini gives us into python text, so the web app can read and use it.

#Section 2b: Rings for Macro Stats-Did use AI for this part, way too complicated for me
def create_ring_svg(label, current, goal, unit, color):
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
        <div style="font-size: 11px; color: #777;">Goal: {goal}{unit}</div>
    </div>
    """





#Section 3:Memory for the web app

#Makes sure that even if the user refreshes the page, their data will not be lost.
if ("inventory" not in st.session_state):
    st.session_state.inventory=[]

#Makes sure that the app remembers the user's total, protein, fat, sodium, and carb goal/limits.
if ("macros" not in st.session_state):
    st.session_state.macros=[]




#Section 4:Entering Item By Hand-In Sidebar

st.sidebar.title("⚙️ Settings") #This tells streamlit(makes our UI) to include a sidebar in our web app

#Section 4a/Header 1-Manual Item Entering
st.sidebar.header("➕ Add Item") 
handName=st.sidebar.text_input("Enter Item Name Here: ")
handEmoji=st.sidebar.text_input("Emoji",value="🍽️")
handDays=st.sidebar.number_input("Item Life (in days): ", min_value=1)
#Used AI for the date part. We never learnt how to get dates and what day it is in python.
if (st.sidebar.button("Add Item Manually")):
    if (handName and handDays): #Creates buttons and text boxes for user to add item by hand, and only also makes sure they don't forget to add the item's remaining lifetime and name
        addItem={"Name":handName,
              "Emoji":handEmoji,
              "Date Added":datetime.date.today(),
              "Expires":datetime.date.today()+datetime.timedelta(days=handDays)}
        st.session_state["inventory"].append(addItem)#Makes sure that the item the user added goes in their account and stays in their account
        st.sidebar.success("Added " + handName + " successfully!")
st.sidebar.divider()

#Section 4b/Header 2-Limit/Goal Settings
st.sidebar.header("🎯 Nutrion Limits/Goals")
#Option for user to allow certain food trackers
#They have to check the box if they want to track a specific macro
#Must choose at least a gram-Future plans is to add other unit of measurement
carbstracker=st.sidebar.checkbox("Track Carbohydrates?", value=True)
carbslimit=st.sidebar.number_input("Carb Goal/Limit(grams)", min_value=1, value=250) if carbstracker else 0
proteintracker=st.sidebar.checkbox("Track Protein?", value=True)
proteingoal=st.sidebar.number_input("Protein Goal (grams)", min_value=1, value=100) if proteintracker else 0
fattracker=st.sidebar.checkbox("Fat Tracker?", value=True)
fatlimit=st.sidebar.number_input("Fat Limit/Goal(grams)", min_value=1, value=50) if fattracker else 0
sodiumtracker=st.sidebar.checkbox("Sodium Tracker?", value=True)
sodiumlimit=st.sidebar.number_input("Sodium Limit/Goal (grams)", min_value=1, value=50) if sodiumtracker else 0





#Section 5:Entering Pic for AI Processing

#This part of the code allows the user to input pics of their grocery receipt or list 
#which then gets sent to AI to process and return the keys to the code

st.title("🥗 FreshPulse")#THIS IS THE NAME OF THE APP-REMEMBER TO ASK AARNAV IF HE WANTS TO CHANGE IT
st.write("Keep Track of Your Food to Help Stop Grocery Waste!")

eatenCarbs = sum(item.get("Carbs", 0) for item in st.session_state["macros"])
eatenProtein = sum(item.get("Protein", 0) for item in st.session_state["macros"])
eatenFat = sum(item.get("Fat", 0) for item in st.session_state["macros"])
eatenSodium = sum(item.get("Sodium", 0) for item in st.session_state["macros"])

# Display active goal rings in columns-Used AI for this part connected to Rings Function(2b)
st.markdown("### 🎯 Your Daily Nutrition Rings (Eaten Progress)")

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

if (sodiumtracker and active_idx < 4):
    with cols[active_idx]:
        st.markdown(create_ring_svg("Sodium", eatenSodium, sodiumlimit, "mg", "#29B6F6"), unsafe_allow_html=True)
    active_idx += 1

st.divider()

types={"png", "jpg", "jpeg"}
fileUpload=st.file_uploader("Enter A Pic of your Grocery Receipt or List Here:", type=types)
analyzeBtn=st.button("🔍 Analyze With AI")#Button that allows user to analyze
if(fileUpload and analyzeBtn): #Makes the uplaoding file part and pressing the button part requried for the user to analyze their reciept or list
    img=Image.open(fileUpload)
    #The next lines we used AI help for because we needed to pass the image to AI for the Gemini to analyze it-We have never done this before
    with st.spinner("AI Is Processing Your Image"):#Loading Screen
        prcsdItems = aircpt(img)
    for item in prcsdItems: #Item is named here, code checks over each item AI proccessed one at a time
        life=int(item.get("life",6))#Defaults to 6 if AI doesn't give a item shelf life-IMPORTANT TO CHECK-Remember
        st.session_state["inventory"].append(
        { #This statement of code takes in the life variable righ above,  the item variable(each item AI processed), and the life of each item which the AI returned as "life"
            "Name": item.get("name", "Unknown"),
            "Emoji": item.get("emoji", "🍽️"),
            "Date Added": datetime.date.today(),
            "Expires": datetime.date.today()+datetime.timedelta(days=life),
            "Carbs": float(item.get("carbs",0)),
            "Protein": float(item.get("protein",0)),
            "Fat": float(item.get("fat",0)),
            "Sodium":float(item.get("sodium",0))
        })
    st.success("Items Extracted and Saved Successfully") #What should be outputted is the name, emoji, and remaining life of each item the user had on their receipt/list in a organized way



#Section 6:Homepage/Dashboard and Expiration Grouping/Countdowns

#The purpose of this part of the code is to provide the user with the stats of 
#their food, grouping of their food, notifications about their food, and their inventory.
if(len(st.session_state["inventory"])>0):
    st.header("Your Nutritional Summary:")
    ttlcarbs=sum(item.get("Carbs", 0) for item in st.session_state["inventory"]) #Gets each item, pulls each item's carbs stats from inventory list, and adds them to one big sum, does same thing for every other macro sum
    ttlprotein=sum(item.get("Protein", 0) for item in st.session_state["inventory"])
    ttlfat=sum(item.get("Fat", 0) for item in st.session_state["inventory"])
    ttlsodium=sum(item.get("Sodium", 0) for item in st.session_state["inventory"])

    m_col1, m_col2, m_col3, m_col4=st.columns(4)

    if(carbstracker):
        with m_col1:
            st.metric("Carbs", f"{ttlcarbs:.1f}g/{carbslimit}g") #.1fg rounds decimal place to the tenth, ASK FOR USER WANTS WITH THIS ONE
            st.progress(min(1.0, ttlcarbs / carbslimit) if carbslimit > 0 else 0.0) #Purpose of this is to find out if the user has reached their carb limit or not
            if(ttlcarbs>carbslimit):
                st.error("Carb Limit Reached! Come on Bro")

    if(proteintracker):
        with m_col2:
            st.metric("Protein", f"{ttlprotein:.1f}g/{proteingoal}g")
            st.progress(min(1.0, ttlprotein/proteingoal) if proteingoal>0 else 0.0) # the if statement makes sure that if the user never check marked the goals or tracker, then no error would occur
            if (ttlprotein>proteingoal):
                st.success("Protein Goal Hit! Yessir")#Maybe make the phrases and bad phrases random?

    if(fattracker):
        with m_col3:
            st.metric("Fat",f"{ttlfat:.1f}g/{fatlimit}g" )
            st.progress(min(1.0,ttlfat/fatlimit) if fatlimit>0 else 0.0)
            if(ttlfat>fatlimit):
                st.error("Fat Limit Hit! Are We Serious?") #Make random phrases in a list which index pos is picked at random and then added?

    if(sodiumtracker):
        with m_col4:
            st.metric("Sodium", f"{ttlsodium}g/{sodiumlimit}g")
            st.progress(min(1.0,ttlsodium/sodiumlimit) if sodiumlimit>0 else 0.0)
            if(ttlsodium>sodiumlimit):
                st.error("You Reached Your Sodium Limit! Come On")

st.divider()
st.header("🛒 Your Grocery Cart")
today=datetime.date.today()#Expiration Date-Today's Date will equal the countdown time, that is why we need to add this line, IMPORTANT
if (len(st.session_state["inventory"])<1):
    st.info("No items are currently in your inventory. Please upload your receipts/lists or add items by hand.")
else:
    for index, item in enumerate(st.session_state["inventory"]):
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
                n_col1, n_col2=st.columns(2)
                with n_col1:
                    st.write(f"*Carbs* {item.get('Carbs', 0)}g") #Defaults to 0 if AI didn't process or user didn't check
                    st.write(f"*Protein* {item.get('Protein',0)}g")
                with n_col2:
                    st.write(f"*Fat* {item.get('Protein', 0)}g")
                    st.write(f"*Sodium* {item.get('Sodium',0)}g")
            #If the item's lifetime is still greater than 0, so if it didn't expire yet and if the item did get the warning message, then the user will get a warning notification
            if(remainLife>0 and remainLife<=warning):
                st.warning(f"⚠️ ACTION NEEDED! Use, cook, or eat {item['Name']} within {remainLife} days!")
        with col2:
            if (st.button("Mark as Eaten", key=f"btn_{index}")):
                #If the User clicks the "Mark As Eaten" button, then that item they marked as eaten will affect their macro goals/limits and also get out of their inventory
                #Remember to pop before apend, appending before popping will mess up index pos
                eaten=st.session_state["inventory"].pop(index)#Takes index position to delwte related item in list
                st.session_state["macros"].append(eaten)
                st.rerun()
