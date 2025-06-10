# TODO - Automation Agents

## Frontend/Backend Deployment Configuration Issues

### Current Problems
The current frontend and backend configuration is hardcoded for local development and will not work in production deployments without manual changes.

### Deployment Scenarios & Issues

#### Scenario 1: Same Domain Deployment
- Frontend: `https://myapp.com`
- Backend: `https://myapp.com/api`
- **Problem**: CONFIG points to localhost, CORS doesn't allow myapp.com

#### Scenario 2: Separate Domains
- Frontend: `https://frontend.myapp.com`
- Backend: `https://api.myapp.com`
- **Problem**: Both URL and CORS issues

#### Scenario 3: Cloud Deployment (AWS/Vercel/etc.)
- Frontend: `https://myapp.vercel.app`
- Backend: `https://mybackend.railway.app`
- **Problem**: Multiple hardcoded URLs need changing

### Required Fixes

#### 1. Frontend - Dynamic Configuration
- [ ] Replace hardcoded CONFIG object with environment detection
- [ ] Auto-detect protocol (http/https) and domain
- [ ] Support both same-domain and cross-domain deployments

#### 2. Backend - Environment-Based CORS
- [ ] Read CORS origins from environment variables
- [ ] Support multiple allowed origins
- [ ] Default to localhost for development

#### 3. Documentation
- [ ] Add deployment guide with configuration examples
- [ ] Document environment variables needed
- [ ] Add examples for common hosting providers

### Priority: High
This needs to be fixed before any production deployment.