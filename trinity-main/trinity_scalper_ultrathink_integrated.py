#!/usr/bin/env python3
"""
TRINITY SCALPER WITH ULTRATHINK INTEGRATION
Uses ASI/HRM/MCTS signals from ULTRATHINK via Redis
"""

import os
import sys
import asyncio
import aiohttp
import json
import time
import logging
import traceback
import uuid
import redis.asyncio as redis
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/trinity-ultrathink.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TRINITY_ULTRATHINK')

# ============================================================================
# CREDENTIAL MANAGER (keeping existing)
# ============================================================================

class CredentialManager:
    """Manages encrypted API credentials"""
    
    def __init__(self):
        self.config_dir = "/opt/cashmachine/config"
        self.credentials = {}
        self.load_all_credentials()
    
    def load_all_credentials(self):
        """Load all available API credentials"""
        apis = ['oanda', 'alpaca']
        
        for api in apis:
            try:
                from cryptography.fernet import Fernet
                
                # Load encryption key
                key_file = f"{self.config_dir}/.{api}.key"
                enc_file = f"{self.config_dir}/{api}.enc"
                
                if os.path.exists(key_file) and os.path.exists(enc_file):
                    with open(key_file, "rb") as f:
                        key = f.read()
                    with open(enc_file, "rb") as f:
                        encrypted = f.read()
                    
                    cipher = Fernet(key)
                    decrypted = cipher.decrypt(encrypted)
                    config = json.loads(decrypted)
                    
                    self.credentials[api] = config
                    logger.info(f"✅ Loaded {api} credentials")
            except Exception as e:
                logger.warning(f"Could not load {api} credentials: {e}")
    
    def get(self, api: str, key: str) -> Optional[str]:
        """Get specific credential"""
        if api in self.credentials:
            return self.credentials[api].get(key)
        return None

# ============================================================================
# ULTRATHINK SIGNAL READER
# ============================================================================

class UltraThinkSignalReader:
    """Reads ASI/HRM/MCTS signals from ULTRATHINK via Redis"""
    
    def __init__(self):
        self.redis_client = None
        self.last_signal = None
        self.signal_history = deque(maxlen=100)
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await redis.Redis(
                host='10.100.2.200',
                port=6379,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("✅ Connected to ULTRATHINK via Redis")
            return True
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return False
    
    async def get_signal(self, symbol: str = None) -> Optional[Dict]:
        """Get latest ULTRATHINK signal"""
        try:
            # Get current ULTRATHINK signals from Redis
            signal_data = await self.redis_client.hgetall('ultrathink:signals')
            if not signal_data:
                return None
            
            # Handle numpy.float64 serialization issue
            confidence_str = signal_data.get('confidence', '0.5')
            if 'np.float64' in str(confidence_str):
                # Extract number from string like "np.float64(0.123)"
                confidence = float(confidence_str.split('(')[1].split(')')[0])
            else:
                confidence = float(confidence_str)
            
            if signal_data:
                signal = {
                    'signal': signal_data.get('signal', 'hold'),
                    'confidence': confidence,
                    'source': 'ULTRATHINK',
                    'timestamp': signal_data.get('timestamp'),
                    'components': {
                        'ASI': signal_data.get('asi'),
                        'HRM': signal_data.get('hrm'),
                        'MCTS': signal_data.get('mcts')
                    }
                }
                
                # Store in history
                self.signal_history.append(signal)
                self.last_signal = signal
                
                return signal
                
        except Exception as e:
            logger.error(f"Error getting ULTRATHINK signal: {e}")
            return None

# ============================================================================
# BROKER CONNECTIONS (keeping existing)
# ============================================================================

class EpicOandaBroker:
    """Real OANDA execution"""
    
    def __init__(self, creds: CredentialManager):
        self.creds = creds
        self.account_id = creds.get('oanda', 'account_id')
        self.api_token = creds.get('oanda', 'api_token')
        self.base_url = "https://api-fxpractice.oanda.com/v3"
        self.connected = False
        self.orders_executed = []
        
        if self.account_id and self.api_token:
            self.connected = True
            logger.info("✅ OANDA Connected")
    
    async def execute_trade(self, symbol: str, units: int, side: str) -> Dict:
        """Execute forex trade"""
        if not self.connected:
            return {"success": False, "error": "OANDA not connected"}
        
        try:
            order_data = {
                "order": {
                    "instrument": symbol,
                    "units": str(units if side == 'buy' else -units),
                    "type": "MARKET",
                    "positionFill": "DEFAULT",
                    "timeInForce": "FOK"
                }
            }
            
            url = f"{self.base_url}/accounts/{self.account_id}/orders"
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=order_data, headers=headers) as resp:
                    if resp.status == 201:
                        data = await resp.json()
                        order_id = data.get("orderFillTransaction", {}).get("orderID")
                        
                        self.orders_executed.append({
                            "order_id": order_id,
                            "instrument": symbol,
                            "units": units,
                            "side": side,
                            "time": datetime.now().isoformat()
                        })
                        
                        logger.info(f"✅ OANDA Order: {symbol} {side} {units}")
                        return {"success": True, "order_id": order_id}
                    else:
                        return {"success": False, "error": f"Status {resp.status}"}
                        
        except Exception as e:
            logger.error(f"OANDA trade error: {e}")
            return {"success": False, "error": str(e)}

