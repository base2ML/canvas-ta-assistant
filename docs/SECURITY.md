# Security Policy

## Overview

The CDA TA Dashboard handles sensitive educational data including student information, grades, and Canvas LMS credentials. This document outlines security best practices for development and deployment.

## Credential Management

### Canvas API Tokens

**Never commit Canvas API tokens to version control.**

Canvas API tokens provide access to sensitive student data and should be treated as highly confidential.

#### Generating Canvas API Tokens

1. Log into your Canvas instance (e.g., `https://your-school.instructure.com`)
2. Navigate to **Account → Settings → Approved Integrations**
3. Click **+ New Access Token**
4. Set a descriptive purpose (e.g., "TA Dashboard")
5. Set an expiration date (recommended: 90 days)
6. Copy the token immediately (it will only be shown once)

#### Token Storage

- Store tokens in `.env` files (already gitignored)
- Never share `.env` files via email, chat, or cloud storage
- Use `.env.example` as a template
- Never log API tokens in application logs

#### Token Regeneration

If tokens are compromised:

1. **Immediately regenerate** your Canvas API token in Canvas settings
2. Update your local `.env` file with the new token
3. Restart Docker containers: `docker-compose down && docker-compose up -d`

### Environment Variables

Required environment variables in `.env`:

```bash
# Canvas API Configuration
CANVAS_API_URL=https://your-school.instructure.com
CANVAS_API_TOKEN=your-canvas-api-token-here
CANVAS_COURSE_ID=your-course-id  # Optional
```

## Deployment Security

### Single-User Design

This application is designed for local, single-user deployment:

- No authentication system (user has direct access)
- SQLite database stored on OneDrive/SharePoint for FERPA-compliant shared access
- Canvas API token stored in local `.env` file

### Data Storage

- **SQLite Database**: stored at the path configured by `DATA_PATH` (see `.env.example`)
  - Recommended: a OneDrive/SharePoint directory shared among TAs
  - Contains student names, emails, grades, submissions
  - Protected by OneDrive access controls and file system permissions
  - Not encrypted at rest
- **Environment File**: `.env`
  - Contains Canvas API token
  - Must never be committed to version control

### Security Checklist

- [ ] `.env` file is in `.gitignore` (default)
- [ ] `data/` directory is in `.gitignore` (default)
- [ ] Canvas API token has appropriate expiration date
- [ ] No sensitive data in screenshots or logs

## Data Privacy

### Student Data Handling

This application accesses student data from Canvas LMS:

- Student names and IDs
- Assignment submissions and grades
- Course enrollment information

**Compliance Requirements:**

- **FERPA**: Comply with Family Educational Rights and Privacy Act
- **Institutional Policies**: Follow your institution's data handling policies

**Best Practices:**

- Only access courses you are authorized to view
- Do not share screenshots containing student data
- Delete or archive the OneDrive database when no longer needed
- Handle student data according to your institution's guidelines

## What NOT to Commit

❌ **Never commit these files:**

- `.env` files with Canvas API tokens
- The OneDrive `DATA_PATH` directory containing the SQLite database
- Screenshots with student names, IDs, or grades
- Logs containing sensitive information

✅ **Safe to commit:**

- `.env.example` with placeholder values
- Documentation without real student data
- Code without hardcoded credentials

## File Security

### Gitignore Configuration

The following are already configured in `.gitignore`:

```
# Environment files
.env
.env.local
.env.*.local

# Local data directory fallback (not used when DATA_PATH points to OneDrive)
data/
!data/.gitkeep

# Logs
logs/
*.log
```

### Verifying Before Commit

Always check `git status` before committing:

```bash
# Check for accidentally staged sensitive files
git status

# If .env or data/ appears, unstage them
git reset HEAD .env
git reset HEAD data/
```

## Security Resources

- **Canvas API Docs**: https://canvas.instructure.com/doc/api/
- **FERPA Guidelines**: https://www2.ed.gov/policy/gen/guid/fpco/ferpa/index.html

## Contact

For security concerns or questions about data handling, contact your institution's IT security team.

---

**Last Updated**: 2025-01-31
