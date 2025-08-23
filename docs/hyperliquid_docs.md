# Notation

The current v0 API currently uses some nonstandard notation. Relevant standardization will be batched into a breaking v1 API change.

<table><thead><tr><th width="231.33333333333331">Abbreviation</th><th>Full name</th><th>Explanation</th></tr></thead><tbody><tr><td>Px</td><td>Price</td><td></td></tr><tr><td>Sz</td><td>Size</td><td>In units of coin, i.e. base currency</td></tr><tr><td>Szi</td><td>Signed size </td><td>Positive for long, negative for short</td></tr><tr><td>Ntl</td><td>Notional</td><td>USD amount, Px * Sz </td></tr><tr><td>Side</td><td>Side of trade or book</td><td>B = Bid = Buy, A = Ask = Short. Side is aggressing side for trades.</td></tr><tr><td>Asset</td><td>Asset</td><td>An integer representing the asset being traded. See below for explanation</td></tr><tr><td>Tif</td><td>Time in force</td><td>GTC = good until canceled, ALO = add liquidity only (post only), IOC = immediate or cancel</td></tr></tbody></table>

# Notation

The current v0 API currently uses some nonstandard notation. Relevant standardization will be batched into a breaking v1 API change.

<table><thead><tr><th width="231.33333333333331">Abbreviation</th><th>Full name</th><th>Explanation</th></tr></thead><tbody><tr><td>Px</td><td>Price</td><td></td></tr><tr><td>Sz</td><td>Size</td><td>In units of coin, i.e. base currency</td></tr><tr><td>Szi</td><td>Signed size </td><td>Positive for long, negative for short</td></tr><tr><td>Ntl</td><td>Notional</td><td>USD amount, Px * Sz </td></tr><tr><td>Side</td><td>Side of trade or book</td><td>B = Bid = Buy, A = Ask = Short. Side is aggressing side for trades.</td></tr><tr><td>Asset</td><td>Asset</td><td>An integer representing the asset being traded. See below for explanation</td></tr><tr><td>Tif</td><td>Time in force</td><td>GTC = good until canceled, ALO = add liquidity only (post only), IOC = immediate or cancel</td></tr></tbody></table>

# Tick and lot size

Both Price (px) and Size (sz) have a maximum number of decimals that are accepted.&#x20;

Prices can have up to 5 significant figures, but no more than `MAX_DECIMALS - szDecimals` decimal places where `MAX_DECIMALS` is 6 for perps and 8 for spot. Integer prices are always allowed, regardless of the number of significant figures. E.g. `123456` is a valid price even though `12345.6` is not.

Sizes are rounded to the `szDecimals` of that asset. For example, if `szDecimals = 3` then `1.001` is a valid size but `1.0001` is not.&#x20;

`szDecimals` for an asset is found in the meta response to the info endpoint

### Perp price examples

`1234.5` is valid but `1234.56` is not (too many significant figures)

`0.001234` is valid, but `0.0012345` is not (more than 6 decimal places)

If `szDecimals = 1` , `0.01234` is valid but `0.012345` is not (more than `6 - szDecimals` decimal places)

### Spot price examples

`0.0001234` is valid if `szDecimals` is 0 or 1, but not if `szDecimals` is greater than 2 (more than 8-2 decimal places).&#x20;

### Signing

Note that if implementing signing, trailing zeroes should be removed. See [Signing](signing) for more details.

# Nonces and API wallets

### Background&#x20;

A decentralized L1 must prevent replay attacks. When a user signs a USDC transfer transaction, the receiver cannot broadcast it multiple times to drain the sender's wallet. To solve this Ethereum stores a "nonce" for each address, which is a number that starts at 0. Each transaction must use exactly "nonce + 1" to be included.

### API wallets

These are also known as `agent wallets` in the docs. A master account can approve API wallets to sign on behalf of the master account or any of the sub-accounts.&#x20;

Note that API wallets are only used to sign. To query the account data associated with a master or sub-account, you must pass in the actual address of that account. A common pitfall is to use the agent wallet which leads to an empty result.

### API wallet pruning

API wallets and their associated nonce state may be pruned in the following cases:

1. The wallet is deregistered. This happens to an existing unnamed API Wallet when an ApproveAgent action is sent to register a new unnamed API Wallet. This also happens to an existing named API Wallet when an ApproveAgent action is sent with a matching name.
2. The wallet expires.
3. The account that registered the agent no longer has funds.

**Important:** for those using API wallets programmatically, it is **strongly** suggested to not reuse their addresses. Once an agent is deregistered, its used nonce state may be pruned. Generate a new agent wallet on future use to avoid unexpected behavior. For example, previously signed actions can be replayed once the nonce set is pruned.

### Hyperliquid nonces&#x20;

Ethereum's design does not work for an onchain order book. A market making strategy can send thousands of orders and cancels in a second. Requiring a precise ordering of inclusion on the blockchain will break any strategy.

On Hyperliquid, the 100 highest nonces are stored per address. Every new transaction must have nonce larger than the smallest nonce in this set and also never have been used before. Nonces are tracked per signer, which is the user address if signed with private key of the address, or the agent address if signed with an API wallet.&#x20;

Nonces must be within `(T - 2 days, T + 1 day)`, where `T` is the unix millisecond timestamp on the block of the transaction.

The following steps may help port over an automated strategy from a centralized exchange:

1. Use a API wallet per trading process. Note that nonces are stored per signer (i.e. private key), so separate subaccounts signed by the same API wallet will share the nonce tracker of the API wallet. It's recommended to use separate API wallets for different subaccounts.
2. In each trading process, have a task that periodically batches order and cancel requests every 0.1 seconds. It is recommended to batch IOC and GTC orders separately from ALO orders because ALO order-only batches are prioritized by the validators.
3. The trading logic tasks send orders and cancels to the batching task.
4. For each batch of orders or cancels, fetch and increment an atomic counter that ensures a unique nonce for the address. The atomic counter can be fast-forwarded to current unix milliseconds if needed.

This structure is robust to out-of-order transactions within 2 seconds, which should be sufficient for an automated strategy geographically near an API server.

### Suggestions for subaccount and vault users

Note that nonces are stored per signer, which is the address of the private key used to sign the transaction. Therefore, it's recommended that each trading process or frontend session use a separate private key for signing. In particular, a single API wallet signing for a user, vault, or subaccount all share the same nonce set.

If users want to use multiple subaccounts in parallel, it would easier to generate two separate API wallets under the master account, and use one API wallet for each subaccount. This avoids collisions between the nonce set used by each subaccount.

---
description: >-
  The info endpoint is used to fetch information about the exchange and specific
  users. The different request bodies result in different corresponding response
  body schemas.
---

# Info endpoint

### Pagination

Responses that take a time range will only return 500 elements or distinct blocks of data. To query larger ranges, use the last returned timestamp as the next `startTime` for pagination.

### Perpetuals vs Spot

