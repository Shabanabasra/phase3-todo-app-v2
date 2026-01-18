# Deployment Guide for Phase-3 AI Todo App

## Overview
This guide explains how to deploy the Phase-3 AI Todo application with FastAPI backend and Next.js frontend.

## Architecture
- **Frontend**: Next.js 16+ application hosted on Vercel
- **Backend**: FastAPI application (can be hosted on Railway, Render, or AWS)
- **Database**: Neon PostgreSQL Serverless
- **Vector DB**: Qdrant Cloud
- **AI Services**: Cohere API, Context7 API

## Deployment Steps

### 1. Deploy Backend (Choose one platform)

#### Option A: Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link project
railway link

# Set environment variables
railway vars set DATABASE_URL="your_neon_db_url"
railway vars set COHERE_API_KEY="your_cohere_key"
railway vars set QDRANT_URL="your_qdrant_url"
railway vars set QDRANT_API_KEY="your_qdrant_key"
railway vars set CONTEXT7_API_KEY="your_context7_key"

# Deploy
railway up
```

#### Option B: Render
1. Create a new Web Service on Render
2. Connect to your GitHub repository
3. Set runtime to "Python"
4. Add build command: `pip install -r requirements.txt`
5. Add start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables in Render dashboard

### 2. Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and create an account
2. Install Vercel CLI: `npm install -g vercel`
3. Login: `vercel login`
4. Navigate to frontend directory: `cd frontend`
5. Deploy: `vercel --prod`

#### Environment Variables for Vercel:
```
NEXT_PUBLIC_API_URL=https://your-backend-url.com/api
NEXT_PUBLIC_BETTER_AUTH_URL=https://your-backend-url.com
BETTER_AUTH_SECRET=your-production-secret
```

### 3. Alternative: Full Stack on Railway/Render

For a simpler deployment, you can host both frontend and backend together:

1. Build the Next.js app: `cd frontend && npm run build`
2. Configure your backend to serve static files from the Next.js build
3. Deploy the combined application

## Environment Configuration

### Backend (.env)
```env
DATABASE_URL=postgresql://username:password@host:port/database
COHERE_API_KEY=your_cohere_api_key
QDRANT_URL=your_qdrant_cloud_url
QDRANT_API_KEY=your_qdrant_api_key
CONTEXT7_API_KEY=your_context7_api_key
BETTER_AUTH_SECRET=your_production_secret
PROJECT_NAME=Your Todo App Name
BETTER_AUTH_URL=https://your-frontend-url.vercel.app
```

### Frontend (.env.local for local, Vercel env for production)
```env
NEXT_PUBLIC_API_URL=https://your-backend-url.com/api
NEXT_PUBLIC_BETTER_AUTH_URL=https://your-backend-url.com
BETTER_AUTH_SECRET=your_secret
```

## Production Checklist

- [ ] Update API keys and secrets
- [ ] Enable SSL certificates
- [ ] Set up monitoring and logging
- [ ] Configure backup strategies
- [ ] Set up CI/CD pipeline
- [ ] Optimize database connections
- [ ] Configure rate limiting
- [ ] Set up error tracking

## Troubleshooting

### Common Issues:

1. **Database Connection Issues**:
   - Verify DATABASE_URL format
   - Check if Neon PostgreSQL is configured for serverless connections
   - Ensure SSL settings are correct

2. **API Keys Not Working**:
   - Regenerate API keys if they've expired
   - Check if API providers have rate limits

3. **Frontend Cannot Reach Backend**:
   - Verify CORS settings in FastAPI
   - Check if backend URL is correctly configured in frontend

4. **Deployment Failures**:
   - Check logs in your hosting platform
   - Verify all dependencies are correctly specified
   - Ensure environment variables are set

## Scaling Recommendations

- Use connection pooling for database connections
- Implement caching for frequently accessed data
- Use CDN for static assets
- Set up auto-scaling based on traffic
- Monitor resource usage and optimize accordingly