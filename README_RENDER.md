# Backend Deployment on Render - Quick Reference

## Environment Variables Required

Set these in Render dashboard → Environment tab:

```
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_SECRET=your_paypal_secret
PAYPAL_ENVIRONMENT=production
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
CORS_ORIGINS=https://your-frontend.vercel.app
ENVIRONMENT=production
```

**Note**: `PORT` is automatically set by Render - don't add it manually.

## Service Configuration

- **Root Directory**: `backend`
- **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/health`

## Quick Deploy Steps

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect GitHub repository
4. Set Root Directory to `backend`
5. Copy build/start commands above
6. Add environment variables
7. Deploy!

## Verify Deployment

Visit: `https://your-service.onrender.com/health`

Should return:
```json
{
  "status": "healthy",
  "timestamp": "...",
  "environment": "production"
}
```

## Full Documentation

See `RENDER_DEPLOYMENT.md` for complete deployment guide.

