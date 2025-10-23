# Email Whitelist Setup Guide

This guide explains how to restrict access to your Canvas TA Dashboard to specific email addresses.

## Overview

The email whitelist uses a Cognito pre-signup Lambda trigger to validate email addresses before allowing account creation. Only emails on the approved list can create accounts.

## Initial Setup

Run the setup script to configure the whitelist for the first time:

```bash
./setup_email_whitelist.sh
```

When prompted, enter comma-separated email addresses:
```
admin@base2ml.com,ta1@gatech.edu,ta2@gatech.edu,ta3@gatech.edu
```

This will:
1. Create a Lambda function to validate emails
2. Configure Cognito to use the Lambda trigger
3. Set up the initial whitelist

## Managing the Whitelist

Use the `manage_whitelist.sh` script for ongoing management:

### View Current Whitelist
```bash
./manage_whitelist.sh list
```

### Add an Email
```bash
./manage_whitelist.sh add newta@gatech.edu
```

### Remove an Email
```bash
./manage_whitelist.sh remove oldta@gatech.edu
```

### Replace Entire Whitelist
```bash
./manage_whitelist.sh set admin@base2ml.com,ta1@gatech.edu,ta2@gatech.edu
```

## How It Works

1. **User attempts signup** → Enters email at https://cda-ta-dashboard.base2ml.com
2. **Cognito triggers Lambda** → Pre-signup Lambda function is invoked
3. **Email validation** → Lambda checks if email is in whitelist
4. **Result:**
   - ✅ **Email allowed** → Account created and auto-confirmed
   - ❌ **Email not allowed** → Signup rejected with error message

## User Experience

**Allowed users:**
- Enter their email
- Account is created automatically
- Email is auto-verified (no confirmation needed)
- Can immediately sign in

**Blocked users:**
- See error: "Email xxx@yyy.com is not authorized to create an account. Please contact the administrator."
- Cannot proceed with signup

## Security Notes

- Emails are case-insensitive (Admin@Example.com = admin@example.com)
- Only exact matches are allowed (no wildcards or patterns)
- Changes take effect immediately
- Existing users are not affected by whitelist changes

## Best Practices

1. **Initial Setup:** Add all TAs and administrators before going live
2. **Onboarding:** Add new TAs before they attempt signup
3. **Offboarding:** Remove TAs when they leave to prevent future access
4. **Regular Audits:** Periodically review the whitelist with `./manage_whitelist.sh list`

## Troubleshooting

### User can't sign up
```bash
# Check if their email is on the list
./manage_whitelist.sh list

# Add their email if missing
./manage_whitelist.sh add their-email@gatech.edu
```

### View Lambda logs
```bash
aws logs tail /aws/lambda/canvas-ta-dashboard-prod-presignup --follow
```

### Update whitelist directly in AWS Console
1. Go to Lambda → `canvas-ta-dashboard-prod-presignup`
2. Configuration → Environment variables
3. Edit `ALLOWED_EMAILS` variable
4. Save

## Example Workflow

**Initial setup for course with 5 TAs:**
```bash
./setup_email_whitelist.sh
# Enter: admin@base2ml.com,ta1@gatech.edu,ta2@gatech.edu,ta3@gatech.edu,ta4@gatech.edu,ta5@gatech.edu
```

**New TA joins mid-semester:**
```bash
./manage_whitelist.sh add ta6@gatech.edu
```

**TA graduates and leaves:**
```bash
./manage_whitelist.sh remove ta1@gatech.edu
```

**Verify current list:**
```bash
./manage_whitelist.sh list
```

## Files

- `lambda/cognito_presignup.py` - Lambda function code
- `setup_email_whitelist.sh` - Initial setup script
- `manage_whitelist.sh` - Whitelist management CLI
- `EMAIL_WHITELIST_SETUP.md` - This guide

## Additional Resources

- [Cognito Lambda Triggers](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools-working-with-aws-lambda-triggers.html)
- [Pre-Signup Lambda Trigger](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-sign-up.html)