The endpoints in this section as well as websocket subscriptions work for both Perpetuals and Spot. For perpetuals `coin` is the name returned in the `meta` response. For Spot, coin should be `PURR/USDC` for PURR, and `@{index}` e.g. `@1` for all other spot tokens where index is the index of the spot pair in the `universe` field of the `spotMeta` response. For example, the spot index for HYPE on mainnet is `@107` because the token index of HYPE is 150 and the spot pair `@107` has tokens `[150, 0]`. Note that some assets may be remapped on user interfaces. For example, `BTC/USDC` on app.hyperliquid.xyz corresponds to `UBTC/USDC` on mainnet HyperCore. The L1 name on the [token details page](https://app.hyperliquid.xyz/explorer/token/0x8f254b963e8468305d409b33aa137c67) can be used to detect remappings.

### User address

To query the account data associated with a master or sub-account, you must pass in the actual address of that account. A common pitfall is to use an agent wallet's address which leads to an empty result.

## Retrieve mids for all coins

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

Note that if the book is empty, the last trade price will be used as a fallback

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                                                                                            |
| -------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "allMids"                                                                                                                              |
| dex                                    | String | Perp dex name. Defaults to the empty string which represents the first perp dex. Spot mids are only included with the first perp dex.. |

{% tabs %}
{% tab title="200: OK Successful Response" %}
```json
{
    "APE": "4.33245",
    "ARB": "1.21695"
}
```
{% endtab %}
{% endtabs %}

## Retrieve a user's open orders

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

See a user's open orders

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                                                                                                  |
| -------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "openOrders"                                                                                                                                 |
| user<mark style="color:red;">\*</mark> | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000.                                                 |
| dex                                    | String | Perp dex name. Defaults to the empty string which represents the first perp dex. Spot open orders are only included with the first perp dex. |

{% tabs %}
{% tab title="200: OK Successful R" %}
```json
[
    {
        "coin": "BTC",
        "limitPx": "29792.0",
        "oid": 91490942,
        "side": "A",
        "sz": "0.0",
        "timestamp": 1681247412573
    }
]
```
{% endtab %}
{% endtabs %}

## Retrieve a user's open orders with additional frontend info

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                                                                                                  |
| -------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "frontendOpenOrders"                                                                                                                         |
| user<mark style="color:red;">\*</mark> | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000.                                                 |
| dex                                    | String | Perp dex name. Defaults to the empty string which represents the first perp dex. Spot open orders are only included with the first perp dex. |

{% tabs %}
{% tab title="200: OK " %}
```json
[
    {
        "coin": "BTC",
        "isPositionTpsl": false,
        "isTrigger": false,
        "limitPx": "29792.0",
        "oid": 91490942,
        "orderType": "Limit",
        "origSz": "5.0",
        "reduceOnly": false,
        "side": "A",
        "sz": "5.0",
        "timestamp": 1681247412573,
        "triggerCondition": "N/A",
        "triggerPx": "0.0",
    }
]
```
{% endtab %}
{% endtabs %}

## Retrieve a user's fills

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

Returns at most 2000 most recent fills

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                                                                                                                                             |
| -------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "userFills"                                                                                                                                                                             |
| user<mark style="color:red;">\*</mark> | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000.                                                                                            |
| aggregateByTime                        | bool   | When true, partial fills are combined when a crossing order gets filled by multiple different resting orders. Resting orders filled by multiple crossing orders will not be aggregated. |



{% tabs %}
{% tab title="200: OK" %}
```json
[
    // Perp fill
    {
        "closedPnl": "0.0",
        "coin": "AVAX",
        "crossed": false,
        "dir": "Open Long",
        "hash": "0xa166e3fa63c25663024b03f2e0da011a00307e4017465df020210d3d432e7cb8",
        "oid": 90542681,
        "px": "18.435",
        "side": "B",
        "startPosition": "26.86",
        "sz": "93.53",
        "time": 1681222254710,
        "fee": "0.01",
        "feeToken": "USDC",
        "builderFee": "0.01", // this is optional and will not be present if 0
        "tid": 118906512037719
    },
    // Spot fill - note the difference in the "coin" format. Refer to 
    // https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids
    // for more information on how spot asset IDs work
    {
        "coin": "@107",
        "px": "18.62041381",
        "sz": "43.84",
        "side": "A",
        "time": 1735969713869,
        "startPosition": "10659.65434798",
        "dir": "Sell",
        "closedPnl": "8722.988077",
        "hash": "0x2222138cc516e3fe746c0411dd733f02e60086f43205af2ae37c93f6a792430b",
        "oid": 59071663721,
        "crossed": true,
        "fee": "0.304521",
        "tid": 907359904431134,
        "feeToken": "USDC"
    }
]
```
{% endtab %}
{% endtabs %}

## Retrieve a user's fills by time

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

Returns at most 2000 fills per response and only the 10000 most recent fills are available

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                                             |
| ------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark>      | String | userFillsByTime                                                                                                                                                                         |
| user<mark style="color:red;">\*</mark>      | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000.                                                                                            |
| startTime<mark style="color:red;">\*</mark> | int    | Start time in milliseconds, inclusive                                                                                                                                                   |
| endTime                                     | int    | End time in milliseconds, inclusive. Defaults to current time.                                                                                                                          |
| aggregateByTime                             | bool   | When true, partial fills are combined when a crossing order gets filled by multiple different resting orders. Resting orders filled by multiple crossing orders will not be aggregated. |

{% tabs %}
{% tab title="200: OK Number of fills is limited to 2000" %}
```json
[
    // Perp fill
    {
        "closedPnl": "0.0",
        "coin": "AVAX",
        "crossed": false,
        "dir": "Open Long",
        "hash": "0xa166e3fa63c25663024b03f2e0da011a00307e4017465df020210d3d432e7cb8",
        "oid": 90542681,
        "px": "18.435",
        "side": "B",
        "startPosition": "26.86",
        "sz": "93.53",
        "time": 1681222254710,
        "fee": "0.01",
        "feeToken": "USDC",
        "builderFee": "0.01", // this is optional and will not be present if 0
        "tid": 118906512037719
    },
    // Spot fill - note the difference in the "coin" format. Refer to 
    // https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids
    // for more information on how spot asset IDs work
    {
        "coin": "@107",
        "px": "18.62041381",
        "sz": "43.84",
        "side": "A",
        "time": 1735969713869,
        "startPosition": "10659.65434798",
        "dir": "Sell",
        "closedPnl": "8722.988077",
        "hash": "0x2222138cc516e3fe746c0411dd733f02e60086f43205af2ae37c93f6a792430b",
        "oid": 59071663721,
        "crossed": true,
        "fee": "0.304521",
        "tid": 907359904431134,
        "feeToken": "USDC"
    }
]
```
{% endtab %}
{% endtabs %}

## Query user rate limits

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Request Body



| Name | Type   | Description                                                                                 |
| ---- | ------ | ------------------------------------------------------------------------------------------- |
| user | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000 |
| type | String | userRateLimit                                                                               |

{% tabs %}
{% tab title="200: OK A successful response" %}
```json
{
  "cumVlm": "2854574.593578",
  "nRequestsUsed": 2890,
  "nRequestsCap": 2864574
}
```
{% endtab %}
{% endtabs %}

## Query order status by oid or cloid

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Request Body

| Name                                   | Type             | Description                                                                                  |
| -------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------- |
| user<mark style="color:red;">\*</mark> | String           | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |
| type<mark style="color:red;">\*</mark> | String           | "orderStatus"                                                                                |
| oid<mark style="color:red;">\*</mark>  | uint64 or string | Either u64 representing the order id or 16-byte hex string representing the client order id  |

The \<status> string returned has the following possible values:

| Order status                              | Explanation                                                                       |
| ----------------------------------------- | --------------------------------------------------------------------------------- |
| open                                      | Placed successfully                                                               |
| filled                                    | Filled                                                                            |
| canceled                                  | Canceled by user                                                                  |
| triggered                                 | Trigger order triggered                                                           |
| rejected                                  | Rejected at time of placement                                                     |
| marginCanceled                            | Canceled because insufficient margin to fill                                      |
| vaultWithdrawalCanceled                   | Vaults only. Canceled due to a user's withdrawal from vault                       |
| openInterestCapCanceled                   | Canceled due to order being too aggressive when open interest was at cap          |
| selfTradeCanceled                         | Canceled due to self-trade prevention                                             |
| reduceOnlyCanceled                        | Canceled reduced-only order that does not reduce position                         |
| siblingFilledCanceled                     | TP/SL only. Canceled due to sibling ordering being filled                         |
| delistedCanceled                          | Canceled due to asset delisting                                                   |
| liquidatedCanceled                        | Canceled due to liquidation                                                       |
| scheduledCancel                           | API only. Canceled due to exceeding scheduled cancel deadline (dead man's switch) |
| tickRejected                              | Rejected due to invalid tick price                                                |
| minTradeNtlRejected                       | Rejected due to order notional below minimum                                      |
| perpMarginRejected                        | Rejected due to insufficient margin                                               |
| reduceOnlyRejected                        | Rejected due to reduce only                                                       |
| badAloPxRejected                          | Rejected due to post-only immediate match                                         |
| iocCancelRejected                         | Rejected due to IOC not able to match                                             |
| badTriggerPxRejected                      | Rejected due to invalid TP/SL price                                               |
| marketOrderNoLiquidityRejected            | Rejected due to lack of liquidity for market order                                |
| positionIncreaseAtOpenInterestCapRejected | Rejected due to open interest cap                                                 |
| positionFlipAtOpenInterestCapRejected     | Rejected due to open interest cap                                                 |
| tooAggressiveAtOpenInterestCapRejected    | Rejected due to price too aggressive at open interest cap                         |
| openInterestIncreaseRejected              | Rejected due to open interest cap                                                 |
| insufficientSpotBalanceRejected           | Rejected due to insufficient spot balance                                         |
| oracleRejected                            | Rejected due to price too far from oracle                                         |
| perpMaxPositionRejected                   | Rejected due to exceeding margin tier limit at current leverage                   |



{% tabs %}
{% tab title="200: OK A successful response" %}
```json
{
  "status": "order",
  "order": {
    "order": {
      "coin": "ETH",
      "side": "A",
      "limitPx": "2412.7",
      "sz": "0.0",
      "oid": 1,
      "timestamp": 1724361546645,
      "triggerCondition": "N/A",
      "isTrigger": false,
      "triggerPx": "0.0",
      "children": [],
      "isPositionTpsl": false,
      "reduceOnly": true,
      "orderType": "Market",
      "origSz": "0.0076",
      "tif": "FrontendMarket",
      "cloid": null
    },
    "status": <status>,
    "statusTimestamp": 1724361546645
  }
}
```
{% endtab %}

{% tab title="200: OK Missing Order" %}
```json
{
  "status": "unknownOid"
}
```
{% endtab %}
{% endtabs %}

## L2 book snapshot

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

Returns at most 20 levels per side

**Headers**

| Name                                           | Value              |
| ---------------------------------------------- | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | "application/json" |

**Body**

| Name                                   | Type   | Description                                                                                                                               |
| -------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "l2Book"                                                                                                                                  |
| coin<mark style="color:red;">\*</mark> | String | coin                                                                                                                                      |
| nSigFigs                               | Number | Optional field to aggregate levels to `nSigFigs` significant figures. Valid values are 2, 3, 4, 5, and `null`, which means full precision |
| mantissa                               | Number | Optional field to aggregate levels. This field is only allowed if nSigFigs is 5. Accepts values of 1, 2 or 5.                             |

**Response**

{% tabs %}
{% tab title="200: OK" %}
```json
{
  "coin": "BTC",
  "time": 1754450974231,
  "levels": [
    [
      {
        "px": "113377.0",
        "sz": "7.6699",
        "n": 17 // number of levels
      },
      {
        "px": "113376.0",
        "sz": "4.13714",
        "n": 8
      },
    ],
    [
      {
        "px": "113397.0",
        "sz": "0.11543",
        "n": 3
      }
    ]
  ]
}
```
{% endtab %}
{% endtabs %}

## Candle snapshot

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

Only the most recent 5000 candles are available

Supported intervals: "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "12h", "1d", "3d", "1w", "1M"

**Headers**

| Name                                           | Value              |
| ---------------------------------------------- | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | "application/json" |

**Body**

| Name                                   | Type   | Description                                                                                    |
| -------------------------------------- | ------ | ---------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "candleSnapshot"                                                                               |
| req<mark style="color:red;">\*</mark>  | Object | {"coin": \<coin>, "interval": "15m", "startTime": \<epoch millis>, "endTime": \<epoch millis>} |

**Response**

{% tabs %}
{% tab title="200: OK" %}
```json
[
  {
    "T": 1681924499999,
    "c": "29258.0",
    "h": "29309.0",
    "i": "15m",
    "l": "29250.0",
    "n": 189,
    "o": "29295.0",
    "s": "BTC",
    "t": 1681923600000,
    "v": "0.98639"
  }
]
```
{% endtab %}
{% endtabs %}

## Check builder fee approval

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`



**Headers**

| Name                                           | Value              |
| ---------------------------------------------- | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | "application/json" |

**Body**

| Name                                      | Type   | Description                                                                                  |
| ----------------------------------------- | ------ | -------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark>    | String | "maxBuilderFee"                                                                              |
| user<mark style="color:red;">\*</mark>    | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |
| builder<mark style="color:red;">\*</mark> | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |

**Response**

{% tabs %}
{% tab title="200: OK" %}
```json
1 // maximum fee approved in tenths of a basis point i.e. 1 means 0.001%
```
{% endtab %}
{% endtabs %}

## Retrieve a user's historical orders

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

Returns at most 2000 most recent historical orders

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                                                  |
| -------------------------------------- | ------ | -------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "historicalOrders"                                                                           |
| user<mark style="color:red;">\*</mark> | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |



{% tabs %}
{% tab title="200: OK" %}
```json
[
  {
    "order": {
      "coin": "ETH",
      "side": "A",
      "limitPx": "2412.7",
      "sz": "0.0",
      "oid": 1,
      "timestamp": 1724361546645,
      "triggerCondition": "N/A",
      "isTrigger": false,
      "triggerPx": "0.0",
      "children": [],
      "isPositionTpsl": false,
      "reduceOnly": true,
      "orderType": "Market",
      "origSz": "0.0076",
      "tif": "FrontendMarket",
      "cloid": null
    },
    "status": "filled" | "open" | "canceled" | "triggered" | "rejected" | "marginCanceled",
    "statusTimestamp": 1724361546645
  }
]
```
{% endtab %}
{% endtabs %}

## Retrieve a user's TWAP slice fills

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

Returns at most 2000 most recent TWAP slice fills

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                                                  |
| -------------------------------------- | ------ | -------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "userTwapSliceFills"                                                                         |
| user<mark style="color:red;">\*</mark> | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |



{% tabs %}
{% tab title="200: OK" %}
```json
[
    {
        "fill": {
            "closedPnl": "0.0",
            "coin": "AVAX",
            "crossed": true,
            "dir": "Open Long",
            "hash": "0x0000000000000000000000000000000000000000000000000000000000000000", // TWAP fills have a hash of 0
            "oid": 90542681,
            "px": "18.435",
            "side": "B",
            "startPosition": "26.86",
            "sz": "93.53",
            "time": 1681222254710,
            "fee": "0.01",
            "feeToken": "USDC",
            "tid": 118906512037719
        },
        "twapId": 3156
    }
]
```
{% endtab %}
{% endtabs %}

## Retrieve a user's subaccounts

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                                                  |
| -------------------------------------- | ------ | -------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "subAccounts"                                                                                |
| user<mark style="color:red;">\*</mark> | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |



{% tabs %}
{% tab title="200: OK" %}
```json
[
  {
    "name": "Test",
    "subAccountUser": "0x035605fc2f24d65300227189025e90a0d947f16c",
    "master": "0x8c967e73e6b15087c42a10d344cff4c96d877f1d",
    "clearinghouseState": {
      "marginSummary": {
        "accountValue": "29.78001",
        "totalNtlPos": "0.0",
        "totalRawUsd": "29.78001",
        "totalMarginUsed": "0.0"
      },
      "crossMarginSummary": {
        "accountValue": "29.78001",
        "totalNtlPos": "0.0",
        "totalRawUsd": "29.78001",
        "totalMarginUsed": "0.0"
      },
      "crossMaintenanceMarginUsed": "0.0",
      "withdrawable": "29.78001",
      "assetPositions": [],
      "time": 1733968369395
    },
    "spotState": {
      "balances": [
        {
          "coin": "USDC",
          "token": 0,
          "total": "0.22",
          "hold": "0.0",
          "entryNtl": "0.0"
        }
      ]
    }
  }
]
```
{% endtab %}
{% endtabs %}

## Retrieve details for a vault

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                           | Type   | Description                                                                                  |
| ---------------------------------------------- | ------ | -------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark>         | String | "vaultDetails"                                                                               |
| vaultAddress<mark style="color:red;">\*</mark> | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |
| user                                           | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |



{% tabs %}
{% tab title="200: OK" %}
```json
{
  "name": "Test",
  "vaultAddress": "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",
  "leader": "0x677d831aef5328190852e24f13c46cac05f984e7",
  "description": "This community-owned vault provides liquidity to Hyperliquid through multiple market making strategies, performs liquidations, and accrues platform fees.",
  "portfolio": [
    [
      "day",
      {
        "accountValueHistory": [
          [
            1734397526634,
            "329265410.90790099"
          ]
        ],
        "pnlHistory": [
          [
            1734397526634,
            "0.0"
          ],
        ],
        "vlm": "0.0"
      }
    ],
    [
      "week" | "month" | "allTime" | "perpDay" | "perpWeek" | "perpMonth" | "perpAllTime",
      {...}
    ]
  ],
  "apr": 0.36387129259090006,
  "followerState": null,
  "leaderFraction": 0.0007904828725729887,
  "leaderCommission": 0,
  "followers": [
    {
      "user": "0x005844b2ffb2e122cf4244be7dbcb4f84924907c",
      "vaultEquity": "714491.71026243",
      "pnl": "3203.43026143",
      "allTimePnl": "79843.74476743",
      "daysFollowing": 388,
      "vaultEntryTime": 1700926145201,
      "lockupUntil": 1734824439201
    }
  ],
  "maxDistributable": 94856870.164485,
  "maxWithdrawable": 742557.680863,
  "isClosed": false,
  "relationship": {
    "type": "parent",
    "data": {
      "childAddresses": [
        "0x010461c14e146ac35fe42271bdc1134ee31c703a",
        "0x2e3d94f0562703b25c83308a05046ddaf9a8dd14",
        "0x31ca8395cf837de08b24da3f660e77761dfb974b"
      ]
    }
  },
  "allowDeposits": true,
  "alwaysCloseOnWithdraw": false
}  
```
{% endtab %}
{% endtabs %}

## Retrieve a user's vault deposits

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                                                  |
| -------------------------------------- | ------ | -------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "userVaultEquities"                                                                          |
| user<mark style="color:red;">\*</mark> | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |



{% tabs %}
{% tab title="200: OK" %}
```json
[
  {
    "vaultAddress": "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",
    "equity": "742500.082809",
  }
]
```
{% endtab %}
{% endtabs %}

## Query a user's role

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                                                  |
| -------------------------------------- | ------ | -------------------------------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "userRole"                                                                                   |
| user<mark style="color:red;">\*</mark> | String | Address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |

{% tabs %}
{% tab title="User" %}
```
{"role":"user"} # "missing", "user", "agent", "vault", or "subAccount"
```
{% endtab %}

{% tab title="Agent" %}
```
{"role":"agent", "data": {"user": "0x..."}}
```
{% endtab %}

{% tab title="Vault" %}
```
{"role":"vault"}
```
{% endtab %}

{% tab title="Subaccount" %}
```
{"role":"subAccount", "data":{"master":"0x..."}}
```
{% endtab %}

{% tab title="Missing" %}
```
{"role":"missing"}
```
{% endtab %}
{% endtabs %}

## Query a user's portfolio

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                          |
| -------------------------------------- | ------ | -------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "portfolio"                                                          |
| user<mark style="color:red;">\*</mark> | String | hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |

{% tabs %}
{% tab title="200: OK" %}
```json
[
  [
    "day",
    {
      "accountValueHistory": [
        [
          1741886630493,
          "0.0"
        ],
        [
          1741895270493,
          "0.0"
        ],
        ...
      ],
      "pnlHistory": [
        [
          1741886630493,
          "0.0"
        ],
        [
          1741895270493,
          "0.0"
        ],
        ...
      ],
      "vlm": "0.0"
    }
  ],
  ["week", { ... }],
  ["month", { ... }],
  ["allTime", { ... }],
  ["perpDay", { ... }],
  ["perpWeek", { ... }],
  ["perpMonth", { ... }],
  ["perpAllTime", { ... }]
]
```
{% endtab %}
{% endtabs %}

## Query a user's referral information

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                          |
| -------------------------------------- | ------ | -------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "referral"                                                           |
| user<mark style="color:red;">\*</mark> | String | hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |

{% tabs %}
{% tab title="200: OK" %}
```json
{
    "referredBy": {
        "referrer": "0x5ac99df645f3414876c816caa18b2d234024b487",
        "code": "TESTNET"
    },
    "cumVlm": "149428030.6628420055",
    "unclaimedRewards": "11.047361",
    "claimedRewards": "22.743781",
    "builderRewards": "0.027802",
    "referrerState": {
        "stage": "ready",
        "data": {
            "code": "TEST",
            "referralStates": [
                {
                    "cumVlm": "960652.017122",
                    "cumRewardedFeesSinceReferred": "196.838825",
                    "cumFeesRewardedToReferrer": "19.683748",
                    "timeJoined": 1679425029416,
                    "user": "0x11af2b93dcb3568b7bf2b6bd6182d260a9495728"
                },
                {
                    "cumVlm": "438278.672653",
                    "cumRewardedFeesSinceReferred": "97.628107",
                    "cumFeesRewardedToReferrer": "9.762562",
                    "timeJoined": 1679423947882,
                    "user": "0x3f69d170055913103a034a418953b8695e4e42fa"
                }
            ]
        }
    },
    "rewardHistory": []
}
```
{% endtab %}
{% endtabs %}

Note that rewardHistory is for legacy rewards. Claimed rewards are now returned in nonFundingLedgerUpdate

## Query a user's fees

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                          |
| -------------------------------------- | ------ | -------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "userFees"                                                           |
| user<mark style="color:red;">\*</mark> | String | hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |

{% tabs %}
{% tab title="200: OK" %}
```json
{
  "dailyUserVlm": [
    {
      "date": "2025-05-23",
      "userCross": "0.0",
      "userAdd": "0.0",
      "exchange": "2852367.0770729999"
    },
    ...
  ],
  "feeSchedule": {
    "cross": "0.00045",
    "add": "0.00015",
    "spotCross": "0.0007",
    "spotAdd": "0.0004",
    "tiers": {
      "vip": [
        {
          "ntlCutoff": "5000000.0",
          "cross": "0.0004",
          "add": "0.00012",
          "spotCross": "0.0006",
          "spotAdd": "0.0003"
        },
        ...
      ],
      "mm": [
        {
          "makerFractionCutoff": "0.005",
          "add": "-0.00001"
        },
        ...
      ]
    },
    "referralDiscount": "0.04",
    "stakingDiscountTiers": [
      {
        "bpsOfMaxSupply": "0.0",
        "discount": "0.0"
      },
      {
        "bpsOfMaxSupply": "0.0001",
        "discount": "0.05"
      },
      ...
    ]
  },
  "userCrossRate": "0.000315",
  "userAddRate": "0.000105",
  "userSpotCrossRate": "0.00049",
  "userSpotAddRate": "0.00028",
  "activeReferralDiscount": "0.0",
  "trial": null,
  "feeTrialReward": "0.0",
  "nextTrialAvailableTimestamp": null,
  "stakingLink": {
    "type": "tradingUser",
    "stakingUser": "0x54c049d9c7d3c92c2462bf3d28e083f3d6805061"
  },
  "activeStakingDiscount": {
    "bpsOfMaxSupply": "4.7577998927",
    "discount": "0.3"
  }
}
```
{% endtab %}
{% endtabs %}

## Query a user's staking delegations

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                          |
| -------------------------------------- | ------ | -------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "delegations"                                                        |
| user<mark style="color:red;">\*</mark> | String | hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |

{% tabs %}
{% tab title="200: OK" %}
```json
[
    {
        "validator":"0x5ac99df645f3414876c816caa18b2d234024b487",
        "amount":"12060.16529862",
        "lockedUntilTimestamp":1735466781353
    },
    ...
]
```
{% endtab %}
{% endtabs %}

## Query a user's staking summary

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                          |
| -------------------------------------- | ------ | -------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "delegatorSummary"                                                   |
| user<mark style="color:red;">\*</mark> | String | hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |

{% tabs %}
{% tab title="200: OK" %}
```json
{
    "delegated": "12060.16529862",
    "undelegated": "0.0",
    "totalPendingWithdrawal": "0.0",
    "nPendingWithdrawals": 0
}
```
{% endtab %}
{% endtabs %}

## Query a user's staking history

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                          |
| -------------------------------------- | ------ | -------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "delegatorHistory"                                                   |
| user<mark style="color:red;">\*</mark> | String | hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |

{% tabs %}
{% tab title="200: OK" %}
```json
[
    {
        "time": 1735380381353,
        "hash": "0x55492465cb523f90815a041a226ba90147008d4b221a24ae8dc35a0dbede4ea4",
        "delta": {
            "delegate": {
                "validator": "0x5ac99df645f3414876c816caa18b2d234024b487",
                "amount": "10000.0",
                "isUndelegate": false
            }
        }
    },
    ...
]
```
{% endtab %}
{% endtabs %}

## Query a user's staking rewards

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/info`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                   | Type   | Description                                                          |
| -------------------------------------- | ------ | -------------------------------------------------------------------- |
| type<mark style="color:red;">\*</mark> | String | "delegatorRewards"                                                   |
| user<mark style="color:red;">\*</mark> | String | hexadecimal format; e.g. 0x0000000000000000000000000000000000000000. |

{% tabs %}
{% tab title="200: OK" %}
```json
[
    {
        "time": 1736726400073,
        "source": "delegation",
        "totalAmount": "0.73117184"
    },
    {
        "time": 1736726400073,
        "source": "commission",
        "totalAmount": "130.76445876"
    },
    ...
]
```
{% endtab %}
{% endtabs %}

---
description: >-
  The exchange endpoint is used to interact with and trade on the Hyperliquid
  chain. See the Python SDK for code to generate signatures for these requests.
---

# Exchange endpoint

### Asset

Many of the requests take asset as an input. For perpetuals this is the index in the `universe` field returned by the`meta` response. For spot assets, use `10000 + index` where `index` is the corresponding index in `spotMeta.universe`. For example, when submitting an order for `PURR/USDC`, the asset that should be used is `10000` because its asset index in the spot metadata is `0`.

### Subaccounts and vaults

Subaccounts and vaults do not have private keys. To perform actions on behalf of a subaccount or vault signing should be done by the master account and the vaultAddress field should be set to the address of the subaccount or vault. The basic\_vault.py example in the Python SDK demonstrates this.

### Expires After

Some actions support an optional field `expiresAfter` which is a timestamp in milliseconds after which the action will be rejected. User-signed actions such as Core USDC transfer do not support the `expiresAfter` field. Note that actions consume 5x the usual address-based rate limit when canceled due to a stale `expiresAfter` field.&#x20;

See the Python SDK for details on how to incorporate this field when signing.&#x20;

## Place an order

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

See Python SDK for full featured examples on the fields of the order request.



For limit orders, TIF (time-in-force) sets the behavior of the order upon first hitting the book.

ALO (add liquidity only, i.e. "post only") will be canceled instead of immediately matching.

IOC (immediate or cancel) will have the unfilled part canceled instead of resting.

GTC (good til canceled) orders have no special behavior.

Client Order ID (cloid) is an optional 128 bit hex string, e.g. `0x1234567890abcdef1234567890abcdef`



#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "order",<br>  "orders": [{</p><p>    "a": Number,</p><p>    "b": Boolean,</p><p>    "p": String,</p><p>    "s": String,</p><p>    "r": Boolean,</p><p>    "t": {</p><p>      "limit": {</p><p>        "tif": "Alo" | "Ioc" | "Gtc" </p><p>      } or</p><p>      "trigger": {</p><p>         "isMarket": Boolean,</p><p>         "triggerPx": String,</p><p>         "tpsl": "tp" | "sl"</p><p>       }</p><p>    },</p><p>    "c": Cloid (optional)</p><p>  }],</p><p>  "grouping": "na" | "normalTpsl" | "positionTpsl",</p><p>  "builder": Optional({"b": "address", "f": Number})</p><p>}<br><br>Meaning of keys:<br>a is asset<br>b is isBuy<br>p is price<br>s is size<br>r is reduceOnly<br>t is type<br>c is cloid (client order id)<br><br>Meaning of keys in optional builder argument:<br>b is the address the should receive the additional fee<br>f is the size of the fee in tenths of a basis point e.g. if f is 10, 1bp of the order notional  will be charged to the user and sent to the builder</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| vaultAddress                                | String | If trading on behalf of a vault or subaccount, its Onchain address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| expiresAfter                                | Number | Timestamp in milliseconds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |



{% tabs %}
{% tab title="200: OK Successful Response (resting)" %}
```
{
   "status":"ok",
   "response":{
      "type":"order",
      "data":{
         "statuses":[
            {
               "resting":{
                  "oid":77738308
               }
            }
         ]
      }
   }
}
```
{% endtab %}

{% tab title="200: OK Error Response" %}
```
{
   "status":"ok",
   "response":{
      "type":"order",
      "data":{
         "statuses":[
            {
               "error":"Order must have minimum value of $10."
            }
         ]
      }
   }
}
```
{% endtab %}

{% tab title="200: OK Successful Response (filled)" %}
```
{
   "status":"ok",
   "response":{
      "type":"order",
      "data":{
         "statuses":[
            {
               "filled":{
                  "totalSz":"0.02",
                  "avgPx":"1891.4",
                  "oid":77747314
               }
            }
         ]
      }
   }
}
```
{% endtab %}
{% endtabs %}

## Cancel order(s)

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                                                                     |
| ------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "cancel",</p><p>  "cancels": [</p><p>    {</p><p>      "a": Number,</p><p>      "o": Number</p><p>    }</p><p>  ]</p><p>}<br><br>Meaning of keys:<br>a is asset<br>o is oid (order id)</p> |
|                                             |        |                                                                                                                                                                                                                 |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                                                                                        |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                 |
| vaultAddress                                | String | If trading on behalf of a vault or subaccount, its address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000                                                                  |
| expiresAfter                                | Number | Timestamp in milliseconds                                                                                                                                                                                       |

{% tabs %}
{% tab title="200: OK Successful Response" %}
```
{
   "status":"ok",
   "response":{
      "type":"cancel",
      "data":{
         "statuses":[
            "success"
         ]
      }
   }
}
```
{% endtab %}

{% tab title="200: OK Error Response" %}
```
{
   "status":"ok",
   "response":{
      "type":"cancel",
      "data":{
         "statuses":[
            {
               "error":"Order was never placed, already canceled, or filled."
            }
         ]
      }
   }
}
```
{% endtab %}
{% endtabs %}

## Cancel order(s) by cloid

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`&#x20;

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                       |
| ------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "cancelByCloid",</p><p>  "cancels": [</p><p>    {</p><p>      "asset": Number,</p><p>      "cloid": String</p><p>    }</p><p>  ]</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                                          |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                   |
| vaultAddress                                | String | If trading on behalf of a vault or subaccount, its address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000                    |
| expiresAfter                                | Number | Timestamp in milliseconds                                                                                                                                         |

{% tabs %}
{% tab title="200: OK Successful Response" %}

{% endtab %}

{% tab title="200: OK Error Response" %}

{% endtab %}
{% endtabs %}

## Schedule cancel (dead man's switch)

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`&#x20;

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                    |
| ------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "scheduleCancel",</p><p>  "time": number (optional)</p><p>}</p>                                                           |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                       |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                |
| vaultAddress                                | String | If trading on behalf of a vault or subaccount, its address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000 |
| expiresAfter                                | Number | Timestamp in milliseconds                                                                                                                      |

