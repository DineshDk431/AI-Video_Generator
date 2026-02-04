# 🚀 Streamlit Cloud Deployment Guide

## ✅ What's Changed (HuggingFace API Mode)

Your app now uses **HuggingFace Inference API** for cloud video generation:
- ✅ **No GPU needed** - HuggingFace runs the model on their servers
- ✅ **Works 24/7** - Even when your laptop is OFF
- ✅ **No cloud_worker.py needed** - Delete or ignore it
- ✅ **Lightweight** - Only ~100MB dependencies

---

## 📋 Quick Deploy Steps

### Step 1: Push to GitHub

**Option A - Using GitHub Web (No Git needed):**
1. Go to https://github.com/new
2. Create repo: `ai-video-generator`  
3. Click **"uploading an existing file"**
4. Drag & drop ALL files from `C:\AI Video`
5. ⚠️ **EXCLUDE these files** (don't upload):
   - `serviceAccountKey.json`
   - `.env`
   - `venv/` folder
   - `outputs/` folder

**Option B - Using Git CLI:**
```bash
cd "C:\AI Video"
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/ai-video-generator.git
git push -u origin main
```

---

### Step 2: Important! Switch to Cloud Requirements

Before deploying, rename the requirements file:
```
requirements_cloud.txt  →  requirements.txt
```
Or just copy contents of `requirements_cloud.txt` into `requirements.txt`.

This removes heavy PyTorch dependencies that crash Streamlit Cloud.

---

### Step 3: Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Sign in with GitHub
3. Click **"New app"**
4. Select your repository
5. Main file path: `app.py`
6. Click **"Deploy!"**

---

### Step 4: Configure Secrets

After deploying:
1. Go to your app's dashboard
2. Click **Settings** → **Secrets**
3. Add these secrets:

```toml
# REQUIRED - Get from https://huggingface.co/settings/tokens
HF_TOKEN = "hf_your_token_here"
```

That's it! The HuggingFace token is all you need.

---

## 🎯 How It Works Now

```
┌──────────────────┐      ┌─────────────────────┐
│   Your Website   │ ───► │  HuggingFace API    │
│ (Streamlit Cloud)│      │  (Their GPU Servers)│
│   Always Online  │ ◄─── │   Generates Videos  │
└──────────────────┘      └─────────────────────┘
```

**User visits your site → Enters prompt → HuggingFace generates video → Video appears**

All automatic, no laptop needed! 🎉

---

## ⚠️ HuggingFace API Notes

1. **Cold Start**: First request may take 2-5 minutes (model loading)
2. **Free Tier**: Limited requests/month, may queue during high traffic
3. **Pro Tip**: Get a HuggingFace Pro account for faster/unlimited access

---

## 🔧 Troubleshooting

### "Model is loading"
- Normal on first request
- Wait 2-5 minutes and retry

### "Rate limit exceeded"
- HuggingFace free tier limit reached
- Wait an hour or upgrade to Pro

### Build fails on Streamlit Cloud
- Make sure you renamed `requirements_cloud.txt` to `requirements.txt`
- Remove any PyTorch/diffusers imports from requirements

---

## 📂 Files to Upload

| File | Upload? | Notes |
|------|---------|-------|
| `app.py` | ✅ Yes | Main app |
| `requirements.txt` | ✅ Yes | Use cloud version! |
| `models/` | ✅ Yes | All .py files |
| `utils/` | ✅ Yes | All .py files |
| `.streamlit/config.toml` | ✅ Yes | Theme settings |
| `.gitignore` | ✅ Yes | |

