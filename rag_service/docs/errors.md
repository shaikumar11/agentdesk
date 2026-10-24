# Error codes

## Common errors
HTTP 400 means the request body failed validation. HTTP 401 means the API key is missing or invalid. HTTP 403 means the key does not have permission for the resource. HTTP 404 means the resource does not exist. HTTP 409 means a conflict, for example a duplicate idempotency key. HTTP 429 means the rate limit was exceeded. HTTP 500 and 503 mean a server problem, and the request is safe to retry.

## Request ids
Every response includes an X-Request-Id header. Include this id when you contact support so the issue can be traced in the logs.