Schedule a cancel-all operation at a future time. Not including time will remove the scheduled cancel operation. The time must be at least 5 seconds after the current time. Once the time comes, all open orders will be canceled and a trigger count will be incremented. The max number of triggers per day is 10. This trigger count is reset at 00:00 UTC.

## Modify an order

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange` &#x20;

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "modify",</p><p>  "oid": Number | Cloid,</p><p>  "order": {</p><p>    "a": Number,</p><p>    "b": Boolean,</p><p>    "p": String,</p><p>    "s": String,</p><p>    "r": Boolean,</p><p>    "t": {</p><p>      "limit": {</p><p>        "tif": "Alo" | "Ioc" | "Gtc" </p><p>      } or</p><p>      "trigger": {</p><p>         "isMarket": Boolean,</p><p>         "triggerPx": String,</p><p>         "tpsl": "tp" | "sl"</p><p>       }</p><p>    },</p><p>    "c": Cloid (optional)</p><p>  }</p><p>}<br><br>Meaning of keys:<br>a is asset<br>b is isBuy<br>p is price<br>s is size<br>r is reduceOnly<br>t is type<br>c is cloid (client order id)</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| vaultAddress                                | String | If trading on behalf of a vault or subaccount, its Onchain address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| expiresAfter                                | Number | Timestamp in milliseconds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

{% tabs %}
{% tab title="200: OK Successful Response" %}

{% endtab %}

{% tab title="200: OK Error Response" %}

{% endtab %}
{% endtabs %}

## Modify multiple orders

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "batchModify",</p><p>  "modifies": [{</p><p>    "oid": Number | Cloid,</p><p>    "order": {</p><p>      "a": Number,</p><p>      "b": Boolean,</p><p>      "p": String,</p><p>      "s": String,</p><p>      "r": Boolean,</p><p>      "t": {</p><p>        "limit": {</p><p>          "tif": "Alo" | "Ioc" | "Gtc" </p><p>        } or</p><p>        "trigger": {</p><p>           "isMarket": Boolean,</p><p>           "triggerPx": String,</p><p>           "tpsl": "tp" | "sl"</p><p>         }</p><p>      },</p><p>      "c": Cloid (optional)</p><p>    }</p><p>  }]</p><p>}<br><br>Meaning of keys:<br>a is asset<br>b is isBuy<br>p is price<br>s is size<br>r is reduceOnly<br>t is type<br>c is cloid (client order id)</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| vaultAddress                                | String | If trading on behalf of a vault or subaccount, its Onchain address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| expiresAfter                                | Number | Timestamp in milliseconds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

## Update leverage

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

Update cross or isolated leverage on a coin.&#x20;

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                         |
| ------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "updateLeverage",</p><p>  "asset": index of coin,</p><p>  "isCross": true or false if updating cross-leverage,</p><p>  "leverage": integer representing new leverage, subject to leverage constraints on that coin</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                                                                                                                            |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                     |
| vaultAddress                                | String | If trading on behalf of a vault or subaccount, its Onchain address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000                                                                                              |
| expiresAfter                                | Number | Timestamp in milliseconds                                                                                                                                                                                                                           |

{% tabs %}
{% tab title="200: OK Successful response" %}
```
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Update isolated margin

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

