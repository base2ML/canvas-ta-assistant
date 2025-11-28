# Security Policy

## Overview

The CDA TA Dashboard handles sensitive educational data including student information, grades, and Canvas LMS credentials. This document outlines security best practices for development, deployment, and responsible disclosure.

## Credential Management

### Canvas API Tokens

**Never commit Canvas API tokens to version control.**

Canvas API tokens provide access to sensitive student data and should be treated as highly confidential.

#### Generating Canvas API Tokens

1. Log into your Canvas instance (e.g., `https://your-school.instructure.com`)
2. Navigate to **Account → Settings → Approved Integrations**
3. Click **+ New Access Token**
4. Set a descriptive purpose (e.g., "TA Dashboard Development")
5. Set an expiration date (recommended: 90 days for development, 30 days for production)
6. Copy the token immediately (it will only be shown once)

#### Token Storage

**Development:**
- Store tokens in `.env` files (already gitignored)
- Never share `.env` files via email, chat, or cloud storage
- Use `.env.example` as a template for team members

**Production:**
- Use environment variables via your hosting platform
- Enable token rotation (regenerate every 30-90 days)
- Use scoped tokens when Canvas supports it
- Never log API tokens in application logs

#### Token Regeneration

Before making this repository public or if tokens are compromised:

1. **Immediately regenerate** all Canvas API tokens
2. Update environment variables in production
3. Update local `.env` files for development
4. Verify old tokens are revoked in Canvas settings

### Environment Variables

Required environment variables are documented in `.env.example` files:

**Backend** (Terraform/Lambda environment variables):
```bash
CANVAS_API_TOKEN=your-canvas-api-token-here
CANVAS_API_URL=https://your-school.instructure.com
CANVAS_COURSE_ID=your-course-id
JWT_SECRET_KEY=your-production-secret
```

**Frontend** (`canvas-react/.env.example`):
```bash
VITE_CANVAS_API_URL=https://your-school.instructure.com
VITE_CANVAS_API_KEY=your-canvas-api-token-here
VITE_CANVAS_COURSE_ID=12345
VITE_BACKEND_URL=http://localhost:8000
```

## Production Deployment Security

### Critical Configuration Changes

Before deploying to production:

1. **Disable Debug Mode**
   ```bash
   # In Terraform variables or Lambda environment
   ENVIRONMENT=prod
   ```

2. **Configure CORS Properly**
   ```bash
   # Set specific allowed origins (not "*")
   CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

3. **Use HTTPS Only**
   - Enforce HTTPS for all API endpoints
   - Use SSL/TLS certificates (Let's Encrypt recommended)
   - Set `Secure` flag on cookies

4. **Enable Rate Limiting**
   - Implement rate limiting on API endpoints
   - Protect against brute force attacks
   - Consider Canvas API rate limits (1000 requests/hour typical)

### Security Checklist

- [ ] All API tokens regenerated and stored securely
- [ ] Debug mode disabled (`DEBUG=false`)
- [ ] CORS configured with specific domains (not `*`)
- [ ] HTTPS enabled and enforced
- [ ] Environment variables set via hosting platform (not hardcoded)
- [ ] Secrets never logged or exposed in error messages
- [ ] Pre-commit hooks installed (`pre-commit install`)
- [ ] Security scanning enabled in CI/CD pipeline
- [ ] Database credentials rotated (if applicable)
- [ ] Firewall rules configured to restrict access

## Data Privacy

### Student Data Handling

This application accesses student data from Canvas LMS:
- Student names and IDs
- Assignment submissions and grades
- Course enrollment information

**Compliance Requirements:**
- **FERPA**: Comply with Family Educational Rights and Privacy Act
- **GDPR**: If serving EU students, comply with data protection regulations
- **Institutional Policies**: Follow your institution's data handling policies

**Best Practices:**
- Minimize data retention (don't cache student data unnecessarily)
- Use short cache TTLs for sensitive data (see `config.py`)
- Never share screenshots or logs containing student names/IDs
- Anonymize data for debugging or development examples

## Development Security

### Pre-commit Hooks

Install pre-commit hooks to prevent accidental secret commits:

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install hooks in your local repository
pre-commit install

# Manually run on all files (optional)
pre-commit run --all-files
```

The `.pre-commit-config.yaml` includes:
- **detect-secrets**: Scans for API keys, tokens, passwords
- **check-added-large-files**: Prevents committing large files
- **trailing-whitespace**: Code quality checks
- **end-of-file-fixer**: Code quality checks

### Secret Scanning

GitHub Actions automatically scans for secrets on every push and pull request. See `.github/workflows/security.yml` for configuration.

If secrets are detected:
1. **Do not force push** to hide them (history is public)
2. **Immediately regenerate** the compromised credentials
3. **Contact repository admins** to purge from history if necessary
4. Use `git filter-repo` or BFG Repo Cleaner to remove from history

## Vulnerability Reporting

### Responsible Disclosure

If you discover a security vulnerability in this project:

1. **Do NOT** open a public GitHub issue
2. **Email** the maintainers directly at [your-security-email@example.com]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

### Response Timeline

- **24 hours**: Initial response acknowledging receipt
- **7 days**: Assessment and planned fix timeline
- **30 days**: Patch released (or timeline communicated)

### Security Updates

Monitor this repository for security updates:
- Watch for security advisories
- Update dependencies regularly
- Review `CHANGELOG.md` for security fixes

## Common Security Issues

### What NOT to do

❌ **Never commit**:
- `.env` files with real credentials
- Canvas API tokens in code or configuration
- Student names, IDs, or grades in examples
- Private keys or certificates
- Database credentials

❌ **Never share**:
- API tokens via email, Slack, or chat
- Production `.env` files
- Screenshots with student data
- Logs containing sensitive information

✅ **Always**:
- Use `.env.example` as templates
- Rotate credentials regularly
- Enable 2FA on Canvas and GitHub accounts
- Keep dependencies updated
- Review code before committing
- Use pre-commit hooks

## Additional Resources

- [Canvas API Security Best Practices](https://canvas.instructure.com/doc/api/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FERPA Guidelines](https://www2.ed.gov/policy/gen/guid/fpco/ferpa/index.html)
- [Git Secrets Management](https://docs.github.com/en/code-security/secret-scanning)

## Contact

For security concerns or questions:
- **Email**: [your-security-email@example.com]
- **GitHub Issues**: For non-security bugs only
- **Documentation**: See `README.md` and `AGENTS.md`

---

**Last Updated**: 2025-10-10
**Repository**: https://github.com/base2ML/cda-ta-dashboard
