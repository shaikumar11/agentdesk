# Webhooks

## Delivery
CloudDesk sends webhook events as HTTP POST requests with a JSON body. Your endpoint must reply with a 2xx status within 10 seconds. Failed deliveries are retried 5 times over 24 hours with increasing delays.

## Signature verification
Each webhook includes an X-CloudDesk-Signature header. It is an HMAC SHA256 of the raw request body using your webhook secret. Always verify the signature before processing an event.

## Event types
Supported events include ticket.created, ticket.updated, ticket.closed and user.invited.
