# Cookie Storage System

This directory contains login session cookies for web scrapers that require authentication.

## How It Works

1. **Cookie Loading**: When a scraper starts, it attempts to load saved cookies from this directory
2. **Login Check**: If cookies exist, the scraper tries to use them to access protected pages
3. **Automatic Login**: If cookies are invalid/expired, the scraper performs a fresh login
4. **Cookie Saving**: After successful login, new cookies are saved for future use

## Supported Scrapers

- **Orgill** (`orgill_cookies.pkl`) - Requires login for product access
- **Pet Food Experts** (`petfoodex_cookies.pkl`) - Requires login for product access
- **Phillips** (`phillips_cookies.pkl`) - Requires login for product access

## Cookie Manager

Use the `cookie_manager.py` script to manage cookie files:

```bash
# List all cookie files
python cookies/cookie_manager.py list

# Show info about a specific site's cookies
python cookies/cookie_manager.py info orgill

# Clear cookies for a specific site
python cookies/cookie_manager.py clear orgill

# Clear all cookies
python cookies/cookie_manager.py clear
```

## Security Notes

- Cookie files contain sensitive session data
- Never commit cookie files to version control (they're in .gitignore)
- Cookies expire automatically and will be refreshed on next login
- If you suspect cookie compromise, clear them manually

## Troubleshooting

- **Login still required**: Cookies may have expired - they will be refreshed automatically
- **Login failures**: Check your .env file for correct credentials
- **Cookie corruption**: Clear cookies and try again