class EpicAlpacaBroker:
    """Real Alpaca execution for stocks and crypto"""
    
    def __init__(self, creds: CredentialManager):
        self.creds = creds
        self.api_key = creds.get('alpaca', 'api_key')
        self.api_secret = creds.get('alpaca', 'api_secret')
        self.base_url = "https://paper-api.alpaca.markets/v2"
        self.connected = False
        self.orders_executed = []
        
        if self.api_key and self.api_secret:
            self.connected = False  # Will connect in initialize()
    
    async def connect(self):
        """Connect to Alpaca"""
        try:
            headers = {
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/account", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        cash = float(data.get("cash", 0))
                        self.connected = True
                        logger.info(f"✅ ALPACA Connected - Cash: ${cash:,.2f}")
                        
        except Exception as e:
            logger.error(f"Alpaca connection error: {e}")
    
    async def execute_trade(self, symbol: str, qty: int, side: str) -> Dict:
        """Execute stock or crypto trade"""
        if not self.connected:
            return {"success": False, "error": "Alpaca not connected"}
        
        try:
            # Determine if crypto
            is_crypto = symbol in ['BTC', 'ETH', 'SOL']
            
            order_data = {
                "symbol": f"{symbol}USD" if is_crypto else symbol,
                "qty": str(qty) if not is_crypto else None,
                "notional": str(qty * 100) if is_crypto else None,  # $100 per crypto trade
                "side": side,
                "type": "market",
                "time_in_force": "ioc" if not is_crypto else "gtc"  # Use IOC to avoid PDT
            }
            
            # Remove None values
            order_data = {k: v for k, v in order_data.items() if v is not None}
            
            headers = {
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/orders", 
                                       json=order_data, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        order_id = data.get("id")
                        
                        self.orders_executed.append({
                            "order_id": order_id,
                            "symbol": symbol,
                            "qty": qty,
                            "side": side,
                            "time": datetime.now().isoformat()
                        })
                        
                        logger.info(f"✅ ALPACA Order: {symbol} {side} qty={qty}")
                        return {"success": True, "order_id": order_id}
                    else:
                        error_text = await resp.text()
                        logger.error(f"Alpaca order failed: {error_text}")
                        return {"success": False, "error": error_text}
                        
        except Exception as e:
            logger.error(f"Alpaca trade error: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# MAIN TRINITY SCALPER WITH ULTRATHINK
# ============================================================================

class TrinityUltraThinkScalper:
    """Trinity Scalper using ULTRATHINK ASI/HRM/MCTS signals"""
    
    def __init__(self):
        logger.info("="*60)
        logger.info("⚡ TRINITY SCALPER + ULTRATHINK INTEGRATION")
        logger.info("🧠 Using ASI/HRM/MCTS AI Signals")
        logger.info("="*60)
        
        # Initialize components
        self.creds = CredentialManager()
        self.signal_reader = UltraThinkSignalReader()
        self.oanda = EpicOandaBroker(self.creds)
        self.alpaca = EpicAlpacaBroker(self.creds)
        
        # Trading pairs
        self.forex_pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY']
        self.stocks = ['SPY', 'QQQ', 'AAPL', 'TSLA']
        self.crypto = ['BTC', 'ETH', 'SOL']
        
        # State
        self.running = True
        self.total_trades = 0
        self.active_trades = {}
        
    async def initialize(self):
        """Initialize all connections"""
        # Connect to Redis for ULTRATHINK signals
        if not await self.signal_reader.connect():
            logger.error("Failed to connect to ULTRATHINK")
            return False
        
        # Connect to Alpaca
        await self.alpaca.connect()
        
        logger.info("✅ All systems initialized")
        return True
    
    def get_market_hours(self) -> Dict:
        """Check which markets are open"""
        from datetime import datetime
        import pytz
        
        et_tz = pytz.timezone('America/New_York')
        now_et = datetime.now(et_tz)
        hour = now_et.hour
        weekday = now_et.weekday()
        
        return {
            'stocks': weekday < 5 and 9 <= hour < 16,  # Mon-Fri 9:30-4pm ET
            'forex': weekday < 5 or (weekday == 6 and hour >= 17),  # Sun 5pm - Fri 5pm
            'crypto': True  # Always open
        }
    
    async def execute_ultrathink_signal(self, signal: Dict):
        """Execute trade based on ULTRATHINK signal"""
        if not signal or signal['signal'] == 'hold':
            return
        
        confidence = signal['confidence']
        if confidence < 0.6:  # Minimum confidence threshold
            return
        
        # Determine which market to trade based on time
        market_hours = self.get_market_hours()
        
        # Execute based on market availability
        trade_executed = False
        
        # Try crypto FIRST on Alpaca (NO PDT restrictions!)
        if market_hours['crypto'] and self.alpaca.connected:
            symbol = self.crypto[self.total_trades % len(self.crypto)]
            result = await self.alpaca.execute_trade(
                symbol,
                1,  # $100 worth (notional)
                signal['signal']
            )
            if result['success']:
                trade_executed = True
                logger.info(f"🪙 CRYPTO Trade: {symbol} {signal['signal']} (ASI/HRM/MCTS)")
        
        # Try forex if crypto didn't execute
        if not trade_executed and market_hours['forex'] and self.oanda.connected:
            symbol = self.forex_pairs[self.total_trades % len(self.forex_pairs)]
            result = await self.oanda.execute_trade(
                symbol,
                1000,  # 1000 units
                signal['signal']
            )
            if result['success']:
                trade_executed = True
                logger.info(f"💱 FOREX Trade: {symbol} {signal['signal']} (ASI/HRM/MCTS)")
        
        # STOCKS DISABLED TO AVOID PDT RESTRICTIONS
        # Uncomment below to re-enable stock trading (will trigger PDT)
        # if not trade_executed and market_hours['stocks'] and self.alpaca.connected:
        #     symbol = self.stocks[self.total_trades % len(self.stocks)]
        #     result = await self.alpaca.execute_trade(
        #         symbol, 
        #         1,  # 1 share
        #         signal['signal']
        #     )
        #     if result['success']:
        #         trade_executed = True
        #         logger.info(f"📈 STOCK Trade: {symbol} {signal['signal']} (ASI/HRM/MCTS)")
        
        if trade_executed:
            self.total_trades += 1
    
    async def main_loop(self):
        """Main trading loop"""
        logger.info("🚀 Starting ULTRATHINK-powered trading...")
        
        signal_check_interval = 5  # Check for signals every 5 seconds
        status_report_interval = 60  # Report status every minute
        last_status_time = time.time()
        
        while self.running:
            try:
                # Get ULTRATHINK signal
                signal = await self.signal_reader.get_signal()
                
                if signal:
                    logger.info(f"📡 ULTRATHINK Signal: {signal['signal']} "
                              f"@ {signal['confidence']:.1%} "
                              f"(ASI:{signal['components'].get('ASI', '?')} "
                              f"HRM:{signal['components'].get('HRM', '?')} "
                              f"MCTS:{signal['components'].get('MCTS', '?')})")
                    
                    # Execute based on signal
                    await self.execute_ultrathink_signal(signal)
                
                # Status report
                if time.time() - last_status_time > status_report_interval:
                    logger.info("="*50)
                    logger.info(f"📊 STATUS REPORT")
                    logger.info(f"   Total Trades: {self.total_trades}")
                    logger.info(f"   OANDA Orders: {len(self.oanda.orders_executed)}")
                    logger.info(f"   Alpaca Orders: {len(self.alpaca.orders_executed)}")
                    logger.info(f"   Last Signal: {self.signal_reader.last_signal}")
                    logger.info("="*50)
                    last_status_time = time.time()
                
                await asyncio.sleep(signal_check_interval)
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(10)
    
    async def run(self):
        """Run the scalper"""
        if not await self.initialize():
            logger.error("Failed to initialize")
            return
        
        try:
            await self.main_loop()
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            self.running = False
            logger.info("="*60)
            logger.info("🏁 FINAL REPORT")
            logger.info(f"   Total Trades: {self.total_trades}")
            logger.info(f"   OANDA: {len(self.oanda.orders_executed)}")
            logger.info(f"   Alpaca: {len(self.alpaca.orders_executed)}")
            logger.info("="*60)

# ============================================================================
# MAIN ENTRY
# ============================================================================

def main():
    """Main entry point"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║        ⚡ TRINITY + ULTRATHINK INTEGRATION ⚡                ║
    ║                                                              ║
    ║     🧠 ASI + HRM + MCTS = Intelligent Trading               ║
    ║     📊 Stocks + Forex + Crypto = Full Coverage              ║
    ║     🎯 Real AI Decisions + Real Execution                   ║
    ║                                                              ║
    ║     "Your original vision, properly implemented"            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    scalper = TrinityUltraThinkScalper()
    asyncio.run(scalper.run())

if __name__ == "__main__":
    main()