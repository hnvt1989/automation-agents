# Vercel Deployment Guide

This guide walks you through deploying the automation agents application to Vercel.

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Supabase Project**: Set up your Supabase database and vector store
3. **GitHub Repository**: Your code should be pushed to GitHub

## Step 1: Prepare Your Environment Variables

1. Copy the production environment template:
   ```bash
   cp .env.production.example .env.production
   ```

2. Fill in all required values in `.env.production`:
   - `SUPABASE_URL` and `SUPABASE_KEY` (from your Supabase project settings)
   - `JWT_SECRET` (generate a secure random string)
   - `OPENAI_API_KEY` (for LLM functionality)
   - `ALLOWED_ORIGINS` (your Vercel deployment URL)
   - Other API keys as needed

## Step 2: Set Up Supabase Database

1. Run the SQL schema files in your Supabase SQL editor:
   ```sql
   -- Run these files in order:
   scripts/create_user_table.sql
   scripts/create_user_settings_table.sql
   scripts/migrate_documents_to_supabase.py (Python migration script)
   ```

2. Enable Row Level Security (RLS) on all tables
3. Set up authentication policies as needed

## Step 3: Deploy to Vercel

### Option A: Deploy via Vercel CLI

1. Install Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. Login to Vercel:
   ```bash
   vercel login
   ```

3. Deploy from your project directory:
   ```bash
   vercel
   ```

4. Follow the prompts:
   - Link to existing project or create new one
   - Set build settings (should auto-detect from `vercel.json`)

### Option B: Deploy via Vercel Dashboard

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Click "New Project"
3. Import your GitHub repository
4. Vercel should auto-detect the configuration from `vercel.json`
5. Click "Deploy"

## Step 4: Configure Environment Variables in Vercel

1. Go to your project settings in Vercel dashboard
2. Navigate to "Environment Variables"
3. Add all variables from your `.env.production` file:

   **Required Variables:**
   - `SUPABASE_URL`
   - `SUPABASE_KEY` 
   - `JWT_SECRET`
   - `OPENAI_API_KEY`
   - `ALLOWED_ORIGINS`

   **Optional Variables:**
   - `BRAVE_API_KEY`
   - `GITHUB_TOKEN`
   - `SLACK_BOT_TOKEN`
   - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`

4. Save and redeploy if needed

## Step 5: Update CORS Settings

1. After deployment, note your Vercel URL (e.g., `https://your-app.vercel.app`)
2. Update the `ALLOWED_ORIGINS` environment variable in Vercel:
   ```
   ALLOWED_ORIGINS=https://your-app.vercel.app
   ```
3. If you have a custom domain, add it to the CORS origins:
   ```
   ALLOWED_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
   ```

## Step 6: Test Your Deployment

1. Visit your Vercel URL
2. Test the authentication system:
   - Register a new user
   - Login with credentials
3. Test core functionality:
   - Upload documents
   - Use the chat interface
   - Verify user settings work

## Architecture Notes

- **Frontend**: Single HTML file with inline React served as static content
- **Backend**: FastAPI application running as serverless functions
- **Database**: Supabase (PostgreSQL with vector extensions)
- **Authentication**: JWT tokens with custom user management
- **File Storage**: Supabase storage for documents and embeddings

## Troubleshooting

### Common Issues

1. **500 Internal Server Error**
   - Check Vercel function logs in dashboard
   - Verify all environment variables are set correctly
   - Ensure Supabase credentials are valid

2. **CORS Errors**
   - Update `ALLOWED_ORIGINS` to include your Vercel domain
   - Ensure the environment variable format is correct (comma-separated)

3. **Database Connection Errors**
   - Verify Supabase URL and key
   - Check if database tables exist
   - Ensure RLS policies allow access

4. **Authentication Issues**
   - Generate a new JWT_SECRET if needed
   - Verify user table exists in Supabase
   - Check if user registration is working

### Monitoring

- Use Vercel's function logs for debugging
- Monitor Supabase logs for database issues
- Set up alerts for error rates in production

## Security Considerations

1. **Environment Variables**: Never commit secrets to git
2. **CORS**: Restrict origins to your actual domains
3. **JWT Secret**: Use a strong, unique secret for production
4. **Supabase RLS**: Enable and configure Row Level Security
5. **API Rate Limiting**: Consider implementing rate limiting for production

## Performance Optimization

1. **Function Memory**: Increase memory allocation in `vercel.json` if needed
2. **Cold Starts**: Consider using Vercel Pro for reduced cold start times
3. **Caching**: Implement caching for frequently accessed data
4. **Database Indexing**: Ensure proper indexes in Supabase

## Maintenance

1. **Backups**: Set up automated Supabase backups
2. **Updates**: Regularly update dependencies
3. **Monitoring**: Set up uptime monitoring
4. **Logs**: Monitor function logs for errors