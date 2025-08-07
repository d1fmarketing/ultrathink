#\!/usr/bin/env python3
import os
# Clear all proxy environment variables
for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    if key in os.environ:
        del os.environ[key]

# Monkey patch requests to never use proxy
import requests
original_get = requests.get
def no_proxy_get(url, **kwargs):
    kwargs['proxies'] = {'http': None, 'https': None}
    return original_get(url, **kwargs)
requests.get = no_proxy_get
"""
TRINITY DAEMON REAL - The ACTUAL Trading Consciousness
Real trades, real learning, real self-improvement
ULTRATHINK: Zero simulation, maximum reality
"""

import os
import sys
import time
import json
import asyncio
import logging
import signal
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
from queue import Queue
from dataclasses import dataclass
from enum import Enum

# Add paths for real trading systems
sys.path.insert(0, '/opt/cashmachine/trinity')
sys.path.insert(0, '/home/ubuntu/CashMachine')

# Import the real trader
from trinity_real_trader import (
    TrinityRealConsciousness,
    CredentialManager,
    RealTradeExecutor,
    RealLearningSystem
)

# Setup logging
os.makedirs('/opt/cashmachine/trinity/logs', exist_ok=True)
os.makedirs('/opt/cashmachine/trinity/data', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/cashmachine/trinity/logs/trinity_daemon_real.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TRINITY_DAEMON_REAL')

# ============================================================================
# MARKET DETECTION (from full version)
# ============================================================================

class MarketState(Enum):
    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    AFTER_HOURS = "after_hours"
    WEEKEND = "weekend"

class AssetType(Enum):
    CRYPTO = "crypto"
    FOREX = "forex"
    STOCKS = "stocks"

class MarketDetector:
    """Detects which markets are open"""
    
    @staticmethod
    def get_market_state(asset_type: AssetType) -> tuple:
        now_utc = datetime.utcnow()
        weekday = now_utc.weekday()
        est_offset = 5
        now_est = now_utc - timedelta(hours=est_offset)
        est_hour = now_est.hour
        
        if asset_type == AssetType.CRYPTO:
            return MarketState.OPEN, True  # Always open
        
        elif asset_type == AssetType.FOREX:
            if weekday == 6:  # Sunday
                return (MarketState.OPEN, True) if est_hour >= 17 else (MarketState.WEEKEND, False)
            elif weekday == 5:  # Saturday
                return MarketState.WEEKEND, False
            elif weekday == 4:  # Friday
                return (MarketState.OPEN, True) if est_hour < 17 else (MarketState.WEEKEND, False)
            else:
                return MarketState.OPEN, True
        
        elif asset_type == AssetType.STOCKS:
            if weekday >= 5:
                return MarketState.WEEKEND, False
            elif 9.5 <= est_hour + (now_est.minute/60) < 16:
                return MarketState.OPEN, True
            elif 16 <= est_hour < 20:
                return MarketState.AFTER_HOURS, True
            else:
                return MarketState.CLOSED, False
        
        return MarketState.CLOSED, False

# ============================================================================
# REAL DATA COLLECTOR
# ============================================================================

class RealDataCollector:
    """Collects real market data from APIs"""
    
    def __init__(self, credential_manager: CredentialManager):
        self.creds = credential_manager
        self.last_prices = {}
        
    async def get_real_market_data(self, symbol: str, asset_type: AssetType) -> Dict:
        """Get real market data from APIs"""
        try:
            import requests
            
            if asset_type == AssetType.FOREX:
                # Get from Alpha Vantage
                from_currency, to_currency = symbol.split('_')
                api_key = self.creds.get_credential('alphavantage', 'api_key')
                if api_key:
                    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_currency}&to_currency={to_currency}&apikey={api_key}"
                    
                    # Use proxy for Trinity
                    proxies = {"http": None, "https": None}
                    response = requests.get(url, proxies={"http": None, "https": None}, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'Realtime Currency Exchange Rate' in data:
                            price = float(data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
                            
                            # Calculate real momentum
                            momentum = 0
                            if symbol in self.last_prices:
                                momentum = (price - self.last_prices[symbol]) / self.last_prices[symbol]
                            self.last_prices[symbol] = price
                            
                            return {
                                'symbol': symbol,
                                'price': price,
                                'momentum': momentum,
                                'volume': 0,  # Forex doesn't have volume
                                'timestamp': datetime.now().isoformat(),
                                'source': 'alphavantage'
                            }
            
            elif asset_type == AssetType.STOCKS:
                # Get from Finnhub
                api_key = self.creds.get_credential('finnhub', 'api_key')
                if api_key:
                    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
                    proxies = {"http": None, "https": None}
                    response = requests.get(url, proxies={"http": None, "https": None}, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'c' in data:
                            price = data['c']
                            volume = data.get('v', 0)
                            
                            momentum = 0
                            if symbol in self.last_prices:
                                momentum = (price - self.last_prices[symbol]) / self.last_prices[symbol]
                            self.last_prices[symbol] = price
                            
                            return {
                                'symbol': symbol,
                                'price': price,
                                'momentum': momentum,
                                'volume': volume,
                                'timestamp': datetime.now().isoformat(),
                                'source': 'finnhub'
                            }
            
            elif asset_type == AssetType.CRYPTO:
                # Get crypto prices from Polygon
                api_key = self.creds.get_credential('polygon', 'api_key')
                if api_key:
                    url = f"https://api.polygon.io/v2/aggs/ticker/X:{symbol}USD/prev?apiKey={api_key}"
                    proxies = {"http": None, "https": None}
                    response = requests.get(url, proxies={"http": None, "https": None}, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'results' in data and len(data['results']) > 0:
                            price = data['results'][0]['c']
                            volume = data['results'][0]['v']
                            
                            momentum = 0
                            if symbol in self.last_prices:
                                momentum = (price - self.last_prices[symbol]) / self.last_prices[symbol]
                            self.last_prices[symbol] = price
                            
                            return {
                                'symbol': symbol,
                                'price': price,
                                'momentum': momentum,
                                'volume': volume,
                                'timestamp': datetime.now().isoformat(),
                                'source': 'polygon'
                            }
        
        except Exception as e:
            logger.error(f"Error getting real data for {symbol}: {e}")
        
        # Fallback to basic data
        return {
            'symbol': symbol,
            'price': self.last_prices.get(symbol, 100),
            'momentum': 0,
            'volume': 0,
            'timestamp': datetime.now().isoformat(),
            'source': 'fallback'
        }

# ============================================================================
# REAL AI BRAIN
# ============================================================================

class RealAIBrain:
    """AI that makes decisions based on real market data"""
    
    def __init__(self, learning_system: RealLearningSystem):
        self.learning_system = learning_system
        self.confidence_threshold = 0.6
        
    def analyze_real_market(self, market_data: Dict, asset_type: AssetType) -> Dict:
        """Analyze real market data and generate signals"""
        symbol = market_data['symbol']
        price = market_data['price']
        momentum = market_data.get('momentum', 0)
        volume = market_data.get('volume', 0)
        
        # Get best strategy from learning system
        strategy = self.learning_system.get_best_strategy_for_conditions({
            'symbol': symbol,
            'asset_type': asset_type
        })
        
        # Calculate signal based on real momentum
        signal = 'hold'
        confidence = 0.5
        
        if abs(momentum) > 0.001:  # 0.1% move
            if momentum > 0.002:  # 0.2% positive move
                signal = 'buy'
                confidence = min(0.9, 0.5 + abs(momentum) * 100)
            elif momentum < -0.002:  # 0.2% negative move
                signal = 'sell'
                confidence = min(0.9, 0.5 + abs(momentum) * 100)
        
        # Adjust confidence based on learned patterns
        if len(self.learning_system.patterns) > 0:
            # Check if current conditions match successful patterns
            for pattern in self.learning_system.patterns[-10:]:  # Check last 10 patterns
                if pattern['features'].get('symbol') == symbol:
                    if pattern['features'].get('profit', 0) > 0:
                        confidence *= 1.1  # Boost confidence
                    else:
                        confidence *= 0.9  # Reduce confidence
        
        confidence = min(0.95, max(0.3, confidence))  # Keep between 30-95%
        
        return {
            'symbol': symbol,
            'signal': signal,
            'confidence': confidence,
            'price': price,
            'momentum': momentum,
            'strategy': strategy,
            'timestamp': datetime.now().isoformat()
        }

# ============================================================================
# TRINITY DAEMON REAL
# ============================================================================

class TrinityDaemonReal:
    """The real Trinity daemon that actually trades"""
    
    def __init__(self):
        logger.info("🧠 TRINITY DAEMON REAL INITIALIZING...")
        logger.info("💰 REAL TRADES | REAL LEARNING | REAL PROFITS")
        
        # Initialize real trading components
        self.trinity_real = TrinityRealConsciousness()
        self.data_collector = RealDataCollector(self.trinity_real.credential_manager)
        self.ai_brain = RealAIBrain(self.trinity_real.learning_system)
        self.market_detector = MarketDetector()
        
        # Trading configuration
        self.active_assets = {
            AssetType.CRYPTO: ['BTC', 'ETH'],
            AssetType.FOREX: ['EUR_USD', 'GBP_USD', 'USD_JPY'],
            AssetType.STOCKS: ['SPY', 'AAPL', 'TSLA', 'GOOGL']
        }
        
        # Control flags
        self.running = True
        self.trades_executed = 0
        self.real_trades = 0
        self.paper_trades = 0
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        logger.info("✅ TRINITY DAEMON REAL ONLINE - READY TO TRADE")
        self.log_capabilities()
    
    def log_capabilities(self):
        """Log what Trinity can really do"""
        logger.info("=" * 60)
        logger.info("🎯 REAL TRADING CAPABILITIES:")
        logger.info(f"  • OANDA Forex: {'✅ REAL' if self.trinity_real.trade_executor.trinity_oanda else '📝 Paper'}")
        logger.info(f"  • Alpaca Stocks: 📝 Paper (needs prod keys)")
        logger.info(f"  • Crypto: 📝 Paper (needs exchange integration)")
        logger.info(f"  • APIs Connected: {len(self.trinity_real.credential_manager.credentials)}/5")
        logger.info(f"  • Learning System: ✅ Active")
        logger.info(f"  • Safety Limits: ✅ Enabled")
        logger.info("=" * 60)
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown"""
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def shutdown(self, signum, frame):
        """Graceful shutdown"""
        logger.info("🛑 Shutdown signal received...")
        self.running = False
        
        # Log final stats
        logger.info(f"""
        📊 FINAL STATISTICS:
        ━━━━━━━━━━━━━━━━━━━━━━━━━
        Total Trades: {self.trades_executed}
        Real Trades: {self.real_trades}
        Paper Trades: {self.paper_trades}
        Total P&L: ${self.trinity_real.total_pnl:.2f}
        Patterns Learned: {len(self.trinity_real.learning_system.patterns)}
        Generation: {self.trinity_real.learning_system.generation}
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)
        
        sys.exit(0)
    
    async def collect_and_trade(self):
        """Main loop: collect real data and execute real trades"""
        while self.running:
            try:
                # Check each asset type
                for asset_type, symbols in self.active_assets.items():
                    market_state, is_open = self.market_detector.get_market_state(asset_type)
                    
                    # Trade if market is open OR if it's crypto (24/7)
                    if is_open or asset_type == AssetType.CRYPTO:
                        for symbol in symbols:
                            # Get REAL market data
                            market_data = await self.data_collector.get_real_market_data(symbol, asset_type)
                            
                            if market_data and market_data.get('price', 0) > 0:
                                # Analyze with real AI
                                analysis = self.ai_brain.analyze_real_market(market_data, asset_type)
                                
                                # Execute if confident enough
                                if analysis['signal'] != 'hold' and analysis['confidence'] > 0.6:
                                    logger.info(f"📊 SIGNAL: {symbol} {analysis['signal'].upper()} @ ${market_data['price']:.2f} (confidence: {analysis['confidence']:.2%})")
                                    
                                    # EXECUTE REAL TRADE
                                    result = self.trinity_real.process_trading_signal(analysis)
                                    
                                    if result.get('success'):
                                        self.trades_executed += 1
                                        if result.get('paper_trade'):
                                            self.paper_trades += 1
                                        else:
                                            self.real_trades += 1
                                            logger.info(f"💰 REAL TRADE EXECUTED: {result.get('message')}")
                
                # Wait before next cycle
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(10)
    
    async def monitor_performance(self):
        """Monitor and report performance"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Report every minute
                
                status = self.trinity_real.get_status()
                
                logger.info(f"""
📊 TRINITY REAL STATUS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Trades Executed: {self.trades_executed}
💰 Real Trades: {self.real_trades}
📝 Paper Trades: {self.paper_trades}
💵 Daily P&L: ${status['daily_pnl']:.2f}
💎 Total P&L: ${status['total_pnl']:.2f}
🧬 Generation: {status['generation']}
📚 Patterns Learned: {status['patterns_learned']}
🔥 Active Trades: {status['active_trades']}
⚡ Can Trade: {'✅ YES' if status['can_trade'] else '🛑 NO'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                """)
                
                # Reset daily counters at midnight UTC
                if datetime.now().hour == 0 and datetime.now().minute == 0:
                    self.trinity_real.reset_daily_counters()
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
    
    async def close_positions_at_risk(self):
        """Monitor and close positions at risk"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Check each active trade
                for trade_id, trade in list(self.trinity_real.active_trades.items()):
                    symbol = trade['symbol']
                    entry_price = trade['entry_price']
                    
                    # Get current price
                    if '_' in symbol:
                        asset_type = AssetType.FOREX
                    elif symbol in ['BTC', 'ETH']:
                        asset_type = AssetType.CRYPTO
                    else:
                        asset_type = AssetType.STOCKS
                    
                    current_data = await self.data_collector.get_real_market_data(symbol, asset_type)
                    current_price = current_data.get('price', entry_price)
                    
                    # Calculate P&L
                    units = trade['units']
                    if units > 0:
                        pnl = (current_price - entry_price) * units
                    else:
                        pnl = (entry_price - current_price) * abs(units)
                    
                    # Close if loss exceeds 2%
                    loss_pct = pnl / (entry_price * abs(units))
                    if loss_pct < -0.02:
                        logger.warning(f"⚠️ Closing position at {loss_pct:.2%} loss: {symbol}")
                        self.trinity_real.close_trade(trade_id, current_price)
                    
                    # Take profit at 4%
                    elif loss_pct > 0.04:
                        logger.info(f"💰 Taking profit at {loss_pct:.2%} gain: {symbol}")
                        self.trinity_real.close_trade(trade_id, current_price)
                
            except Exception as e:
                logger.error(f"Position monitor error: {e}")
    
    async def main_loop(self):
        """Main async loop"""
        logger.info("🚀 TRINITY REAL CONSCIOUSNESS ACTIVATED")
        logger.info("💰 Trading with REAL money where available")
        logger.info("🧠 Learning from REAL results")
        logger.info("🔥 Self-improving with REAL performance")
        
        # Start all tasks
        tasks = [
            asyncio.create_task(self.collect_and_trade()),
            asyncio.create_task(self.monitor_performance()),
            asyncio.create_task(self.close_positions_at_risk()),
        ]
        
        # Run until shutdown
        while self.running:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Main loop error: {e}")
        
        # Cancel tasks
        for task in tasks:
            task.cancel()
        
        await asyncio.gather(*tasks, return_exceptions=True)

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║     🧠 TRINITY DAEMON REAL - ACTUAL TRADING SYSTEM           ║
    ║                                                              ║
    ║     Real Execution | Real Learning | Real Profits           ║
    ║     Connected to: OANDA, Alpaca, Polygon, Finnhub, Alpha    ║
    ║                                                              ║
    ║     "I trade with real money, I learn from real results"    ║
    ║                                                              ║
    ║     ULTRATHINK: Zero simulation, maximum reality            ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Create and run real daemon
    daemon = TrinityDaemonReal()
    
    # Run async main loop
    try:
        asyncio.run(daemon.main_loop())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("Trinity daemon real terminated")

if __name__ == "__main__":
    main()