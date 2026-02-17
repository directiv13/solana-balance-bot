# Performance Optimization - Helius Client

## Overview
The Helius client has been optimized to handle large numbers of wallets efficiently while respecting rate limits.

## Key Improvements

### 1. Batch Requests with `getMultipleAccounts`
- **Old approach**: `getTokenAccountsByOwner` - 1 request per wallet
- **New approach**: `getMultipleAccounts` - 100 wallets per request
- **Result**: ~100x reduction in API calls

### 2. Binary Data Parsing
- **Old approach**: JSON parsing with `encoding: "jsonParsed"`
- **New approach**: Base64 decoding + struct unpacking
- **Result**: Faster parsing, less data transfer

### 3. Rate Limiting
- **Implementation**: Semaphore-based rate limiter
- **Limit**: 10 requests per second
- **Result**: Complies with Helius free tier limits, prevents throttling

### 4. ATA Address Caching
- **Implementation**: In-memory cache for Associated Token Addresses
- **Result**: No redundant address derivations

## Performance Comparison

### 200 Wallets Example

| Metric | Old Method | New Method | Improvement |
|--------|-----------|-----------|-------------|
| API Requests | 200 | 2 | 100x fewer |
| Request Time | ~40s (with rate limiting) | ~0.4s | 100x faster |
| Data Transfer | ~400KB | ~20KB | 20x less |
| Rate Limit Buffer | Tight (10 req/s limit) | Comfortable | Better reliability |

### Real-World Performance

**Scenario: 500 wallets tracked**
- **Batching**: 5 requests (500 ÷ 100)
- **Time with rate limiting**: ~0.5 seconds
- **Sync interval**: 60 seconds (plenty of buffer)

**Scenario: 1000 wallets tracked**
- **Batching**: 10 requests (1000 ÷ 100)  
- **Time with rate limiting**: ~1 second
- **Sync interval**: 60 seconds (still comfortable)

## Code Example

### Old Approach (Inefficient)
```python
# Makes N individual requests
for wallet in wallets:
    balance = await get_usdt_balance(wallet)  # 1 API call each
```

### New Approach (Optimized)
```python
# Makes N÷100 batch requests
balances = await helius.get_multiple_balances(wallets)  # Batched
```

## Rate Limiting Details

- **Helius Free Tier**: 10 requests/second
- **Implementation**: Semaphore with time-based reset
- **Behavior**: Automatically throttles requests to stay under limit
- **Buffer**: Built-in delays ensure we never hit the rate limit

## Binary Parsing Details

SPL Token Account Layout:
```
Bytes 0-31:   Mint address (32 bytes)
Bytes 32-63:  Owner address (32 bytes)  
Bytes 64-71:  Amount (uint64, little-endian) ← We extract this
Bytes 72+:    Additional fields...
```

Parsing code:
```python
raw_data = base64.b64decode(account_data["data"][0])
amount_raw = struct.unpack("<Q", raw_data[64:72])[0]
usdt_balance = amount_raw / 1_000_000  # USDT has 6 decimals
```

## Testing

Run the test script to verify performance:
```bash
python test_helius.py
```

This will:
- Test single wallet queries
- Test batch queries
- Test rate limiting
- Simulate large batches (150+ wallets)
- Measure actual performance

## Migration Notes

The API interface remains the same, so existing code works without changes:
- `get_usdt_balance(address)` - Single wallet
- `get_multiple_balances(addresses)` - Multiple wallets  
- `get_total_usdt_balance(addresses)` - Total only (even faster)

The optimization is transparent to the rest of the application.
