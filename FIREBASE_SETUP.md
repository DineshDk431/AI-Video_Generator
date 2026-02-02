# 🔥 Firebase Setup Guide for Cloud Mode

To use the **Cloud (Faster)** generation mode, you need to connect the app to your Firebase project.

## Step 1: Create a Project
1.  Go to the [Firebase Console](https://console.firebase.google.com/).
2.  Click **"Add project"** and give it a name (e.g., "AI Video Cloud").
3.  Disable Google Analytics (not needed) and Create.

## Step 2: Get your Key 🔑
1.  In your new project, click the **Gear Icon ⚙️** (Project Settings) in the top left.
2.  Go to the **"Service accounts"** tab.
3.  Click **"Generate new private key"**.
4.  Confirm by clicking **"Generate key"**.
5.  A file (JSON) will download to your computer.

## Step 3: Install the Key
1.  **Rename** the downloaded file to exactly: `serviceAccountKey.json`
2.  **Move** this file into your project folder:
    `c:\AI Video\serviceAccountKey.json`

## Step 4: Setup Database
1.  In Firebase Console, go to **"Firestore Database"** (left menu).
2.  Click **"Create database"**.
3.  Choose **"Start in test mode"** (easier for personal use).
4.  Select a location (e.g., `us-central1`).

✅ **Done!** Now restart the app using `streamlit run app.py` and select "Cloud Mode".
