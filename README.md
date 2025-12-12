# FastAPI Backend for PayPal Payment Processing

Backend API for Shree Samrajya Foundation - PayPal payment processing with Supabase integration.

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file with:

```env
# PayPal Configuration
PAYPAL_CLIENT_ID=your_paypal_client_id_here
PAYPAL_SECRET=your_paypal_secret_key_here
PAYPAL_ENVIRONMENT=production

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Server Configuration
PORT=8000

# CORS Configuration
CORS_ORIGINS=https://your-frontend.vercel.app

# Environment
ENVIRONMENT=production
```

### 3. Start the Backend Server

```bash
# Development
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 4. Verify It's Working

Visit `http://localhost:8000/health` in your browser. You should see:

```json
{
  "status": "healthy",
  "timestamp": "...",
  "environment": "production"
}
```

## 📚 Documentation

- **Render Deployment**: See `RENDER_DEPLOYMENT.md` for complete guide
- **Quick Render Guide**: See `README_RENDER.md`
- **Setup Instructions**: See `SETUP.md`
- **Database Migrations**: See `DATABASE_MIGRATION.md`

## 🚀 Render Deployment

This backend is configured for Render deployment. See `RENDER_DEPLOYMENT.md` for detailed instructions.

**Quick Deploy:**
1. Connect repository to Render
2. Set environment variables
3. Deploy!

The `render.yaml` file is already configured.

## 🔍 API Endpoints

- `GET /health` - Health check endpoint
- `GET /` - Root endpoint
- `POST /api/paypal/capture-payment` - Capture PayPal payment

## 📝 Notes

- The `.env` file is gitignored and won't be committed
- Never share your `PAYPAL_SECRET` or `SUPABASE_SERVICE_ROLE_KEY`
- Use `sandbox` environment for testing
- Switch to `production` only when ready for live payments
