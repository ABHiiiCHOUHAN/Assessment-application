# Security Policy

## Supported Versions

Please use the following table to track which versions of your app are currently supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Crucial Data / Secrets Management

> [!WARNING]
> **DO NOT** store actual passwords, API keys, or sensitive credentials in this file, as this file may be committed to version control. Use a `.env` file for local development and keep it out of source control (add `.env` to your `.gitignore`).

**Important Security Notes:**
- Store API keys (like Gemini, OpenAI, etc.) in `.env` and load them via environment variables.
- Ensure your Streamlit app does not expose sensitive paths or files.
- If you deploy this app, use the platform's secrets management feature (e.g., Streamlit Secrets, AWS Secrets Manager, Vercel Environment Variables).

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please follow these steps:
1. Do not disclose the vulnerability publicly.
2. Report the vulnerability to the maintainer via email or a secure channel.
3. The team will review the issue and release a patch as quickly as possible.