Add or remove margin from isolated position

Note that to target a specific leverage instead of a USDC value of margin change, there is an alternate action `{"type": "topUpIsolatedOnlyMargin", "asset": <asset>, "leverage": <float string>}`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                             |
| ------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "updateIsolatedMargin",</p><p>  "asset": index of coin,</p><p>  "isBuy": true, (this parameter won't have any effect until hedge mode is introduced)</p><p>  "ntli": int representing amount to add or remove with 6 decimals, e.g. 1000000 for 1 usd,</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                                                                                                                                                                |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                         |
| vaultAddress                                | String | If trading on behalf of a vault or subaccount, its Onchain address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000                                                                                                                                  |
| expiresAfter                                | Number | Timestamp in milliseconds                                                                                                                                                                                                                                                               |

{% tabs %}
{% tab title="200: OK Successful response" %}
```
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Core USDC transfer

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

Send usd to another address. This transfer does not touch the EVM bridge. The signature format is human readable for wallet interfaces.

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "usdSend",</p><p>  "hyperliquidChain": "Mainnet" (on testnet use "Testnet" instead),<br>  "signatureChainId": the id of the chain used when signing in hexadecimal format; e.g. "0xa4b1" for Arbitrum,</p><p>  "destination": address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000,</p><p>   "amount": amount of usd to send as a string, e.g. "1" for 1 usd,</p><p>     "time": current timestamp in milliseconds as a Number, should match nonce</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

{% tabs %}
{% tab title="200: OK Successful Response" %}
```
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Core spot transfer

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

Send spot assets to another address. This transfer does not touch the EVM bridge. The signature format is human readable for wallet interfaces.

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "spotSend",</p><p>  "hyperliquidChain": "Mainnet" (on testnet use "Testnet" instead),<br>  "signatureChainId": the id of the chain used when signing in hexadecimal format; e.g. "0xa4b1" for Arbitrum,</p><p>  "destination": address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000,<br>  "token": tokenName:tokenId; e.g. "PURR:0xc4bf3f870c0e9465323c0b6ed28096c2",</p><p>   "amount": amount of token to send as a string, e.g. "0.01",</p><p>     "time": current timestamp in milliseconds as a Number, should match nonce</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |



{% tabs %}
{% tab title="200: OK Successful Response" %}
```
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

```
Example sign typed data for generating the signature:
{
  "types": {
    "HyperliquidTransaction:SpotSend": [
      {
        "name": "hyperliquidChain",
        "type": "string"
      },
      {
        "name": "destination",
        "type": "string"
      },
      {
        "name": "token",
        "type": "string"
      },
      {
        "name": "amount",
        "type": "string"
      },
      {
        "name": "time",
        "type": "uint64"
      }
    ]
  },
  "primaryType": "HyperliquidTransaction:SpotSend",
  "domain": {
    "name": "HyperliquidSignTransaction",
    "version": "1",
    "chainId": 42161,
    "verifyingContract": "0x0000000000000000000000000000000000000000"
  },
  "message": {
    "destination": "0x0000000000000000000000000000000000000000",
    "token": "PURR:0xc1fb593aeffbeb02f85e0308e9956a90",
    "amount": "0.1",
    "time": 1716531066415,
    "hyperliquidChain": "Mainnet"
  }
}
```

## Initiate a withdrawal request

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

This method is used to initiate the withdrawal flow. After making this request, the L1 validators will sign and send the withdrawal request to the bridge contract. There is a $1 fee for withdrawing at the time of this writing and withdrawals take approximately 5 minutes to finalize.

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{<br>  "type": "withdraw3",</p><p>  "hyperliquidChain": "Mainnet" (on testnet use "Testnet" instead),<br>  "signatureChainId": the id of the chain used when signing in hexadecimal format; e.g. "0xa4b1" for Arbitrum,</p><p>  "amount": amount of usd to send as a string, e.g. "1" for 1 usd,</p><p>  "time": current timestamp in milliseconds as a Number, should match nonce,</p><p>  "destination": address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds, must match the nonce in the action Object above                                                                                                                                                                                                                                                                                                                                                                                                             |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

{% tabs %}
{% tab title="200: OK " %}
```
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Transfer from Spot account to Perp account (and vice versa)

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

This method is used to transfer USDC from the user's spot wallet to perp wallet and vice versa.

**Headers**

| Name                                           | Value              |
| ---------------------------------------------- | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | "application/json" |

**Body**

<table><thead><tr><th>Name</th><th width="200">Type</th><th>Description</th></tr></thead><tbody><tr><td>action<mark style="color:red;">*</mark></td><td>Object</td><td><p>{</p><p>  "type": "usdClassTransfer",</p><p>  "hyperliquidChain": "Mainnet" (on testnet use "Testnet" instead),<br>  "signatureChainId": the id of the chain used when signing in hexadecimal format; e.g. "0xa4b1" for Arbitrum,</p><p> "amount": amount of usd to transfer as a string, e.g. "1" for 1 usd. If you want to use this action for a subaccount, you can include subaccount: address after the amount, e.g. "1" subaccount:0x0000000000000000000000000000000000000000,</p><p>  "toPerp": true if (spot -> perp) else false,</p><p>"nonce": current timestamp in milliseconds as a Number, must match nonce in outer request body</p><p>}</p></td></tr><tr><td>nonce<mark style="color:red;">*</mark></td><td>Number</td><td>Recommended to use the current timestamp in milliseconds, must match the nonce in the action Object above</td></tr><tr><td>signature<mark style="color:red;">*</mark></td><td>Object</td><td></td></tr></tbody></table>

**Response**

{% tabs %}
{% tab title="200: OK" %}
```json
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Send Asset (testnet only)

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

This generalized method is used to transfer tokens between different perp DEXs, spot balance, users, and/or sub-accounts. Use "" to specify the default USDC perp DEX and "spot" to specify spot. Only the collateral token can be transferred to or from a perp DEX.

#### Headers

| Name                                           | Value              |
| ---------------------------------------------- | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | `application/json` |

#### Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "sendAsset",</p><p>  "hyperliquidChain": "Mainnet" (on testnet use "Testnet" instead),</p><p>  "signatureChainId": the id of the chain used when signing in hexadecimal format; e.g. "0xa4b1" for Arbitrum,</p><p>  "destination": address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000,</p><p>  "sourceDex": name of perp dex to transfer from,</p><p>  "destinationDex": name of the perp dex to transfer to,</p><p>  "token": tokenName:tokenId; e.g. "PURR:0xc4bf3f870c0e9465323c0b6ed28096c2",</p><p>  "amount": amount of token to send as a string; e.g. "0.01",</p><p>  "fromSubAccount": address in 42-character hexadecimal format or empty string if not from a subaccount,</p><p>  "nonce": current timestamp in milliseconds as a Number, should match nonce</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds, must match the nonce in the action Object above                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

#### Response

{% tabs %}
{% tab title="200: OK" %}
```
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Deposit into staking

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

This method is used to transfer native token from the user's spot account into staking for delegating to validators.&#x20;

#### Headers

| Name                                           | Value              |
| ---------------------------------------------- | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | `application/json` |

#### Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "cDeposit",</p><p>  "hyperliquidChain": "Mainnet" (on testnet use "Testnet" instead),<br>  "signatureChainId": the id of the chain used when signing in hexadecimal format; e.g. "0xa4b1" for Arbitrum,</p><p> "wei": amount of wei to transfer as a number,</p><p>"nonce": current timestamp in milliseconds as a Number, must match nonce in outer request body</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds, must match the nonce in the action Object above                                                                                                                                                                                                                                                                                          |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                    |

#### Response

{% tabs %}
{% tab title="200: OK" %}
```json
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Withdraw from staking

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

This method is used to transfer native token from staking into the user's spot account. Note that transfers from staking to spot account go through a 7 day unstaking queue.

#### Headers

| Name                                           | Value              |
| ---------------------------------------------- | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | `application/json` |

#### Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "cWithdraw",</p><p>  "hyperliquidChain": "Mainnet" (on testnet use "Testnet" instead),<br>  "signatureChainId": the id of the chain used when signing in hexadecimal format; e.g. "0xa4b1" for Arbitrum,</p><p> "wei": amount of wei to transfer as a number,</p><p>"nonce": current timestamp in milliseconds as a Number, must match nonce in outer request body</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds, must match the nonce in the action Object above                                                                                                                                                                                                                                                                                           |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                     |

#### Response

{% tabs %}
{% tab title="200: OK" %}
```json
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Delegate or undelegate stake from validator

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

Delegate or undelegate native tokens to or from a validator. Note that delegations to a particular validator have a lockup duration of 1 day.

#### Headers

| Name                                           | Value              |
| ---------------------------------------------- | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | `application/json` |

#### Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "tokenDelegate",</p><p>  "hyperliquidChain": "Mainnet" (on testnet use "Testnet" instead),<br>  "signatureChainId": the id of the chain used when signing in hexadecimal format; e.g. "0xa4b1" for Arbitrum,</p><p>  "validator": address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000,<br>"isUndelegate": boolean,</p><p>"wei": number,</p><p>"nonce": current timestamp in milliseconds as a Number, must match nonce in outer request body</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | number | Recommended to use the current timestamp in milliseconds                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |

#### Response

{% tabs %}
{% tab title="200: OK" %}
```json
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Deposit or withdraw from a vault

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

Add or remove funds from a vault.

**Headers**

| Name                                           | Value              |
| ---------------------------------------------- | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | `application/json` |

**Body**

| Name                                        | Type   | Description                                                                                                                                                                                                         |
| ------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "vaultTransfer",</p><p>  "vaultAddress": address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000,<br>"isDeposit": boolean,</p><p>"usd": number</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | number | Recommended to use the current timestamp in milliseconds                                                                                                                                                            |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                     |
| expiresAfter                                | Number | Timestamp in milliseconds                                                                                                                                                                                           |

**Response**

{% tabs %}
{% tab title="200" %}
```json
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Approve an API wallet

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

Approves an API Wallet (also sometimes referred to as an Agent Wallet). See [here](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/nonces-and-api-wallets#api-wallets) for more details.

**Headers**

| Name                                           | Value              |
| ---------------------------------------------- | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | `application/json` |

**Body**

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{<br>  "type": "approveAgent",</p><p>  "hyperliquidChain": "Mainnet" (on testnet use "Testnet" instead),<br>  "signatureChainId": the id of the chain used when signing in hexadecimal format; e.g. "0xa4b1" for Arbitrum,</p><p>  "agentAddress": address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000,</p><p>"agentName": Optional name for the API wallet. An account can have 1 unnamed approved wallet and up to 3 named ones. And additional 2 named agents are allowed per subaccount,</p><p>  "nonce": current timestamp in milliseconds as a Number, must match nonce in outer request body</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | number | Recommended to use the current timestamp in milliseconds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

**Response**

{% tabs %}
{% tab title="200" %}
```json
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Approve a builder fee

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

Approve a maximum fee rate for a builder.

**Headers**

| Name                                           | Value              |
| ---------------------------------------------- | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | `application/json` |

**Body**

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{<br>  "type": "approveBuilderFee",</p><p>  "hyperliquidChain": "Mainnet" (on testnet use "Testnet" instead),<br>  "signatureChainId": the id of the chain used when signing in hexadecimal format; e.g. "0xa4b1" for Arbitrum,</p><p>  "maxFeeRate": the maximum allowed builder fee rate as a percent string; e.g. "0.001%",</p><p>  "builder": address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000,</p><p>  "nonce": current timestamp in milliseconds as a Number, must match nonce in outer request body</p><p>}</p> |
| nonce<mark style="color:red;">\*</mark>     | number | Recommended to use the current timestamp in milliseconds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

**Response**

{% tabs %}
{% tab title="200" %}
```json
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Place a TWAP order

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "twapOrder",<br>  "twap": {</p><p>    "a": Number,</p><p>    "b": Boolean,</p><p>    "s": String,</p><p>    "r": Boolean,</p><p>    "m": Number,</p><p>    "t": Boolean</p><p>  }</p><p>  }<br><br>Meaning of keys:<br>a is asset<br>b is isBuy<br>s is size<br>r is reduceOnly</p><p>m is minutes<br>t is randomize</p> |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                                                                                                                                                                                                                      |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                                                                                                                                                                                                               |
| vaultAddress                                | String | If trading on behalf of a vault or subaccount, its Onchain address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000                                                                                                                                                                                        |
| expiresAfter                                | Number | Timestamp in milliseconds                                                                                                                                                                                                                                                                                                                     |



{% tabs %}
{% tab title="200: OK Successful Response" %}
```
{
   "status":"ok",
   "response":{
      "type":"twapOrder",
      "data":{
         "status": {
            "running":{
               "twapId":77738308
            }
         }
      }
   }
}
```
{% endtab %}

{% tab title="200: OK Error Response" %}
```
{
   "status":"ok",
   "response":{
      "type":"twapOrder",
      "data":{
         "status": {
            "error":"Invalid TWAP duration: 1 min(s)"
         }
      }
   }
}
```
{% endtab %}
{% endtabs %}

## Cancel a TWAP order

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                                                                                     |
| ------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "twapCancel",</p><p>   "a": Number,</p><p>   "t": Number</p><p>}<br><br>Meaning of keys:<br>a is asset<br>t is twap_id</p> |
|                                             |        |                                                                                                                                                 |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                                                                                        |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                                                                                 |
| vaultAddress                                | String | If trading on behalf of a vault or subaccount, its address in 42-character hexadecimal format; e.g. 0x0000000000000000000000000000000000000000  |
| expiresAfter                                | Number | Timestamp in milliseconds                                                                                                                       |

{% tabs %}
{% tab title="200: OK Successful Response" %}
```
{
   "status":"ok",
   "response":{
      "type":"twapCancel",
      "data":{
         "status": "success"
      }
   }
}
```
{% endtab %}

{% tab title="200: OK Error Response" %}
```
{
   "status":"ok",
   "response":{
      "type":"twapCancel",
      "data":{
         "status": {
            "error": "TWAP was never placed, already canceled, or filled."
         }
      }
   }
}
```
{% endtab %}
{% endtabs %}

## Reserve Additional Actions

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`&#x20;

Instead of trading to increase the address based rate limits, this action allows reserving additional actions for 0.0005 USDC per request. The cost is paid from the Perps balance.&#x20;

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                                                        |
| ------------------------------------------- | ------ | ---------------------------------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "reserveRequestWeight",</p><p>   "weight": Number</p><p>}</p> |
|                                             |        |                                                                                    |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds                           |
| signature<mark style="color:red;">\*</mark> | Object |                                                                                    |
| expiresAfter                                | Number | Timestamp in milliseconds                                                          |

{% tabs %}
{% tab title="200: OK Successful Response" %}
```
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}

