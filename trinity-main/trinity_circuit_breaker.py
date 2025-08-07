#!/usr/bin/env python3
"""
ULTRATHINK Circuit Breaker - Emergency Stop Loss Protection
Monitors daily P&L and stops all trading if losses exceed threshold
"""

import redis
import json
import time
import logging
import os
import sys
from datetime import datetime, timedelta
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CircuitBreaker:
    def __init__(self, loss_threshold=-200, redis_host='10.100.3.141'):
        self.loss_threshold = loss_threshold
        self.redis_client = redis.Redis(host=redis_host, port=6379, decode_responses=True)
        self.daily_pnl = 0.0
        self.trade_count = 0
        self.breaker_tripped = False
        self.last_reset = datetime.now()
        
    def calculate_daily_pnl(self):
        """Calculate P&L for today from Redis"""
        try:
            # Get all trades from last 24 hours
            trades_key = 'trinity:trades:*'
            total_pnl = 0.0
            trade_count = 0
            
            for key in self.redis_client.scan_iter(match=trades_key):
                trade_data = self.redis_client.get(key)
                if trade_data:
                    trade = json.loads(trade_data)
                    # Check if trade is from today
                    trade_time = datetime.fromisoformat(trade.get('timestamp', ''))
                    if trade_time.date() == datetime.now().date():
                        pnl = trade.get('pnl', 0)
                        total_pnl += pnl
                        trade_count += 1
            
            self.daily_pnl = total_pnl
            self.trade_count = trade_count
            return total_pnl
            
        except Exception as e:
            logging.error(f"Error calculating P&L: {e}")
            return 0.0
    
    def check_threshold(self):
        """Check if loss threshold exceeded"""
        current_pnl = self.calculate_daily_pnl()
        
        if current_pnl <= self.loss_threshold:
            if not self.breaker_tripped:
                self.trip_breaker()
            return True
        else:
            if self.breaker_tripped and self.should_reset():
                self.reset_breaker()
            return False
    
    def trip_breaker(self):
        """Emergency stop all trading"""
        logging.critical(f"🚨 CIRCUIT BREAKER TRIPPED! P&L: {self.daily_pnl:.2f} pips")
        
        # Set emergency stop flag in Redis
        self.redis_client.set('trinity:emergency_stop', '1')
        self.redis_client.set('trinity:breaker_reason', 
                             f'Daily loss exceeded: {self.daily_pnl:.2f} pips')
        
        # Stop trading processes
        try:
            # Kill trinity scalper
            subprocess.run(['pkill', '-f', 'trinity_scalper'], check=False)
            logging.info("Stopped trinity_scalper")
            
            # Kill data collector
            subprocess.run(['pkill', '-f', 'data_collector'], check=False)
            logging.info("Stopped data_collector")
            
            # Close all open positions via OANDA API
            self.close_all_positions()
            
        except Exception as e:
            logging.error(f"Error stopping processes: {e}")
        
        self.breaker_tripped = True
        
        # Send alert
        self.send_alert()
    
    def close_all_positions(self):
        """Close all open OANDA positions"""
        try:
            import oandapyV20
            from oandapyV20 import API
            from oandapyV20.endpoints.positions import PositionClose
            
            # OANDA credentials from environment
            account_id = os.getenv('OANDA_ACCOUNT_ID', 'fake_account')
            api_token = os.getenv('OANDA_API_TOKEN', 'fake_token')
            
            client = API(access_token=api_token, environment='practice')
            
            # Close all positions
            instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']
            for instrument in instruments:
                try:
                    r = PositionClose(accountID=account_id, instrument=instrument, 
                                     data={"longUnits": "ALL", "shortUnits": "ALL"})
                    client.request(r)
                    logging.info(f"Closed position: {instrument}")
                except Exception as e:
                    if 'NoSuchPosition' not in str(e):
                        logging.error(f"Error closing {instrument}: {e}")
                        
        except Exception as e:
            logging.error(f"Error closing positions: {e}")
    
    def should_reset(self):
        """Check if we should reset breaker (new trading day)"""
        now = datetime.now()
        # Reset at midnight UTC
        if now.date() > self.last_reset.date():
            return True
        return False
    
    def reset_breaker(self):
        """Reset circuit breaker for new day"""
        logging.info("Resetting circuit breaker for new trading day")
        self.breaker_tripped = False
        self.daily_pnl = 0.0
        self.trade_count = 0
        self.last_reset = datetime.now()
        
        # Clear emergency stop in Redis
        self.redis_client.delete('trinity:emergency_stop')
        self.redis_client.delete('trinity:breaker_reason')
        
        # Restart trading if configured
        if os.getenv('AUTO_RESTART_TRADING', 'false').lower() == 'true':
            self.restart_trading()
    
    def restart_trading(self):
        """Restart trading processes"""
        try:
            # Start data collector
            subprocess.Popen(['python3', '/opt/cashmachine/data_collector_real.py'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logging.info("Started data_collector")
            
            # Start trinity scalper
            subprocess.Popen(['python3', '/opt/cashmachine/trinity/trinity_scalper_v3_epic.py'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logging.info("Started trinity_scalper")
            
        except Exception as e:
            logging.error(f"Error restarting trading: {e}")
    
    def send_alert(self):
        """Send alert notification"""
        alert_msg = {
            'timestamp': datetime.now().isoformat(),
            'type': 'CIRCUIT_BREAKER',
            'pnl': self.daily_pnl,
            'trades': self.trade_count,
            'action': 'TRADING_STOPPED'
        }
        
        # Store alert in Redis
        self.redis_client.lpush('trinity:alerts', json.dumps(alert_msg))
        self.redis_client.expire('trinity:alerts', 86400)  # 24h TTL
        
        logging.critical(f"Alert sent: {alert_msg}")
    
    def monitor(self):
        """Main monitoring loop"""
        logging.info(f"Circuit Breaker started. Threshold: {self.loss_threshold} pips")
        
        while True:
            try:
                self.check_threshold()
                
                # Log status every 5 minutes
                if int(time.time()) % 300 == 0:
                    status = "TRIPPED" if self.breaker_tripped else "ACTIVE"
                    logging.info(f"Status: {status} | P&L: {self.daily_pnl:.2f} | Trades: {self.trade_count}")
                
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                logging.info("Circuit breaker stopped by user")
                break
            except Exception as e:
                logging.error(f"Monitor error: {e}")
                time.sleep(30)

if __name__ == "__main__":
    # Get configuration from environment or use defaults
    loss_threshold = float(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '-200'))
    redis_host = os.getenv('REDIS_HOST', '10.100.3.141')
    
    breaker = CircuitBreaker(loss_threshold=loss_threshold, redis_host=redis_host)
    breaker.monitor()