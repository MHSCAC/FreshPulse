
#Section 1:Tools/Packages for web app



#This allows us to import the tools needed for our app, like gen ai from google allows us to use Gemini for image processing, streamlit allows us to build our ferontend using only python, etc."
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
    aiprompt = "Analyze this grocery receipt image. Extract all food items. For each item, provide name, emoji, and estimated shelf life in days as an integer. Return ONLY a JSON list with keys: 'name', 'emoji', 'life'." #The prompt variable and text in it is the message that gets sent to Google AI with the user's uploaded receipt.

    response = client.models.generate_content(
    model='gemini-flash-latest', #Cant use 2.5 flash, google retired it for new users
    contents=[aiprompt, image],#This makes the code send the user's image and our prompt to Gemini
    config={'response_mime_type': 'application/json'}
)
    #CleanText Function will break if everything is not in one line, adding lines will overide and revert back to the original text given by the AI
    cleanText = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(cleanText)#This returns and makes the java text that Gemini gives us into python text, so the web app can read and use it.





#Section 3:Memory for the web app

#Makes sure that even if the user refreshes the page, their data will not be lost.
if ("inventory" not in st.session_state):
    st.session_state.inventory=[]








#Section 4:Entering Item By Hand-In Sidebar

st.sidebar.title("⚙️ Settings") #This tells streamlit(makes our UI) to include a sidebar in our web app
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









#Section 5:Entering Pic for AI Processing

#This part of the code allows the user to input pics of their grocery receipt or list 
#which then gets sent to AI to process and return the keys to the code

st.title("🥗 FreshPulse")#THIS IS THE NAME OF THE APP-REMEMBER TO ASK AARNAV IF HE WANTS TO CHANGE IT
st.write("Keep Track of Your Food to Help Stop Grocery Waste!")
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
        st.session_state["inventory"].append({#This statement of code takes in the life variable righ above,  the item variable(each item AI processed), and the life of each item which the AI returned as "life"
            "Name": item.get("name", "Unknown"),
            "Emoji": item.get("emoji", "🍽️"),
            "Date Added": datetime.date.today(),
            "Expires": datetime.date.today()+datetime.timedelta(days=life)
        })
    st.success("Items Extracted and Saved Successfully") #What should be outputted is the name, emoji, and remaining life of each item the user had on their receipt/list in a organized way



#Section 6:Homepage/Dashboard and Expiration Grouping/Countdowns

#The purpose of this part of the code is to provide the user with the stats of 
#their food, grouping of their food, notifications about their food, and their inventory.

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
            #If the item's lifetime is still greater than 0, so if it didn't expire yet and if the item did get the warning message, then the user will get a warning notification
            if(remainLife>0 and remainLife<=warning):
                st.warning(f"⚠️ ACTION NEEDED! Use, cook, or eat {item['Name']} within {remainLife} days!")
        with col2:
            if (st.button("Mark as Eaten", key=f"btn_{index}")):
                #If the User clicks the "Mark As Eaten" button, then that item they marked as eaten, will get out of their inventory and dashboard
                st.session_state["inventory"].pop(index)
                st.rerun()
