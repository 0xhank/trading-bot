from hyperliquid.info import Info
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
import json
from lib.logger import get_market_data_logger

logger = get_market_data_logger()


class DataStore:
    info: Info
    def __init__(self, address: str, info: Info):
        self.address = address
        self.info = info
        # Initialize DataFrames for user-specific and general subscription types only
        # Coin-specific data (l2Book, trades, candle, bbo, activeAssetCtx, activeAssetData) 
        # should use the CoinDataStore instead
        self.dataframes = {
            'allMids': pd.DataFrame(columns=['timestamp', 'mids']),
            'userEvents': pd.DataFrame(columns=['timestamp', 'event_type', 'data']),
            'userFills': pd.DataFrame(columns=['timestamp', 'isSnapshot', 'user', 'coin', 'px', 'sz', 'side', 'time', 'startPosition', 'dir', 'closedPnl', 'hash', 'oid', 'crossed', 'fee', 'tid', 'feeToken', 'builderFee']),
            'orderUpdates': pd.DataFrame(columns=['timestamp', 'coin', 'side', 'limitPx', 'sz', 'oid', 'order_timestamp', 'origSz', 'cloid', 'status', 'statusTimestamp']),
            'userFundings': pd.DataFrame(columns=['timestamp', 'isSnapshot', 'user', 'time', 'coin', 'usdc', 'szi', 'fundingRate']),
            'userNonFundingLedgerUpdates': pd.DataFrame(columns=['timestamp', 'isSnapshot', 'user', 'time', 'hash', 'delta_type', 'delta_data']),
            'webData2': pd.DataFrame(columns=['timestamp', 'data']),
        }

    def handle_update(self, subscription_type: str):
        def handler(data):
            """Handle updates for a specific subscription type"""
            try:
                timestamp = datetime.now()
                
                if subscription_type == 'allMids':
                    row = {'timestamp': timestamp, 'mids': json.dumps(data.get('mids', {}))}
                    new_df = pd.DataFrame([row])
                    if self.dataframes['allMids'].empty:
                        self.dataframes['allMids'] = new_df
                    else:
                        self.dataframes['allMids'] = pd.concat([self.dataframes['allMids'], new_df], ignore_index=True)
                    
                elif subscription_type == 'userEvents':
                    event_type = list(data.keys())[0] if data else 'unknown'
                    row = {
                        'timestamp': timestamp,
                        'event_type': event_type,
                        'data': json.dumps(data)
                    }
                    new_df = pd.DataFrame([row])
                    if self.dataframes['userEvents'].empty:
                        self.dataframes['userEvents'] = new_df
                    else:
                        self.dataframes['userEvents'] = pd.concat([self.dataframes['userEvents'], new_df], ignore_index=True)
                    
                elif subscription_type == 'userFills':
                    is_snapshot = data.get('isSnapshot', False)
                    user = data.get('user', '')
                    fills = data.get('fills', [])
                    
                    rows = []
                    for fill in fills:
                        rows.append({
                            'timestamp': timestamp,
                            'isSnapshot': is_snapshot,
                            'user': user,
                            'coin': fill.get('coin', ''),
                            'px': fill.get('px', ''),
                            'sz': fill.get('sz', ''),
                            'side': fill.get('side', ''),
                            'time': fill.get('time', 0),
                            'startPosition': fill.get('startPosition', ''),
                            'dir': fill.get('dir', ''),
                            'closedPnl': fill.get('closedPnl', ''),
                            'hash': fill.get('hash', ''),
                            'oid': fill.get('oid', 0),
                            'crossed': fill.get('crossed', False),
                            'fee': fill.get('fee', ''),
                            'tid': fill.get('tid', 0),
                            'feeToken': fill.get('feeToken', ''),
                            'builderFee': fill.get('builderFee', '')
                        })
                    
                    if rows:
                        new_df = pd.DataFrame(rows)
                        if self.dataframes['userFills'].empty:
                            self.dataframes['userFills'] = new_df
                        else:
                            self.dataframes['userFills'] = pd.concat([self.dataframes['userFills'], new_df], ignore_index=True)
                        
                elif subscription_type == 'orderUpdates':
                    orders = data if isinstance(data, list) else [data]
                    rows = []
                    
                    for order_update in orders:
                        order = order_update.get('order', {})
                        rows.append({
                            'timestamp': timestamp,
                            'coin': order.get('coin', ''),
                            'side': order.get('side', ''),
                            'limitPx': order.get('limitPx', ''),
                            'sz': order.get('sz', ''),
                            'oid': order.get('oid', 0),
                            'order_timestamp': order.get('timestamp', 0),
                            'origSz': order.get('origSz', ''),
                            'cloid': order.get('cloid', ''),
                            'status': order_update.get('status', ''),
                            'statusTimestamp': order_update.get('statusTimestamp', 0)
                        })
                    
                    if rows:
                        new_df = pd.DataFrame(rows)
                        if self.dataframes['orderUpdates'].empty:
                            self.dataframes['orderUpdates'] = new_df
                        else:
                            self.dataframes['orderUpdates'] = pd.concat([self.dataframes['orderUpdates'], new_df], ignore_index=True)
                        
                elif subscription_type == 'userFundings':
                    is_snapshot = data.get('isSnapshot', False)
                    user = data.get('user', '')
                    fundings = data.get('fundings', [])
                    
                    rows = []
                    for funding in fundings:
                        rows.append({
                            'timestamp': timestamp,
                            'isSnapshot': is_snapshot,
                            'user': user,
                            'time': funding.get('time', 0),
                            'coin': funding.get('coin', ''),
                            'usdc': funding.get('usdc', ''),
                            'szi': funding.get('szi', ''),
                            'fundingRate': funding.get('fundingRate', '')
                        })
                    
                    if rows:
                        new_df = pd.DataFrame(rows)
                        if self.dataframes['userFundings'].empty:
                            self.dataframes['userFundings'] = new_df
                        else:
                            self.dataframes['userFundings'] = pd.concat([self.dataframes['userFundings'], new_df], ignore_index=True)
                        
                elif subscription_type == 'userNonFundingLedgerUpdates':
                    is_snapshot = data.get('isSnapshot', False)
                    user = data.get('user', '')
                    ledger_updates = data.get('ledgerUpdates', [])
                    
                    rows = []
                    for update in ledger_updates:
                        delta = update.get('delta', {})
                        delta_type = delta.get('type', 'unknown') if isinstance(delta, dict) else 'unknown'
                        
                        rows.append({
                            'timestamp': timestamp,
                            'isSnapshot': is_snapshot,
                            'user': user,
                            'time': update.get('time', 0),
                            'hash': update.get('hash', ''),
                            'delta_type': delta_type,
                            'delta_data': json.dumps(delta)
                        })
                    
                    if rows:
                        new_df = pd.DataFrame(rows)
                        if self.dataframes['userNonFundingLedgerUpdates'].empty:
                            self.dataframes['userNonFundingLedgerUpdates'] = new_df
                        else:
                            self.dataframes['userNonFundingLedgerUpdates'] = pd.concat([self.dataframes['userNonFundingLedgerUpdates'], new_df], ignore_index=True)
                        
                elif subscription_type == 'webData2':
                    row = {'timestamp': timestamp, 'data': json.dumps(data)}
                    new_df = pd.DataFrame([row])
                    if self.dataframes['webData2'].empty:
                        self.dataframes['webData2'] = new_df
                    else:
                        self.dataframes['webData2'] = pd.concat([self.dataframes['webData2'], new_df], ignore_index=True)
                    
                else:
                    # Generic handler for unknown subscription types
                    row = {'timestamp': timestamp, 'data': json.dumps(data)}
                    new_df = pd.DataFrame([row])
                    if subscription_type not in self.dataframes:
                        self.dataframes[subscription_type] = pd.DataFrame(columns=['timestamp', 'data'])
                    if self.dataframes[subscription_type].empty:
                        self.dataframes[subscription_type] = new_df
                    else:
                        self.dataframes[subscription_type] = pd.concat([self.dataframes[subscription_type], new_df], ignore_index=True)
                    
                logger.debug(f"Updated {subscription_type} dataframe")
                    
            except Exception as e:
                logger.error(f"Error handling update for {subscription_type}: {e}")

        return handler
    def start(self):
        self.info.subscribe({"type": "allMids"}, self.handle_update("allMids"))

        user_subscriptions = [
            "userEvents", "userFills", "orderUpdates", 
            "userFundings", "userNonFundingLedgerUpdates", "webData2"
        ]

        for sub_type in user_subscriptions:
            self.info.subscribe(
                {"type": sub_type, "user": self.address}, 
                self.handle_update(sub_type)
            )

    def _parse_data(self, subscription_type: str, data: Any, timestamp: datetime) -> List[Dict]:
        """Parse data based on subscription type and return list of rows for DataFrame"""
        
        if subscription_type == 'allMids':
            return [{'timestamp': timestamp, 'mids': json.dumps(data.get('mids', {}))}]
            
        elif subscription_type == 'userEvents':
            event_type = list(data.keys())[0] if data else 'unknown'
            return [{
                'timestamp': timestamp,
                'event_type': event_type,
                'data': json.dumps(data)
            }]
            
        elif subscription_type == 'userFills':
            rows = []
            is_snapshot = data.get('isSnapshot', False)
            user = data.get('user', '')
            fills = data.get('fills', [])
            
            for fill in fills:
                rows.append({
                    'timestamp': timestamp,
                    'isSnapshot': is_snapshot,
                    'user': user,
                    'coin': fill.get('coin', ''),
                    'px': fill.get('px', ''),
                    'sz': fill.get('sz', ''),
                    'side': fill.get('side', ''),
                    'time': fill.get('time', 0),
                    'startPosition': fill.get('startPosition', ''),
                    'dir': fill.get('dir', ''),
                    'closedPnl': fill.get('closedPnl', ''),
                    'hash': fill.get('hash', ''),
                    'oid': fill.get('oid', 0),
                    'crossed': fill.get('crossed', False),
                    'fee': fill.get('fee', ''),
                    'tid': fill.get('tid', 0),
                    'feeToken': fill.get('feeToken', ''),
                    'builderFee': fill.get('builderFee', '')
                })
            return rows
            
        elif subscription_type == 'orderUpdates':
            orders = data if isinstance(data, list) else [data]
            rows = []
            for order_update in orders:
                order = order_update.get('order', {})
                rows.append({
                    'timestamp': timestamp,
                    'coin': order.get('coin', ''),
                    'side': order.get('side', ''),
                    'limitPx': order.get('limitPx', ''),
                    'sz': order.get('sz', ''),
                    'oid': order.get('oid', 0),
                    'order_timestamp': order.get('timestamp', 0),
                    'origSz': order.get('origSz', ''),
                    'cloid': order.get('cloid', ''),
                    'status': order_update.get('status', ''),
                    'statusTimestamp': order_update.get('statusTimestamp', 0)
                })
            return rows
            
        elif subscription_type == 'userFundings':
            rows = []
            is_snapshot = data.get('isSnapshot', False)
            user = data.get('user', '')
            fundings = data.get('fundings', [])
            
            for funding in fundings:
                rows.append({
                    'timestamp': timestamp,
                    'isSnapshot': is_snapshot,
                    'user': user,
                    'time': funding.get('time', 0),
                    'coin': funding.get('coin', ''),
                    'usdc': funding.get('usdc', ''),
                    'szi': funding.get('szi', ''),
                    'fundingRate': funding.get('fundingRate', '')
                })
            return rows
            
        elif subscription_type == 'userNonFundingLedgerUpdates':
            rows = []
            is_snapshot = data.get('isSnapshot', False)
            user = data.get('user', '')
            ledger_updates = data.get('ledgerUpdates', [])
            
            for update in ledger_updates:
                delta = update.get('delta', {})
                delta_type = delta.get('type', 'unknown') if isinstance(delta, dict) else 'unknown'
                
                rows.append({
                    'timestamp': timestamp,
                    'isSnapshot': is_snapshot,
                    'user': user,
                    'time': update.get('time', 0),
                    'hash': update.get('hash', ''),
                    'delta_type': delta_type,
                    'delta_data': json.dumps(delta)
                })
            return rows
            
        elif subscription_type == 'webData2':
            return [{'timestamp': timestamp, 'data': json.dumps(data)}]
            
        else:
            # Generic store for other subscription types
            return [{'timestamp': timestamp, 'data': json.dumps(data)}]
    
    def get_dataframe(self, subscription_type: str) -> pd.DataFrame:
        return self.dataframes.get(subscription_type, pd.DataFrame())
    
    def get_all_dataframes(self) -> Dict[str, pd.DataFrame]:
        return self.dataframes
    