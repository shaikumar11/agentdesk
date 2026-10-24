# Rate limits

## Limits by plan
The Starter plan allows 60 requests per minute. The Growth plan allows 600 requests per minute. The Enterprise plan allows 6000 requests per minute and supports custom limits.

## Handling limit errors
When a limit is exceeded the API returns HTTP 429 with a Retry-After header. Clients should wait for the number of seconds in Retry-After and then retry with exponential backoff. Bulk endpoints count each item as one request.
