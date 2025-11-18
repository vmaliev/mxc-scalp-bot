#!/usr/bin/env python3
"""
Test MEXC authentication using CCXT library
"""
import ccxt

# Initialize MEXC exchange
exchange = ccxt.mexc({
    'apiKey': 'test_key',
    'secret': 'test_secret',
    'enableRateLimit': True,
})

# Print the signature method
print("CCXT MEXC Exchange Info:")
print(f"Exchange ID: {exchange.id}")
print(f"Has: {exchange.has}")
print(f"\nAuth method: {exchange.sign.__doc__ if hasattr(exchange, 'sign') else 'N/A'}")

# Try to see the signature generation
import inspect
if hasattr(exchange, 'sign'):
    print(f"\nSign method source:")
    try:
        print(inspect.getsource(exchange.sign))
    except:
        print("Could not get source")

# Check the exchange class
print(f"\nExchange class: {exchange.__class__.__name__}")
print(f"Base classes: {[c.__name__ for c in exchange.__class__.__mro__]}")