## Invalidate Pending Nonce (noop)

<mark style="color:green;">`POST`</mark> `https://api.hyperliquid.xyz/exchange`&#x20;

This action does not do anything (no operation), but causes the nonce to be marked as used. This can be a more effective way to cancel in-flight orders than the cancel action.

#### Headers

| Name                                           | Type   | Description        |
| ---------------------------------------------- | ------ | ------------------ |
| Content-Type<mark style="color:red;">\*</mark> | String | "application/json" |

#### Request Body

| Name                                        | Type   | Description                                              |
| ------------------------------------------- | ------ | -------------------------------------------------------- |
| action<mark style="color:red;">\*</mark>    | Object | <p>{</p><p>  "type": "noop"</p><p>}</p>                  |
|                                             |        |                                                          |
| nonce<mark style="color:red;">\*</mark>     | Number | Recommended to use the current timestamp in milliseconds |
| signature<mark style="color:red;">\*</mark> | Object |                                                          |
| expiresAfter                                | Number | Timestamp in milliseconds                                |

{% tabs %}
{% tab title="200: OK Successful Response" %}
```
{'status': 'ok', 'response': {'type': 'default'}}
```
{% endtab %}
{% endtabs %}
# Websocket

WebSocket endpoints are available for real-time data streaming and as an alternative to HTTP request sending on the Hyperliquid exchange. The WebSocket URLs by network are:

