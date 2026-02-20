# Sawed-off-Socials
Powerful social media automation for interest clubs and organizations. Sawed-off-Socials primarily automates posting to multiple social media accounts, including Discord, Instagram, and Google services. Currently automates discord event creation and announcement, emailing to lists, automatic custom emails, google calendar event creation, posting to Instagram as both a post and a story. This project is feature-complete but ultimately still a work in progress.

# Usage
The best way to use the bot is to clone the repository, create a new virtual environment for python using the requirements.txt and running main.py with python3. (To be fully implemented) However an .exe file has also been provided through pyinstaller, though this has not been as thoroughly tested.

Once cloned go down to setup to create and load all required authentication keys. You then simply launch the application, enter in all fields for your event, and click the relevant buttons after saving. All event details will be saved locally and loaded on later uses so most setup only needs to occur the first time.

## Functions
![image](https://github.com/user-attachments/assets/d297690b-bab4-4304-9bdc-cd68e2da0935)

**Post to Discord**: Posts an announcement to discord and mentions everyone. Also creates a discord event to collect RSVPs. Event image is sent as an embed below the announcement

**Send Emails**: Sends emails to all emails detailed in csv about the event

**Add to Calendar**: Creates a Google Calendar entry for the event

**Post to Instagram**: Posts to Instagram and sends that post to story

**Custom Emails**: Sends customized emails, specified by name in detail entry, using the custom emails dictionary defined in custom_emails.json.

**(Planned/WIP) Create Canva Poster**: Automatically create a poster for the event from a canva template to be sent in all messaging.


### A Note on Custom Emails
Custom emails are a list of prespecified emails to be sent for things like scheduling rooms, requesting to be put on listservs, newsletters, etc. All custom emails must be specified as a set of key value pairs in `custom_emails.json`. The keys being are the "entry name" that must be referred to in the adminjack input fields to specify which custom emails should be sent, and the values are 3-tuples that correspond to the email address, subject line and body respectively.

Sawed-off-Socials will automatically replace formatted fields with the relevant inputted entry from Event Details. For example if you have `{club_name}` somehwhere in one of your custom email jsons. Putting in your club name in the "Enter Event Details" screen will ensure that the `{club_name}` is replaced with the actual club name that you inputted. This follows the python convention where the field must be enclosed in curly braces. A full list of fields is detailed below:
```
"event_name", "description", "image", "server_name", "channel_name", "meeting_link", "event_date", "event_time", "timezone", "calendar_name", "csv_file", "email_column", "event_duration", "club_name", "custom emails list","more_info_link"
```


## Fields
![image](https://github.com/user-attachments/assets/3e7bd455-6d2f-4882-a7e5-fc646079827b)
1. **Event Name**  
   - Enter the name/title of the event.
   - This prefaces the event description and is used as the event title whenever relevant
   - This helps identify the event in communications and scheduling systems.

2. **Description**  
   - Provide a description of the event that will be sent in all communications.  
   - This can include details such as the agenda, purpose, key participants, etc.
   - more key details such as the location, date and time will automatically be attached to the end of this description

3. **Image**  
   - Browse and upload an image related to the event.  
   - This could be a flyer, logo, or promotional material.

4. **Server Name**  
   - Enter the name of the discord server where the event is to be announced  

5. **Channel Name**  
   - Specify the name of the channel within the server where the event will be discussed or announced.  

6. **Meeting Link** -> **Event Location**
   - **This field serves as both the meeting link and the event location for the event. Whatever is put here is exactly what will be printed out when the bot announces where the event is happening and standard string formatting can be used**
   - **This confusing naming is currently in the process of being fixed as it requires some refactoring**
   - Provide a URL for the meeting and/or the event location.  
   - This can be a Zoom, Google Meet, physical location reference or a combination of all, standard string formatting can be used to combine the fields.

8. **Event Date**  
   - Enter the event date in `YYYY-MM-DD` format.  
   - Ensures proper scheduling and calendar integration.

9. **Event Time**  
   - Specify the time of the event in `HH:MM` format (24-hour clock).  

10. **Timezone**  
    - Define the timezone of the event (e.g., `EST`, `UTC`).  
    - This is also what is used to synchronize the event time in discord and on google calendar.

11. **Calendar Name**  
    - Provide the name of the calendar where the event should be added.
    - If none or an invalid calendar name is provided it will instead schedule on whatever calendar is set to be the primary. 
    - Useful for the Google Calendar integration.

12. **CSV File**  
    - Browse and select a `.csv` file containing participant or invitee data.
    - This `.csv` file is what is used to extract email addresses for automatic emailing in the *Send Emails* Function 

13. **Email Column**  
    - Enter the column name in the CSV file that contains email addresses.  
    - Required for sending invites automatically.

14. **Event Duration**  
    - Specify how long the event will last in hours (e.g., `1.5`).  

15. **Club Name**  
    - Enter the club or organization hosting the event.  
    - Useful for context in shared calendars and emails.

16. **Custom Emails List**  
    - This is where you enter comma separated entries from the `custom_emails.json`
    - All custom emails corresponding to the entries in the `.json` file are sent when you press the button

17. **More Info Link**  
    - Provide a link to more event details, such as your website, linktree, etc..  
    - This is used as supplementary inforrmation on emails and in some other places.

### **Saving the Event**
Once all necessary fields are filled out, click **Save** to store the event details and trigger any necessary scheduling or communication actions. It is usually recommended to always Save the event before executing any given set of actions.


## A Note on General Customization
It is important to note that all of these functions exist in the relevant Jack_[relevant cloud provider].py files and are all commented and written for readability. If you would like to customize the content, structure or sending of any of these functions, simply enter into these .py files and edit away to your heart's content. **This will not work for the .exe as it is pre-compiled, editing these for the exe will require rebuilding with pyinstaller**

All details that are inputted are read and saved into a dictionary called `details` details has all the fields specified in the `fields` variable in main.py. If you would like to add a field, for example website, simply add `"website"` into the fields array and the bot will automatically reconfigure all relevant GUI items. You can then use `details["website"]` anywhere in the code for your inputted website.


# Setup and Authentication Keys
## Google
The Google endpoints for Sawed-off-Socials rely on a Google Cloud App. The safest way to route your information for this is to create your own Google Cloud App for your club's use.
To obtain the `client_secret` for your Google Cloud app, follow these steps:

### **1. Create or Select a Google Cloud Project**
- Go to the [Google Cloud Console](https://console.cloud.google.com/).
- Select an existing project or create a new one.
- Go to the OAuth Consent screen (or when prompted to) Edit the App Registration
- When asked to add scopes enter the list below:
  - https://www.googleapis.com/auth/calendar.app.created
  - https://www.googleapis.com/auth/calendar.calendarlist.readonly
  - https://www.googleapis.com/auth/calendar.events.freebusy
  - https://www.googleapis.com/auth/calendar.events.public.readonly
  - https://www.googleapis.com/auth/calendar.settings.readonly
  - https://www.googleapis.com/auth/calendar.freebusy
  - https://www.googleapis.com/auth/gmail.send
  - https://www.googleapis.com/auth/calendar.readonly
  - https://www.googleapis.com/auth/calendar.calendars
  - https://www.googleapis.com/auth/calendar.calendars.readonly
  - https://www.googleapis.com/auth/calendar.events
  - https://www.googleapis.com/auth/calendar.events.owned
  - https://www.googleapis.com/auth/calendar.events.owned.readonly
  - https://www.googleapis.com/auth/calendar.events.readonly
- When prompted to enter Test users add the email address you intend to use for the club

### **2. Enable OAuth 2.0 for Your App**
- Navigate to **APIs & Services** > **Credentials**.
- Click **Create Credentials** > **OAuth 2.0 Client ID**.

### **3. Configure OAuth Consent Screen**
- If you haven't already set it up, you’ll be prompted to configure the OAuth consent screen.
- Choose **External** (for public use) or **Internal** (for Google Workspace users in your org).
- Fill in the required details, including scopes and authorized domains.

### **4. Generate Client ID and Secret**
- Under **Credentials**, click **Create Credentials** > **OAuth Client ID**.
- Choose **Desktop App** as your app type:
- Configure **Authorized Redirect URIs** if you want to.
- Click **Create** to generate the credentials.

### **5. Download Your Client Secret**
- A dialog box will show the **Client ID** and **Client Secret**.
- Click **Download JSON** to save your credentials (this includes `client_secret`).

### **6. Store It in the Sawed-off-Socials Folder**
- Store your credentials in the same folder as the Sawed-off-Socials python scripts. **Guard this secret file closely**

## Discord
### **How to Create a Discord Bot and Store Its Credentials in a `.env` File**

#### **Step 1: Create a Discord Application**
1. **Go to the Discord Developer Portal**:  
   - Visit [Discord Developer Portal](https://discord.com/developers/applications).
   - Log in with your Discord account.

2. **Create a New Application**:  
   - Click **"New Application"**.
   - Give your bot a name (e.g., `Administrator Jack`).
   - Click **"Create"**.

#### **Step 2: Create a Bot User**
1. **Go to the "Bot" Section**:  
   - In the left menu, select **"Bot"**.
   - Click **"Add Bot"**, then confirm by clicking **"Yes, do it!"**.

2. **Configure the Bot**:  
   - Set an **Avatar (optional)**.
   - Toggle **"Public Bot"** off if you don’t want others adding the bot.
   - Enable **"Presence Intent"** and **"Server Members Intent"** (for mentioning users).
   - Copy the **Token** (you will need this in `.env`).

#### **Step 3: Assign Required Permissions**
1. **Go to "OAuth2" → "URL Generator"**:
   - Select **"Bot"** as a scope.
   - Under "Bot Permissions," select:
   - ![image](https://github.com/user-attachments/assets/835d553f-8550-4b83-9b59-d7e41ccb6bcc)
   - You can also just give it Administrator permissions or all permissions but I'm not responsible if it goes rogue.
   - Copy the generated URL.

2. **Invite the Bot to Your Server**:  
   - Paste the copied URL into your browser.
   - Select your server and authorize.

#### **Step 4: Store Credentials in a `.env` File**
1. **Create a `.env` File** in Your Project Directory.
2. **Store the Bot Token Securely**:
   ```
   DISCORD_TOKEN=your-bot-token-here
   ```
## Instagram 
To post to Instagram using the Instagram Graph API, you need the following credentials:  

- **Instagram Access Token** (`INSTAGRAM_ACCESS_TOKEN`)  
- **Instagram User ID** (`INSTAGRAM_USER_ID`)  

### **Step 1: Set Up a Meta (Facebook) App**
1. **Go to the [Meta Developer Portal](https://developers.facebook.com/)**.  
2. Click **"Get Started"** and follow the on-screen instructions if you haven't already set up a developer account.  
3. Go to **"My Apps"** → Click **"Create App"**.  
4. Select **"Business"** and click **"Continue"**.  
5. Enter the app name, contact email, and create the app.  

---

### **Step 2: Add Instagram API to Your App**
1. Inside your newly created app, go to **"Add a Product"** → Select **"Instagram Graph API"** → Click **"Set Up"**.  
2. In the left panel, go to **"Settings" → "Basic"**.  
3. Scroll down to **"Add Platform"** → Select **"Website"** and enter your website URL (use any if testing).  

---

### **Step 3: Create an Instagram Business/Creator Account**
1. Go to [Instagram](https://www.instagram.com/) and log in.  
2. Click **Profile** → **Edit Profile**.  
3. Under **"Professional Account"**, ensure your account is set to **Business or Creator**. **Note: Personal accounts are no longer supported via the Graph API as of late 2024.**
4. **Link your Instagram account** to a **Facebook Page** (this is mandatory).  
   - Go to **Facebook Business Suite** → **Business Settings** → **Accounts → Instagram Accounts** → **Add Account**.  

---

### **Step 4: Generate a User Access Token**
1. **Go to the [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/)**.  
2. Select your App from the dropdown.  
3. Under **Permissions**, add the following:  
   ```
   instagram_basic, instagram_content_publish
   ```
4. Click **"Generate Access Token"** and approve the request.  
5. **Copy the Access Token** (`INSTAGRAM_ACCESS_TOKEN`).  

---

### **Step 5: Get Your Instagram User ID**
1. Open a new browser tab and enter the following request in the [Graph API Explorer](https://developers.facebook.com/tools/explorer/):  
   ```
   https://graph.facebook.com/v22.0/me?fields=id,username&access_token=YOUR_ACCESS_TOKEN
   ```
2. Click **Submit**.  
3. The response will contain your Instagram **User ID** (`INSTAGRAM_USER_ID`).  

---

### **Step 6: Store Credentials in the `.env` File**
Create or edit the `.env` file and store the credentials securely:  

```
INSTAGRAM_ACCESS_TOKEN=your-access-token-here
INSTAGRAM_USER_ID=your-user-id-here
```
