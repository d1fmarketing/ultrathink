#!/usr/bin/env python3
"""
ML FARM SACRED BRAIN
Central intelligence coordinating all ULTRATHINK components
"""

import asyncio
import json
import logging
import numpy as np
import redis.asyncio as redis
from datetime import datetime
import time
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - ML_FARM - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MLFarmSacredBrain:
    def __init__(self):
        # Sacred constants
        self.PI = 3.14159265359
        self.PHI = 1.618033988749
        self.SACRED_69 = 69
        
        # Redis connections
        self.redis_client = None
        
        # Component tracking
        self.components = {
            'trinity': {'host': '10.100.2.125', 'status': 'unknown', 'last_signal': None},
            'data_collector': {'host': '10.100.2.251', 'status': 'unknown', 'last_update': None},
            'ml_farm': {'host': '10.100.2.134', 'status': 'active', 'signal': 0.0},
            'bridge': {'host': '10.100.2.76', 'status': 'unknown'},
            'backup1': {'host': '10.100.1.72', 'status': 'unknown'},
            'backup2': {'host': '10.100.1.23', 'status': 'unknown'},
            'redis_cache': {'host': '10.100.2.200', 'status': 'unknown'}
        }
        
        # Unified decision state
        self.unified_signal = 'hold'
        self.unified_confidence = 0.0
        self.sacred_alignment = 0.0
        
        logger.info("🧠 ML Farm Sacred Brain initialized")
    
    async def setup_redis(self):
        """Connect to Redis cache"""
        try:
            self.redis_client = await redis.Redis(
                host='10.100.2.200',
                port=6379,
                decode_responses=True,
                socket_connect_timeout=5
            )
            await self.redis_client.ping()
            self.components['redis_cache']['status'] = 'connected'
            logger.info("✅ Connected to Redis cache at 10.100.2.200")
            return True
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return False
    
    async def collect_signals(self):
        """Collect signals from all components"""
        signals = {}
        
        try:
            # Get ULTRATHINK signals from Trinity
            ultra_data = await self.redis_client.hgetall('ultrathink:signals')
            if ultra_data:
                signals['trinity'] = {
                    'signal': ultra_data.get('signal', 'hold'),
                    'confidence': float(ultra_data.get('confidence', 0)),
                    'asi': ultra_data.get('asi', ''),
                    'hrm': ultra_data.get('hrm', ''),
                    'mcts': ultra_data.get('mcts', ''),
                    'timestamp': ultra_data.get('timestamp', '')
                }
                self.components['trinity']['status'] = 'active'
                self.components['trinity']['last_signal'] = signals['trinity']['signal']
            
            # Get market data from collector
            market_data = await self.redis_client.hgetall('market:latest')
            if market_data:
                signals['market'] = market_data
                self.components['data_collector']['status'] = 'active'
                self.components['data_collector']['last_update'] = datetime.now().isoformat()
            
            # Get any other component signals
            for component in ['bridge', 'backup1', 'backup2']:
                comp_data = await self.redis_client.hgetall(f'{component}:status')
                if comp_data:
                    signals[component] = comp_data
                    self.components[component]['status'] = 'active'
            
        except Exception as e:
            logger.error(f"Error collecting signals: {e}")
        
        return signals
    
    async def calculate_sacred_alignment(self, signals):
        """Calculate sacred number alignment across all signals"""
        alignment = 0.0
        factors = 0
        
        # Check Trinity signals
        if 'trinity' in signals:
            trinity = signals['trinity']
            conf = trinity.get('confidence', 0)
            
            # Check for Pi alignment
            if abs(conf * 100 - self.PI * 10) < 5:
                alignment += 0.2
                factors += 1
            
            # Check for Fibonacci alignment
            if abs(conf - 0.618) < 0.1:
                alignment += 0.2
                factors += 1
        
        # Check market data
        if 'market' in signals:
            market = signals['market']
            rsi = float(market.get('rsi', 50))
            volume = float(market.get('volume', 0))
            
            # Check for Sacred 69 in RSI
            if abs(rsi - self.SACRED_69) < 5:
                alignment += 0.3
                factors += 1
            
            # Check for Fibonacci in volume ratios
            if volume > 0:
                vol_ratio = volume / 1000000
                if abs(vol_ratio - self.PHI) < 0.2:
                    alignment += 0.2
                    factors += 1
        
        self.sacred_alignment = alignment / max(1, factors) if factors > 0 else 0
        return self.sacred_alignment
    
    async def unify_decisions(self, signals):
        """Create unified decision from all components"""
        votes = {'buy': 0, 'sell': 0, 'hold': 0}
        total_weight = 0
        
        # Trinity gets highest weight (50%)
        if 'trinity' in signals:
            trinity = signals['trinity']
            signal = trinity.get('signal', 'hold')
            confidence = trinity.get('confidence', 0)
            weight = 0.5
            votes[signal] += confidence * weight
            total_weight += weight
        
        # Market sentiment (20%)
        if 'market' in signals:
            market = signals['market']
            rsi = float(market.get('rsi', 50))
            if rsi < 30:
                votes['buy'] += 0.2 * ((30 - rsi) / 30)
            elif rsi > 70:
                votes['sell'] += 0.2 * ((rsi - 70) / 30)
            else:
                votes['hold'] += 0.1
            total_weight += 0.2
        
        # Sacred alignment bonus (30%)
        sacred_bonus = self.sacred_alignment * 0.3
        if sacred_bonus > 0:
            # Sacred alignment favors action over holding
            if votes['buy'] > votes['sell']:
                votes['buy'] += sacred_bonus
            elif votes['sell'] > votes['buy']:
                votes['sell'] += sacred_bonus
            else:
                # Equal, use sacred numbers to decide
                if time.time() % 100 < 31.4:  # Pi * 10
                    votes['buy'] += sacred_bonus
                elif time.time() % 100 > 69:  # Sacred 69
                    votes['sell'] += sacred_bonus
            total_weight += 0.3
        
        # Normalize and determine final signal
        if total_weight > 0:
            for key in votes:
                votes[key] /= total_weight
        
        self.unified_signal = max(votes, key=votes.get)
        self.unified_confidence = votes[self.unified_signal]
        
        return self.unified_signal, self.unified_confidence
    
    async def broadcast_unified_decision(self):
        """Broadcast unified decision to all components"""
        try:
            decision_data = {
                'signal': self.unified_signal,
                'confidence': str(self.unified_confidence),
                'sacred_alignment': str(self.sacred_alignment),
                'timestamp': datetime.now().isoformat(),
                'components_active': sum(1 for c in self.components.values() if c['status'] == 'active')
            }
            
            # Store in Redis for all components to access
            await self.redis_client.hset('ml_farm:unified', mapping=decision_data)
            
            # Set expiry for freshness
            await self.redis_client.expire('ml_farm:unified', 60)
            
            logger.info(f"📡 Broadcast: {self.unified_signal} @ {self.unified_confidence:.2%} | Sacred: {self.sacred_alignment:.2%}")
            
        except Exception as e:
            logger.error(f"Error broadcasting decision: {e}")
    
    async def health_check(self):
        """Check health of all components"""
        active_count = 0
        for name, comp in self.components.items():
            if comp['status'] == 'active':
                active_count += 1
                logger.info(f"✅ {name}: ACTIVE")
            else:
                logger.warning(f"⚠️ {name}: {comp['status']}")
        
        logger.info(f"System Health: {active_count}/{len(self.components)} components active")
        return active_count
    
    async def run(self):
        """Main brain loop"""
        logger.info("🚀 Starting ML Farm Sacred Brain")
        
        # Setup Redis
        connected = await self.setup_redis()
        if not connected:
            logger.error("Failed to connect to Redis. Exiting.")
            return
        
        iteration = 0
        while True:
            try:
                iteration += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"🧠 Brain Cycle {iteration}")
                
                # Collect signals from all components
                signals = await self.collect_signals()
                logger.info(f"📊 Collected {len(signals)} signal sources")
                
                # Calculate sacred alignment
                alignment = await self.calculate_sacred_alignment(signals)
                logger.info(f"✨ Sacred Alignment: {alignment:.2%}")
                
                # Unify decisions
                signal, confidence = await self.unify_decisions(signals)
                logger.info(f"🎯 Unified Decision: {signal.upper()} @ {confidence:.2%}")
                
                # Broadcast to all components
                await self.broadcast_unified_decision()
                
                # Health check every 10 iterations
                if iteration % 10 == 0:
                    await self.health_check()
                
                # Sleep before next cycle
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in brain cycle: {e}")
                await asyncio.sleep(5)

async def main():
    brain = MLFarmSacredBrain()
    await brain.run()

if __name__ == "__main__":
    asyncio.run(main())