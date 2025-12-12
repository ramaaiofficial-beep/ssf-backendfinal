# Backend Setup Instructions

## ⚠️ **IMPORTANT: Fix PayPal Configuration Error**

The error you're seeing means the backend doesn't have PayPal credentials configured.

## 🚀 **Quick Fix Steps**

### Step 1: Create `.env` file in `backend` directory

Create a file named `.env` in the `backend` folder with the following content:

```env
# PayPal Configuration
PAYPAL_CLIENT_ID=your_paypal_client_id_here
PAYPAL_SECRET=your_paypal_secret_key_here
PAYPAL_ENVIRONMENT=sandbox

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Server Configuration
PORT=8000
```

### Step 2: Get PayPal Credentials

1. Go to https://developer.paypal.com
2. Log in with your PayPal account
3. Navigate to **"My Apps & Credentials"**
4. Click **"Create App"** (or select an existing app)
5. For testing, make sure you're in **Sandbox** mode
6. Copy the **Client ID** → Replace `your_paypal_client_id_here` in `.env`
7. Click **"Show"** next to Secret and copy it → Replace `your_paypal_secret_key_here` in `.env`

**Important:** 
- For testing, use **Sandbox** credentials
- For production, use **Live** credentials and set `PAYPAL_ENVIRONMENT=production`

### Step 3: Get Supabase Credentials

1. Go to your Supabase project dashboard
2. Navigate to **Project Settings** → **API**
3. Copy **Project URL** → Replace `https://your-project.supabase.co` in `.env`
4. Copy **service_role** key (not the anon key) → Replace `your_service_role_key_here` in `.env`

### Step 4: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 5: Start the Backend Server

```bash
# Make sure you're in the backend directory
cd backend

# Start the server
python main.py

# Or use uvicorn directly:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 6: Verify Backend is Running

Open your browser and visit: `http://localhost:8000/health`

You should see:
```json
{
  "status": "healthy",
  "timestamp": "...",
  "environment": "sandbox"
}
```

## 🔍 **Troubleshooting**

### Error: "PayPal credentials not configured"

**Cause:** The `.env` file is missing or doesn't have the correct variable names.

**Solution:**
1. Make sure `.env` file exists in the `backend` directory
2. Check that variable names are exactly:
   - `PAYPAL_CLIENT_ID` (not `VITE_PAYPAL_CLIENT_ID`)
   - `PAYPAL_SECRET` (not `PAYPAL_CLIENT_SECRET`)
3. Make sure there are no extra spaces or quotes around the values
4. Restart the backend server after creating/editing `.env`

### Error: "Module not found"

**Solution:** Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

### Backend not starting

**Check:**
1. Python version: `python --version` (needs 3.8+)
2. Port 8000 is available (or change `PORT` in `.env`)
3. All dependencies are installed

## 📝 **File Structure**

After setup, your `backend` directory should have:
```
backend/
  ├── .env              ← Create this file with your credentials
  ├── main.py           ← Backend server code
  ├── requirements.txt  ← Python dependencies
  ├── payment_errors.log ← Error logs (auto-generated)
  └── README.md         ← Documentation
```

## ✅ **After Setup**

Once the backend is running with credentials configured:
1. The frontend will be able to capture PayPal payments
2. Payment errors will be logged to `payment_errors.log`
3. You can check the health endpoint at `http://localhost:8000/health`

## 🔒 **Security Notes**

- ✅ `.env` is gitignored - your credentials won't be committed
- ❌ Never share your `PAYPAL_SECRET` or `SUPABASE_SERVICE_ROLE_KEY`
- ✅ Use `sandbox` for testing, `production` for live payments

