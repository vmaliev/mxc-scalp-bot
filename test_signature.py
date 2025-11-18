#!/usr/bin/env python3
"""
Test script to verify MXC API signature generation
"""
import hmac
import hashlib
import time

# Test with example from MXC documentation
secret_key = "45d0b3c26f2644f19bfb98b07741b2f5"
query_string = "symbol=BTCUSDT&side=BUY&type=LIMIT&quantity=1&price=11&recvWindow=5000&timestamp=1644489390087"

signature = hmac.new(
    secret_key.encode('utf-8'),
    query_string.encode('utf-8'),
    hashlib.sha256
).hexdigest()

print(f"Query string: {query_string}")
print(f"Expected signature: 323c96ab85a745712e95e63cad28903dd8292e4a905e99c4ee3932023843a117")
print(f"Generated signature: {signature}")
print(f"Match: {signature == '323c96ab85a745712e95e63cad28903dd8292e4a905e99c4ee3932023843a117'}")

# Test with current timestamp
timestamp = int(time.time() * 1000)
test_query = f"timestamp={timestamp}"
test_sig = hmac.new(
    secret_key.encode('utf-8'),
    test_query.encode('utf-8'),
    hashlib.sha256
).hexdigest()

print(f"\nTest query: {test_query}")
print(f"Test signature: {test_sig}")
