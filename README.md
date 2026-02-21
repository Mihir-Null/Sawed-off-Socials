# Sawed-off-Socials
Powerful social media automation for interest clubs and organizations. Sawed-off-Socials primarily automates posting to multiple social media accounts, including Discord, Instagram, and Google services. Currently automates discord event creation and announcement, emailing to lists, automatic custom emails, google calendar event creation, posting to Instagram as both a post and a story. This project is feature-complete but ultimately still a work in progress.

# Usage
The best way to use the web app is through the provided docker image. If you are not using docker, you can use the standalone binary or source code. All relevant details can be found in the Installation and Releases section.

Once installed you must create and load all required authentication keys, stored securely in a ```.env``` file. You then simply launch the application, enter in all fields for your event, and launch relevant automations. All event details will be saved locally (via the sync config button, which is also called automatically on posting) and loaded on later uses so most setup only needs to occur the first time.

## Functions

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

6. **Event Location / Meeting Link**
   - Provide the physical location or a URL for the meeting.  
   - This can be a Zoom, Google Meet, physical address, or a combination. Standard string formatting can be used to combine fields.

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
It is important to note that all of these functions exist in the relevant Jack_[relevant cloud provider].py files and are all commented and written for readability. If you would like to customize the content, structure or sending of any of these functions, simply enter into these .py files and edit away to your heart's content. This, of course, assumes you know what you're doing and can recompile the relevant docker image or are running directly from source

All details that are inputted are read and saved into a dictionary called `details` details has all the fields specified in the `fields` variable in main.py. If you would like to add a field, for example website, simply add `"website"` into the fields array and the bot will automatically reconfigure all relevant GUI items. You can then use `details["website"]` anywhere in the code for your inputted website.


# Setup and Authentication Keys
All auth keys and API credentials should be stored in a .env file in the same directory as the Sawed-Off-Socials application/files. A .env.example file has been provided to show all required fields with instructions to obtain keys below. 

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

### **Step 6: Store Credentials in the `.env` File**
Your `.env` should have the following entries added look like this (but with your actual keys):  

```
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_PROJECT_ID=your_google_project_id_here
```

If hosting as a webapp you must set your redirect URI to your public domain, otherwise, just leave it as the default localhost.
```
# The redirect URI must match what you set in GCP. 
# Example: https://yourwebsitehere.com/api/auth/callback
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/callback
```

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
   - Under "Bot Permissions," select standard permissions required for posting and creating events (Administrator or specific channel permissions).
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
- **Cloudinary Credentials** (Required for media hosting - see Cloudinary section below)

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
   instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement
   ```
4. Click **"Generate Access Token"**. 
5. **CRITICAL**: A popup will appear. You MUST select the Facebook Page and the Instagram Business Account you want to use. If you don't select them, the token will not have permission to post.
6. **Copy the Access Token** and paste it into `INSTAGRAM_ACCESS_TOKEN` in your `.env` file.

---

### **Step 5: Get Your Instagram User ID**
1. Instead of manual lookups, we've provided a script to find the correct ID for you.
2. Ensure your `INSTAGRAM_ACCESS_TOKEN` is saved in your `.env` file.
3. Run the following command in your terminal:
   ```bash
   python3 find_insta_id.py
   ```
4. The script will output the correct **Instagram Business Account ID**.
5. Copy this ID and paste it into `INSTAGRAM_USER_ID` in your `.env` file.

---

### **Step 6: Store Credentials in the `.env` File**
Your `.env` should look like this (but with your actual keys):  

```
INSTAGRAM_ACCESS_TOKEN=your-access-token-here
INSTAGRAM_USER_ID=your-user-id-here
```

## Cloudinary (Required for Instagram)
Instagram requires a publicly accessible URL for all media. Cloudinary is used to host your local images and videos so Instagram can fetch them.

### **Step 1: Create a Cloudinary Account**
1. Sign up for a free account at [Cloudinary](https://cloudinary.com/users/register/free).
2. Once logged in, go to your **Dashboard**.

### **Step 2: Get Your Credentials**
1. On the Dashboard, you will see your **Product Environment Details**:
   - **Cloud Name**
   - **API Key**
   - **API Secret** (Click the eye icon to reveal it)

### **Step 3: Store Credentials in the `.env` File**
Add these to your `.env` file under the Cloudinary section:
```bash
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

# Installation and Releases

Sawed-off-Socials have been packaged for distribution in three ways: as a standalone binary, a Docker image, or a source ZIP.

## 1. Standalone Binary (Nuitka)
For users who don't want to install Python, you can compile the app into a single executable. This version will launch the server and automatically open the UI in the default web browser.

1.  **Install Nuitka**:
    ```bash
    pip install nuitka
    ```
2.  **Build the application**:
    ```bash
    python -m nuitka --onefile --standalone --include-data-dir=frontend/dist=frontend/dist --include-data-dir=backend=backend run_app.py
    ```
    - Replace `python` with `python3` if needed.
    - The resulting executable will be in the `run_app.dist` or `run_app.bin` folder (or as `run_app.exe` on Windows).

## 2. Docker (Production)
If you are hosting the app on a server, use the provided Dockerfile.

1.  **Build the image**:
    ```bash
    docker build -t sawed-off-socials:latest .
    ```
2.  **Run the container**:
    ```bash
    docker run -p 8000:8000 --env-file .env sawed-off-socials:latest
    ```

## 3. Source Release (ZIP)
Simply download the ZIP archive for the current development version from the code tab in the github repository.