* Mainnet: `wss://api.hyperliquid.xyz/ws`&#x20;
* Testnet: `wss://api.hyperliquid-testnet.xyz/ws`.

### Connecting

To connect to the WebSocket API, you must establish a WebSocket connection to the respective URL based on your desired network. Once connected, you can start sending subscription messages to receive real-time data updates.

Example from command line:

```
$ wscat -c  wss://api.hyperliquid.xyz/ws
Connected (press CTRL+C to quit)
>  { "method": "subscribe", "subscription": { "type": "trades", "coin": "SOL" } }
< {"channel":"subscriptionResponse","data":{"method":"subscribe","subscription":{"type":"trades","coin":"SOL"}}}
```

Note: this doc uses Typescript for defining many of the message types. If you prefer to use Python, you can check out the equivalent types in the python SDK [here](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/hyperliquid/utils/types.py) and example connection code [here](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/hyperliquid/websocket_manager.py).

---
description: This page describes subscribing to data streams using the WebSocket API.
---

# Subscriptions

### Subscription messages

To subscribe to specific data feeds, you need to send a subscription message. The subscription message format is as follows:

```json
{
  "method": "subscribe",
  "subscription": { ... }
}
```

The subscription ack provides a snapshot of previous data for time series data (e.g. user fills). These snapshot messages are tagged with `isSnapshot: true` and can be ignored if the previous messages were already processed.

