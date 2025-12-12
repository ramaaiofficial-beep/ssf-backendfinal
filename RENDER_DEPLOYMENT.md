# Render Deployment Guide for Backend

## Quick Start

### 1. Create New Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select the repository containing this backend

### 2. Configure Service Settings

**Basic Settings:**
- **Name**: `shree-samrajya-backend` (or your preferred name)
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main` (or your production branch)

**Build & Deploy:**
- **Root Directory**: `backend`
- **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Health Check:**
- **Health Check Path**: `/health`

### 3. Set Environment Variables

In Render dashboard, go to **Environment** tab and add:

#### Required Variables:
```
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_SECRET=your_paypal_secret
PAYPAL_ENVIRONMENT=production
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
CORS_ORIGINS=https://your-frontend.vercel.app,https://www.yourdomain.com
ENVIRONMENT=production
```

**Note**: Render automatically sets `PORT` - don't set it manually.

#### Variable Descriptions:

| Variable | Description | Required |
|----------|-------------|----------|
| `PAYPAL_CLIENT_ID` | PayPal Client ID from PayPal Developer Dashboard | Yes |
| `PAYPAL_SECRET` | PayPal Secret Key from PayPal Developer Dashboard | Yes |
| `PAYPAL_ENVIRONMENT` | `production` for live payments, `sandbox` for testing | Yes |
| `SUPABASE_URL` | Your Supabase project URL | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (not anon key) | Yes |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend URLs | Yes |
| `ENVIRONMENT` | Set to `production` | Yes |

### 4. Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Install dependencies
   - Build the service
   - Start the server
3. Monitor the logs for any errors

### 5. Verify Deployment

1. Check the service URL (e.g., `https://shree-samrajya-backend.onrender.com`)
2. Visit `/health` endpoint: `https://your-service.onrender.com/health`
3. You should see:
   ```json
   {
     "status": "healthy",
     "timestamp": "2024-...",
     "environment": "production"
   }
   ```

## Using render.yaml (Infrastructure as Code)

If you prefer to use `render.yaml`:

1. The `render.yaml` file is already configured in the root directory
2. When you connect your repository, Render will detect it
3. You still need to set environment variables in the Render dashboard
4. Render will use the configuration from `render.yaml`

## Post-Deployment Configuration

### 1. Update CORS Settings

After deployment, update `CORS_ORIGINS` with your actual frontend URL:
```
CORS_ORIGINS=https://your-app.vercel.app,https://www.yourdomain.com
```

### 2. Update Frontend API URL

In your frontend (Vercel), update the API base URL to point to your Render backend:
```
VITE_API_BASE_URL=https://your-backend.onrender.com
```

Or update the PayPal capture service to use the Render URL directly.

### 3. Update PayPal Redirect URLs

In PayPal Developer Dashboard:
1. Go to your app settings
2. Add your Render backend URL to allowed redirect URLs:
   ```
   https://your-backend.onrender.com/api/paypal/capture
   ```

## Monitoring

### View Logs
- Go to your service in Render dashboard
- Click **"Logs"** tab
- View real-time logs and errors

### Health Checks
- Render automatically checks `/health` endpoint
- Service will restart if health check fails
- Monitor health status in dashboard

### Metrics
- View request metrics in Render dashboard
- Monitor response times
- Check error rates

## Troubleshooting

### Service Won't Start

**Check logs for:**
- Missing environment variables
- Import errors
- Port binding issues

**Common fixes:**
- Verify all environment variables are set
- Check `requirements.txt` has all dependencies
- Ensure `startCommand` uses `$PORT` (not hardcoded port)

### Health Check Failing

**Verify:**
- `/health` endpoint is accessible
- Service is responding to requests
- No errors in logs

### CORS Errors

**Fix:**
- Update `CORS_ORIGINS` with exact frontend URL
- Include protocol (`https://`)
- No trailing slashes
- Comma-separated for multiple origins

### PayPal Errors

**Check:**
- `PAYPAL_CLIENT_ID` and `PAYPAL_SECRET` are correct
- `PAYPAL_ENVIRONMENT` matches your credentials (production vs sandbox)
- PayPal app is configured correctly

### Database Errors

**Verify:**
- `SUPABASE_URL` is correct
- `SUPABASE_SERVICE_ROLE_KEY` is the service role key (not anon key)
- Supabase project is active
- Database tables exist

## Scaling

### Free Tier Limitations
- Service spins down after 15 minutes of inactivity
- First request after spin-down may be slow (cold start)
- Consider upgrading for production use

### Upgrade Options
- **Starter Plan**: $7/month - Always on, better performance
- **Standard Plan**: $25/month - Better for production workloads

## Security Best Practices

1. ✅ Never commit `.env` files
2. ✅ Use service role key (not anon key) for backend
3. ✅ Set `CORS_ORIGINS` to specific domains (not `*`)
4. ✅ Use `PAYPAL_ENVIRONMENT=production` for live payments
5. ✅ Regularly rotate secrets
6. ✅ Monitor logs for suspicious activity

## Support

- Render Documentation: https://render.com/docs
- Render Support: https://render.com/support
- Check service logs for detailed error messages

