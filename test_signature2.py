#!/usr/bin/env python3
"""
Comprehensive test for MEXC API signature
"""
import hmac
import hashlib
import time

# Test parameters
api_key = "test_api_key"
secret_key = "test_secret_key"
timestamp = 1644489390087

# Test case from MEXC documentation
params = {
    'symbol': 'BTCUSDT',
    'side': 'BUY',
    'type': 'LIMIT',
    'quantity': '1',
    'price': '11',
    'recvWindow': '5000',
    'timestamp': str(timestamp)
}

# Create query string (sorted)
query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
print(f"Query string: {query_string}")

# Generate signature
signature = hmac.new(
    secret_key.encode('utf-8'),
    query_string.encode('utf-8'),
    hashlib.sha256
).hexdigest()

print(f"Generated signature: {signature}")
print(f"Expected from docs: fd3e4e8543c5188531eb7279d68ae7d26a573d0fc5ab0d18eb692451654d837a")
print(f"Match: {signature == 'fd3e4e8543c5188531eb7279d68ae7d26a573d0fc5ab0d18eb692451654d837a'}")

# Now test with actual secret key from docs
actual_secret = "45d0b3c26f2644f19bfb98b07741b2f5"
signature2 = hmac.new(
    actual_secret.encode('utf-8'),
    query_string.encode('utf-8'),
    hashlib.sha256
).hexdigest()

print(f"\nWith actual secret from docs:")
print(f"Generated signature: {signature2}")
print(f"Expected from docs: fd3e4e8543c5188531eb7279d68ae7d26a573d0fc5ab0d18eb692451654d837a")
print(f"Match: {signature2 == 'fd3e4e8543c5188531eb7279d68ae7d26a573d0fc5ab0d18eb692451654d837a'}")
