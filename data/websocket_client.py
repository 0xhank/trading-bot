import json
import logging
import websocket
import threading
import time
from typing import Dict, Callable, Optional
from config.settings import Config


class HyperliquidWebSocketClient:
    """
    Basic WebSocket client for Hyperliquid real-time data feeds
    """
    
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        
        # WebSocket URLs
        self.ws_url = "wss://api.hyperliquid-testnet.xyz/ws" if self.config.SANDBOX else "wss://api.hyperliquid.xyz/ws"
        
        # WebSocket connection
        self.ws = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Subscriptions and callbacks
        self.subscriptions = {}
        self.message_handlers = {}
        
        # Threading
        self.ws_thread = None
        self.ping_thread = None
        self.should_stop = False
        
    def connect(self):
        """Establish WebSocket connection"""
        try:
            self.logger.info(f"Connecting to Hyperliquid WebSocket: {self.ws_url}")
            
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start WebSocket in separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection
            timeout = 10
            while not self.is_connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
                
            if not self.is_connected:
                raise Exception("Failed to connect within timeout")
                
            self.logger.info("WebSocket connected successfully")
            
            # Start ping thread to keep connection alive
            self._start_ping_thread()
            
        except Exception as e:
            self.logger.error(f"Error connecting to WebSocket: {e}")
            raise
    
    def disconnect(self):
        """Close WebSocket connection"""
        self.should_stop = True
        self.is_connected = False
        
        if self.ws:
            self.ws.close()
            
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)
            
        if self.ping_thread and self.ping_thread.is_alive():
            self.ping_thread.join(timeout=5)
            
        self.logger.info("WebSocket disconnected")
    
    def subscribe_all_mids(self, callback: Optional[Callable] = None):
        """Subscribe to all mid prices"""
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "allMids"
            }
        }
        self._send_subscription(subscription, "allMids", callback)
    
    def subscribe_trades(self, coin: str, callback: Optional[Callable] = None):
        """Subscribe to trades for a specific coin"""
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "trades",
                "coin": coin
            }
        }
        self._send_subscription(subscription, f"trades_{coin}", callback)
    
    def subscribe_l2_book(self, coin: str, callback: Optional[Callable] = None):
        """Subscribe to L2 order book for a specific coin"""
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": coin
            }
        }
        self._send_subscription(subscription, f"l2Book_{coin}", callback)
    
    def subscribe_candles(self, coin: str, interval: str = "1m", callback: Optional[Callable] = None):
        """Subscribe to candle data for a specific coin and interval"""
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "candle",
                "coin": coin,
                "interval": interval
            }
        }
        self._send_subscription(subscription, f"candle_{coin}_{interval}", callback)
    
    def subscribe_user_fills(self, user_address: str, callback: Optional[Callable] = None):
        """Subscribe to user fills"""
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "userFills",
                "user": user_address
            }
        }
        self._send_subscription(subscription, f"userFills_{user_address}", callback)
    
    def subscribe_user_orders(self, user_address: str, callback: Optional[Callable] = None):
        """Subscribe to user order updates"""
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "orderUpdates",
                "user": user_address
            }
        }
        self._send_subscription(subscription, f"orderUpdates_{user_address}", callback)
    
    def _send_subscription(self, subscription: Dict, key: str, callback: Optional[Callable] = None):
        """Send subscription message"""
        if not self.is_connected:
            self.logger.error("WebSocket not connected")
            return
        
        try:
            message = json.dumps(subscription)
            self.ws.send(message)
            
            # Store subscription info
            self.subscriptions[key] = subscription
            if callback:
                self.message_handlers[key] = callback
                
            self.logger.info(f"Sent subscription: {key}")
            
        except Exception as e:
            self.logger.error(f"Error sending subscription: {e}")
    
    def _on_open(self, ws):
        """Called when WebSocket connection is opened"""
        self.is_connected = True
        self.reconnect_attempts = 0
        self.logger.info("WebSocket connection opened")
    
    def _on_message(self, ws, message):
        """Called when a message is received"""
        try:
            data = json.loads(message)
            
            # Handle different message types
            if "channel" in data:
                channel = data["channel"]
                
                if channel == "subscriptionResponse":
                    self._handle_subscription_response(data)
                elif channel == "pong":
                    # Heartbeat response
                    pass
                else:
                    self._handle_data_message(channel, data)
            else:
                self.logger.debug(f"Received message without channel: {data}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON message: {e}")
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    def _on_error(self, ws, error):
        """Called when WebSocket error occurs"""
        self.logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Called when WebSocket connection is closed"""
        self.is_connected = False
        self.logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        
        # Attempt reconnection if not intentionally stopped
        if not self.should_stop and self.reconnect_attempts < self.max_reconnect_attempts:
            self._attempt_reconnection()
    
    def _handle_subscription_response(self, data):
        """Handle subscription confirmation"""
        subscription_data = data.get("data", {})
        subscription_type = subscription_data.get("subscription", {}).get("type", "unknown")
        self.logger.info(f"Subscription confirmed: {subscription_type}")
        print(f"✅ Subscribed to: {subscription_type}")
    
    def _handle_data_message(self, channel: str, data: Dict):
        """Handle incoming data messages"""
        # Print all messages by default
        print(f"\n📡 Channel: {channel}")
        print(f"📊 Data: {json.dumps(data.get('data', {}), indent=2)}")
        
        # Call custom handler if registered
        for key, handler in self.message_handlers.items():
            if channel in key or key in channel:
                try:
                    handler(channel, data)
                except Exception as e:
                    self.logger.error(f"Error in custom handler {key}: {e}")
    
    def _start_ping_thread(self):
        """Start heartbeat ping thread"""
        def ping_loop():
            while self.is_connected and not self.should_stop:
                try:
                    time.sleep(30)  # Ping every 30 seconds
                    if self.is_connected:
                        ping_message = json.dumps({"method": "ping"})
                        self.ws.send(ping_message)
                        self.logger.debug("Sent ping")
                except Exception as e:
                    self.logger.error(f"Error sending ping: {e}")
        
        self.ping_thread = threading.Thread(target=ping_loop)
        self.ping_thread.daemon = True
        self.ping_thread.start()
    
    def _attempt_reconnection(self):
        """Attempt to reconnect WebSocket"""
        self.reconnect_attempts += 1
        self.logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        
        time.sleep(2 ** self.reconnect_attempts)  # Exponential backoff
        
        try:
            self.connect()
            
            # Re-subscribe to previous subscriptions
            for key, subscription in self.subscriptions.items():
                self._send_subscription(subscription, key, self.message_handlers.get(key))
                
        except Exception as e:
            self.logger.error(f"Reconnection attempt failed: {e}")
