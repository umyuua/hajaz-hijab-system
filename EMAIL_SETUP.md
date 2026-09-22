# Real email delivery

For a persistent local Gmail setup, run `python manage.py configure_email --skip-checks` in the VS Code terminal. Enter the sender Gmail address, its Google App Password, and your website address. The password input is hidden. The command checks SMTP authentication without sending a message and saves credentials in the Git-ignored `email_config.local.json`. Restart the server afterward. Do not share that local file. The saved local configuration takes priority over environment variables.

Set these environment variables before starting Django (restart the server after changes):

```powershell
$env:EMAIL_HOST_USER = "your-sender@gmail.com"
$env:EMAIL_HOST_PASSWORD = "your-google-app-password"
$env:PUBLIC_BASE_URL = "https://your-store-domain.com"
```

For Gmail, enable two-step verification on the sender account and create a Google App Password. Use the app password, not the normal account password. Never commit credentials to Git. These PowerShell settings apply to the current terminal session; configure them in your hosting environment for deployment without the local configuration file.

Other SMTP providers can use EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_USE_SSL, and DEFAULT_FROM_EMAIL. TLS defaults to true, SSL to false; do not enable both.

PUBLIC_BASE_URL must be the address customers can reach. For local testing on this computer, use http://127.0.0.1:8000. Without a configured base URL, links use the incoming request's address.

Register using an inbox you own. Confirm the email arrives, open the link, and log in. Before verification, login is blocked. Use the login page to resend lost or expired links. Existing payment and order notifications also send an email after their database transaction commits. A notification delivery failure is logged and does not undo the order update; automatic retries are not configured.

