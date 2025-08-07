#!/usr/bin/env python3
"""
Multi-API Data Collector - Uses multiple free APIs to ensure data availability
While AlphaVantage premium key issue is being resolved
"""

import asyncio
import aiohttp
import time
import json
import redis.asyncio as redis
import logging
from datetime import datetime
from typing import Dict, List, Optional
import yfinance as yf
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiAPIDataCollector:
    def __init__(self):
        self.redis_client = None
        
        # Multiple API sources for redundancy
        self.apis = {
            'yahoo': {
                'enabled': True,
                'rate_limit': 0,  # No rate limit
                'last_call': 0
            },
            'coingecko': {
                'enabled': True,
                'rate_limit': 2,  # 30/minute free
                'last_call': 0
            },
            'twelvedata': {
                'enabled': True,
                'key': 'demo',  # Free tier available
                'rate_limit': 5,  # 12/minute free
                'last_call': 0
            },
            'alphavantage': {
                'enabled': False,  # DISABLED until premium key fixed
                'key': 'WI9OSK9WTI10FAL8',
                'rate_limit': 86400,  # Effectively disabled
                'last_call': 0
            }
        }
        
        self.symbols = {
            'stocks': ['SPY', 'AAPL', 'GOOGL', 'MSFT', 'NVDA', 'TSLA', 'META', 'QQQ', 'AMC', 'GME'],
            'crypto': ['BTC', 'ETH', 'SOL', 'DOGE'],
            'forex': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']
        }
    
    async def setup_redis(self):
        """Connect to Redis"""
        try:
            self.redis_client = await redis.Redis(
                host='10.100.2.200',
                port=6379,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("✅ Connected to Redis")
            return True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return False
    
    def fetch_yahoo(self, symbol: str) -> Optional[Dict]:
        """Fetch from Yahoo Finance (no API key needed)"""
        try:
            # Handle forex symbols
            yahoo_symbol = symbol
            if symbol == 'EUR_USD':
                yahoo_symbol = 'EURUSD=X'
            elif symbol == 'GBP_USD':
                yahoo_symbol = 'GBPUSD=X'
            elif symbol == 'USD_JPY':
                yahoo_symbol = 'USDJPY=X'
            elif symbol in ['BTC', 'ETH', 'SOL', 'DOGE']:
                yahoo_symbol = f"{symbol}-USD"
            
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info
            
            # Get current price
            price = None
            if 'regularMarketPrice' in info:
                price = info['regularMarketPrice']
            elif 'currentPrice' in info:
                price = info['currentPrice']
            elif 'ask' in info and info['ask']:
                price = info['ask']
            elif 'bid' in info and info['bid']:
                price = info['bid']
            else:
                # Try fast_info for crypto
                try:
                    fast = ticker.fast_info
                    price = fast.get('lastPrice') or fast.get('regularMarketPrice')
                except:
                    pass
            
            if price and price > 0:
                return {
                    'symbol': symbol,
                    'price': float(price),
                    'source': 'yahoo',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.debug(f"Yahoo error for {symbol}: {e}")
        
        return None
    
    async def fetch_coingecko(self, session: aiohttp.ClientSession, symbol: str) -> Optional[Dict]:
        """Fetch crypto prices from CoinGecko"""
        if symbol not in ['BTC', 'ETH', 'SOL', 'DOGE']:
            return None
        
        current_time = time.time()
        if current_time - self.apis['coingecko']['last_call'] < self.apis['coingecko']['rate_limit']:
            return None
        
        crypto_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'DOGE': 'dogecoin'
        }
        
        try:
            url = 'https://api.coingecko.com/api/v3/simple/price'
            params = {
                'ids': crypto_map[symbol],
                'vs_currencies': 'usd'
            }
            
            async with session.get(url, params=params, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if crypto_map[symbol] in data:
                        price = data[crypto_map[symbol]]['usd']
                        self.apis['coingecko']['last_call'] = current_time
                        
                        return {
                            'symbol': symbol,
                            'price': price,
                            'source': 'coingecko',
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            logger.debug(f"CoinGecko error for {symbol}: {e}")
        
        return None
    
    async def fetch_twelvedata(self, session: aiohttp.ClientSession, symbol: str) -> Optional[Dict]:
        """Fetch from Twelve Data API (free tier)"""
        current_time = time.time()
        if current_time - self.apis['twelvedata']['last_call'] < self.apis['twelvedata']['rate_limit']:
            return None
        
        try:
            url = 'https://api.twelvedata.com/price'
            params = {
                'symbol': symbol,
                'apikey': self.apis['twelvedata']['key']
            }
            
            async with session.get(url, params=params, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if 'price' in data:
                        price = float(data['price'])
                        self.apis['twelvedata']['last_call'] = current_time
                        
                        return {
                            'symbol': symbol,
                            'price': price,
                            'source': 'twelvedata',
                            'timestamp': datetime.now().isoformat()
                        }
        except Exception as e:
            logger.debug(f"TwelveData error for {symbol}: {e}")
        
        return None
    
    async def collect_symbol_data(self, session: aiohttp.ClientSession, symbol: str):
        """Collect data for a symbol from multiple sources"""
        results = []
        
        # Try Yahoo first (no rate limit)
        yahoo_result = self.fetch_yahoo(symbol)
        if yahoo_result:
            results.append(yahoo_result)
        
        # Try CoinGecko for crypto
        if symbol in ['BTC', 'ETH', 'SOL', 'DOGE']:
            gecko_result = await self.fetch_coingecko(session, symbol)
            if gecko_result:
                results.append(gecko_result)
        
        # Try TwelveData for stocks
        if symbol in self.symbols['stocks']:
            twelve_result = await self.fetch_twelvedata(session, symbol)
            if twelve_result:
                results.append(twelve_result)
        
        if results:
            # Average prices from multiple sources
            avg_price = sum(r['price'] for r in results) / len(results)
            sources = ', '.join(r['source'] for r in results)
            
            # Store in Redis
            await self.redis_client.hset(f'market:{symbol}', mapping={
                'price': str(avg_price),
                'sources': sources,
                'source_count': len(results),
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"✅ {symbol}: ${avg_price:.2f} from {len(results)} sources ({sources})")
            return True
        
        return False
    
    async def run(self):
        """Main collection loop"""
        if not await self.setup_redis():
            logger.error("Cannot start without Redis")
            return
        
        logger.info("="*60)
        logger.info("💎 MULTI-API DATA COLLECTOR")
        logger.info("✅ Yahoo Finance - UNLIMITED")
        logger.info("✅ CoinGecko - 30/minute")
        logger.info("✅ TwelveData - 12/minute")
        logger.info("❌ AlphaVantage - DISABLED (premium key issue)")
        logger.info("="*60)
        
        async with aiohttp.ClientSession() as session:
            cycle = 0
            while True:
                try:
                    cycle += 1
                    all_symbols = (
                        self.symbols['stocks'] + 
                        self.symbols['crypto']
                    )
                    
                    # Collect data for all symbols
                    tasks = []
                    for symbol in all_symbols:
                        tasks.append(self.collect_symbol_data(session, symbol))
                    
                    results = await asyncio.gather(*tasks)
                    success_count = sum(1 for r in results if r)
                    
                    logger.info(f"📊 Cycle {cycle}: Collected {success_count}/{len(all_symbols)} symbols")
                    
                    # Forex data (Yahoo only)
                    for forex in ['EUR_USD', 'GBP_USD', 'USD_JPY']:
                        yahoo_result = self.fetch_yahoo(forex)
                        if yahoo_result:
                            await self.redis_client.hset(f'market:{forex}', mapping={
                                'price': str(yahoo_result['price']),
                                'sources': 'yahoo',
                                'source_count': 1,
                                'timestamp': datetime.now().isoformat()
                            })
                            logger.info(f"✅ {forex}: ${yahoo_result['price']:.4f} from Yahoo")
                    
                    # Sleep 10 seconds between cycles
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    logger.error(f"Collection error: {e}")
                    await asyncio.sleep(30)

if __name__ == "__main__":
    # Install yfinance if not present
    try:
        import yfinance
    except ImportError:
        import subprocess
        subprocess.check_call(['pip3', 'install', 'yfinance'])
    
    collector = MultiAPIDataCollector()
    asyncio.run(collector.run())