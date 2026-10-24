# Authentication

## API keys
Every request to the CloudDesk API must send an API key in the X-API-Key header. Keys are created in the dashboard under Settings and Developer. A key can be rotated at any time, and the old key stops working 24 hours after rotation.

## OAuth 2.0
For apps that act on behalf of users, CloudDesk supports the OAuth 2.0 authorization code flow. Access tokens expire after 60 minutes. Refresh tokens expire after 30 days of inactivity.

## Single sign on
SSO through SAML 2.0 is available on the Enterprise plan only. An admin uploads the identity provider metadata in Settings and Security, then enforces SSO for all members.