The subscription object contains the details of the specific feed you want to subscribe to. Choose from the following subscription types and provide the corresponding properties:

1. `allMids`:
   * Subscription message: `{ "type": "allMids", "dex": "<dex>" }`
   * Data format: `AllMids`&#x20;
   * The `dex` field represents the perp dex to source mids from.
   * Note that the `dex` field is optional. If not provided, then the first perp dex is used. Spot mids are only included with the first perp dex.
2. `notification`:
   * Subscription message: `{ "type": "notification", "user": "<address>" }`
   * Data format: `Notification`
3. `webData2`
   * Subscription message: `{ "type": "webData2", "user": "<address>" }`
   * Data format: `WebData2`
4. `candle`:
   * Subscription message: `{ "type": "candle", "coin": "<coin_symbol>", "interval": "<candle_interval>" }`
   * &#x20;Supported intervals: "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "12h", "1d", "3d", "1w", "1M"
   * Data format: `Candle[]`
5. `l2Book`:
   * Subscription message: `{ "type": "l2Book", "coin": "<coin_symbol>" }`
   * Optional parameters: nSigFigs: int, mantissa: int
   * Data format: `WsBook`
6. `trades`:
   * Subscription message: `{ "type": "trades", "coin": "<coin_symbol>" }`
   * Data format: `WsTrade[]`
7. `orderUpdates`:
   * Subscription message: `{ "type": "orderUpdates", "user": "<address>" }`
   * Data format: `WsOrder[]`
8. `userEvents`:&#x20;
   * Subscription message: `{ "type": "userEvents", "user": "<address>" }`
   * Data format: `WsUserEvent`
9. `userFills`:&#x20;
   * Subscription message: `{ "type": "userFills", "user": "<address>" }`
   * Optional parameter:  `aggregateByTime: bool`&#x20;
   * Data format: `WsUserFills`
10. `userFundings`:&#x20;
    * Subscription message: `{ "type": "userFundings", "user": "<address>" }`
    * Data format: `WsUserFundings`
11. `userNonFundingLedgerUpdates`:&#x20;
    * Subscription message: `{ "type": "userNonFundingLedgerUpdates", "user": "<address>" }`
    * Data format: `WsUserNonFundingLedgerUpdates`
12. `activeAssetCtx`:&#x20;
    * Subscription message: `{ "type": "activeAssetCtx", "coin": "coin_symbol>" }`
    * Data format: `WsActiveAssetCtx` or `WsActiveSpotAssetCtx`&#x20;
13. `activeAssetData`: (only supports Perps)
    * Subscription message: `{ "type": "activeAssetData", "user": "<address>", "coin": "coin_symbol>" }`
    * Data format: `WsActiveAssetData`
14. `userTwapSliceFills`:&#x20;
    * Subscription message: `{ "type": "userTwapSliceFills", "user": "<address>" }`
    * Data format: `WsUserTwapSliceFills`
15. `userTwapHistory`:&#x20;
    * Subscription message: `{ "type": "userTwapHistory", "user": "<address>" }`
    * Data format: `WsUserTwapHistory`
16. `bbo` :
    * Subscription message: `{ "type": "bbo", "coin": "<coin>" }`
    * Data format: `WsBbo`

### Data formats

The server will respond to successful subscriptions with a message containing the `channel` property set to `"subscriptionResponse"`, along with the `data` field providing the original subscription. The server will then start sending messages with the `channel` property set to the corresponding subscription type e.g. `"allMids"` and the `data` field providing the subscribed data.

The `data` field format depends on the subscription type:

* `AllMids`: All mid prices.
  * Format: `AllMids { mids: Record<string, string> }`
* `Notification`: A notification message.
  * Format: `Notification { notification: string }`
* `WebData2`: Aggregate information about a user, used primarily for the frontend.
  * Format: `WebData2`
* `WsTrade[]`: An array of trade updates.
  * Format: `WsTrade[]`
* `WsBook`: Order book snapshot updates.
  * Format: `WsBook { coin: string; levels: [Array<WsLevel>, Array<WsLevel>]; time: number; }`
* `WsOrder`: User order updates.
  * Format: `WsOrder[]`
* `WsUserEvent`: User events that are not order updates
  * Format: `WsUserEvent { "fills": [WsFill] | "funding": WsUserFunding | "liquidation": WsLiquidation | "nonUserCancel": [WsNonUserCancel] }`
* `WsUserFills` : Fills snapshot followed by streaming fills
* `WsUserFundings` : Funding payments snapshot followed by funding payments on the hour
* `WsUserNonFundingLedgerUpdates`: Ledger updates not including funding payments: withdrawals, deposits, transfers, and liquidations
* `WsBbo` : Bbo updates that are sent only if the bbo changes on a block

For the streaming user endpoints such as `WsUserFills`,`WsUserFundings` the first message has `isSnapshot: true` and the following streaming updates have `isSnapshot: false`.&#x20;

### Data type definitions

Here are the definitions of the data types used in the WebSocket API:

```typescript
interface WsTrade {
  coin: string;
  side: string;
  px: string;
  sz: string;
  hash: string;
  time: number;
  // tid is 50-bit hash of (buyer_oid, seller_oid). 
  // For a globally unique trade id, use (block_time, coin, tid)
  tid: number;  
  users: [string, string] // [buyer, seller]
}

// Snapshot feed, pushed on each block that is at least 0.5 since last push
interface WsBook {
  coin: string;
  levels: [Array<WsLevel>, Array<WsLevel>];
  time: number;
}

interface WsBbo {
  coin: string;
  time: number;
  bbo: [WsLevel | null, WsLevel | null];
}

interface WsLevel {
  px: string; // price
  sz: string; // size
  n: number; // number of orders
}

interface Notification {
  notification: string;
}

interface AllMids {
  mids: Record<string, string>;
}

interface Candle {
  t: number; // open millis
  T: number; // close millis
  s: string; // coin
  i: string; // interval
  o: number; // open price
  c: number; // close price
  h: number; // high price
  l: number; // low price
  v: number; // volume (base unit)
  n: number; // number of trades
}

type WsUserEvent = {"fills": WsFill[]} | {"funding": WsUserFunding} | {"liquidation": WsLiquidation} | {"nonUserCancel" :WsNonUserCancel[]};

interface WsUserFills {
  isSnapshot?: boolean;
  user: string;
  fills: Array<WsFill>;
}

interface WsFill {
  coin: string;
  px: string; // price
  sz: string; // size
  side: string;
  time: number;
  startPosition: string;
  dir: string; // used for frontend display
  closedPnl: string;
  hash: string; // L1 transaction hash
  oid: number; // order id
  crossed: boolean; // whether order crossed the spread (was taker)
  fee: string; // negative means rebate
  tid: number; // unique trade id
  liquidation?: FillLiquidation;
  feeToken: string; // the token the fee was paid in
  builderFee?: string; // amount paid to builder, also included in fee
}

interface FillLiquidation {
  liquidatedUser?: string;
  markPx: number;
  method: "market" | "backstop";
}

interface WsUserFunding {
  time: number;
  coin: string;
  usdc: string;
  szi: string;
  fundingRate: string;
}

interface WsLiquidation {
  lid: number;
  liquidator: string;
  liquidated_user: string;
  liquidated_ntl_pos: string;
  liquidated_account_value: string;
}

interface WsNonUserCancel {
  coin: String;
  oid: number;
}

interface WsOrder {
  order: WsBasicOrder;
  status: string; // See https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint#query-order-status-by-oid-or-cloid for a list of possible values
  statusTimestamp: number;
}

interface WsBasicOrder {
  coin: string;
  side: string;
  limitPx: string;
  sz: string;
  oid: number;
  timestamp: number;
  origSz: string;
  cloid: string | undefined;
}

interface WsActiveAssetCtx {
  coin: string;
  ctx: PerpsAssetCtx;
}

interface WsActiveSpotAssetCtx {
  coin: string;
  ctx: SpotAssetCtx;
}

type SharedAssetCtx = {
  dayNtlVlm: number;
  prevDayPx: number;
  markPx: number;
  midPx?: number;
};

type PerpsAssetCtx = SharedAssetCtx & {
  funding: number;
  openInterest: number;
  oraclePx: number;
};

type SpotAssetCtx = SharedAssetCtx & {
  circulatingSupply: number;
};

interface WsActiveAssetData {
  user: string;
  coin: string;
  leverage: Leverage;
  maxTradeSzs: [number, number];
  availableToTrade: [number, number];
}

interface WsTwapSliceFill {
  fill: WsFill;
  twapId: number;
}

interface WsUserTwapSliceFills {
  isSnapshot?: boolean;
  user: string;
  twapSliceFills: Array<WsTwapSliceFill>;
}

interface TwapState {
  coin: string;
  user: string;
  side: string;
  sz: number;
  executedSz: number;
  executedNtl: number;
  minutes: number;
  reduceOnly: boolean;
  randomize: boolean;
  timestamp: number;
}

type TwapStatus = "activated" | "terminated" | "finished" | "error";
interface WsTwapHistory {
  state: TwapState;
  status: {
    status: TwapStatus;
    description: string;
  };
  time: number;
}

interface WsUserTwapHistory {
  isSnapshot?: boolean;
  user: string;
  history: Array<WsTwapHistory>;
}
```

<details>

<summary>WsUserNonFundingLedgerUpdates</summary>

```typescript
interface WsUserNonFundingLedgerUpdate {
  time: number;
  hash: string;
  delta: WsLedgerUpdate;
}

type WsLedgerUpdate = 
  | WsDeposit
  | WsWithdraw 
  | WsInternalTransfer 
  | WsSubAccountTransfer 
  | WsLedgerLiquidation 
  | WsVaultDelta 
  | WsVaultWithdrawal
  | WsVaultLeaderCommission
  | WsSpotTransfer
  | WsAccountClassTransfer
  | WsSpotGenesis
  | WsRewardsClaim;
  
interface WsDeposit {
  type: "deposit";
  usdc: number;
}

interface WsWithdraw {
  type: "withdraw";
  usdc: number;
  nonce: number;
  fee: number;
}

interface WsInternalTransfer {
  type: "internalTransfer";
  usdc: number;
  user: string;
  destination: string;
  fee: number;
}

interface WsSubAccountTransfer {
  type: "subAccountTransfer";
  usdc: number;
  user: string;
  destination: string;
}

interface WsLedgerLiquidation {
  type: "liquidation";
  // NOTE: for isolated positions this is the isolated account value
  accountValue: number;
  leverageType: "Cross" | "Isolated";
  liquidatedPositions: Array<LiquidatedPosition>;
}

interface LiquidatedPosition {
  coin: string;
  szi: number;
}

interface WsVaultDelta {
  type: "vaultCreate" | "vaultDeposit" | "vaultDistribution";
  vault: string;
  usdc: number;
}

interface WsVaultWithdrawal {
  type: "vaultWithdraw";
  vault: string;
  user: string;
  requestedUsd: number;
  commission: number;
  closingCost: number;
  basis: number;
  netWithdrawnUsd: number;
}

interface WsVaultLeaderCommission {
  type: "vaultLeaderCommission";
  user: string;
  usdc: number;
}

interface WsSpotTransfer = {
  type: "spotTransfer";
  token: string;
  amount: number;
  usdcValue: number;
  user: string;
  destination: string;
  fee: number;
}

interface WsAccountClassTransfer = {
  type: "accountClassTransfer";
  usdc: number;
  toPerp: boolean;
}

interface WsSpotGenesis = {
  type: "spotGenesis";
  token: string;
  amount: number;
}

interface WsRewardsClaim = {
  type: "rewardsClaim";
  amount: number;
}
```

</details>

Please note that the above data types are in TypeScript format, and their usage corresponds to the respective subscription types.

### Examples

Here are a few examples of subscribing to different feeds using the subscription messages:

1.  Subscribe to all mid prices:

    ```json
    { "method": "subscribe", "subscription": { "type": "allMids" } }
    ```
2.  Subscribe to notifications for a specific user:

    ```json
    { "method": "subscribe", "subscription": { "type": "notification", "user": "<address>" } }
    ```
3.  Subscribe to web data for a specific user:

    ```json
    { "method": "subscribe", "subscription": { "type": "webData", "user": "<address>" } }
    ```
4.  Subscribe to candle updates for a specific coin and interval:

    ```json
    { "method": "subscribe", "subscription": { "type": "candle", "coin": "<coin_symbol>", "interval": "<candle_interval>" } }
    ```
5.  Subscribe to order book updates for a specific coin:

    ```json
    { "method": "subscribe", "subscription": { "type": "l2Book", "coin": "<coin_symbol>" } }
    ```
6.  Subscribe to trades for a specific coin:

    ```json
    { "method": "subscribe", "subscription": { "type": "trades", "coin": "<coin_symbol>" } }
    ```

### Unsubscribing from WebSocket feeds

To unsubscribe from a specific data feed on the Hyperliquid WebSocket API, you need to send an unsubscribe message with the following format:

```json
{
  "method": "unsubscribe",
  "subscription": { ... }
}
```

The `subscription` object should match the original subscription message that was sent when subscribing to the feed. This allows the server to identify the specific feed you want to unsubscribe from. By sending this unsubscribe message, you inform the server to stop sending further updates for the specified feed.

Please note that unsubscribing from a specific feed does not affect other subscriptions you may have active at that time. To unsubscribe from multiple feeds, you can send multiple unsubscribe messages, each with the appropriate subscription details.

---
description: This page describes posting requests using the WebSocket API.
---

# Post requests

### Request format

The WebSocket API supports posting requests that you can normally post through the HTTP API. These requests are either info requests or signed actions. For examples of info request payloads, please refer to the Info endpoint section. For examples of signed action payloads, please refer to the Exchange endpoint section.

To send such a payload for either type via the WebSocket API, you must wrap it as such:

```json
{
  "method": "post",
  "id": <number>,
  "request": {
    "type": "info" | "action",
    "payload": { ... }
  }
}
```

Note: The `method` and `id` fields are mandatory. It is recommended that you use a unique `id` for every post request you send in order to track outstanding requests through the channel.

Note: `explorer` requests are not supported via WebSocket.

### Response format

The server will respond to post requests with either a success or an error. For errors, a `String` is returned mirroring the HTTP status code and description that would have been returned if the request were sent through HTTP.

```json
{
  "channel": "post",
  "data": {
    "id": <number>,
    "response": {
      "type": "info" | "action" | "error",
      "payload": { ... }
    }
  }
}
```

### Examples

Here are a few examples of subscribing to different feeds using the subscription messages:

Sending an L2Book info request:

```json
{
  "method": "post",
  "id": 123,
  "request": {
    "type": "info",
    "payload": {
      "type": "l2Book",
      "coin": "ETH",
      "nSigFigs": 5,
      "mantissa": null
    }
  }
}
```

Sample response:

```json
{
  "channel": "post",
  "data": {
    "id": <number>,
    "response": {
      "type": "info",
      "payload": {
        "type": "l2Book",
        "data": {
          "coin": "ETH",
          "time": <number>,
          "levels": [
            [{"px":"3007.1","sz":"2.7954","n":1}],
            [{"px":"3040.1","sz":"3.9499","n":1}]
          ]
        }
      }
    }
  }
}
```

Sending an order signed action request:

```json
{
  "method": "post",
  "id": 256,
  "request": {
    "type": "action",
    "payload": {
      "action": {
        "type": "order",
        "orders": [{"a": 4, "b": true, "p": "1100", "s": "0.2", "r": false, "t": {"limit": {"tif": "Gtc"}}}],
        "grouping": "na"
      },
      "nonce": 1713825891591,
      "signature": {
        "r": "...",
        "s": "...",
        "v": "..."
      },
      "vaultAddress": "0x12...3"
    }
  }
}
```

Sample response:

```json
{
  "channel": "post",
  "data": {
    "id": 256,
    "response": {
      "type":"action",
      "payload": {
        "status": "ok",
        "response": {
          "type": "order",
          "data": {
            "statuses": [
              {
                "resting": {
                  "oid": 88383,
                }
              }
            ]
          }
        }
      }
    }
  }
}
```

---
description: This page describes the measures to keep WebSocket connections alive.
---

# Timeouts and heartbeats

The server will close any connection if it hasn't sent a message to it in the last 60 seconds. If you are subscribing to a channel that doesn't receive messages every 60 seconds, you can send heartbeat messages to keep your connection alive. The format for these messages are:

```json
{ "method": "ping" }
```

The server will respond with:

```json
{ "channel": "pong" }
```
