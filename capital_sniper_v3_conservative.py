#!/usr/bin/env python3
"""
Capital Sniper v3.0 CONSERVATIVE - Python EA for MetaTrader5
===========================================================

Conservative hardened version of Capital Sniper v3.0 with Robert's risk management mandate:
"Leave out anything that would put my strategy at risk. Close out only in profit. 
Limit entries that put you in risk. Keep very limited drawdowns."

Key Conservative Modifications:
- Ultra-tight risk parameters (0.50% risk, 2% daily DD limit)
- Single position per pair (no stacking)
- Profit-only exits with faster breakeven
- Minimum 0.7 confidence threshold
- Time-based position closure
- Anti-loss logic and floating P&L checks
- Tighter spreads and session times
- Enhanced winner protection

Author: OpenClaw AI Assistant
Version: 3.0 CONSERVATIVE
License: Proprietary
Reference: Robert's 2023 trading style (0.06-0.09 lots, diversified pairs, $4-38 wins)
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import traceback
import signal
import sys

# =============================================================================
# CONFIGURATION SECTION - CONSERVATIVE PARAMETERS
# =============================================================================

CONFIG = {
    # CONSERVATIVE RISK MANAGEMENT
    'RISK': {
        'risk_percent': 0.50,           # REDUCED from 0.75% - Robert's ultra-conservative approach
        'max_daily_drawdown': 2.0,      # REDUCED from 3.0% - tighter daily limit
        'max_weekly_drawdown': 4.0,     # REDUCED from 6.0% - tighter weekly limit
        'max_positions_total': 4,       # REDUCED from 6 - fewer simultaneous positions
        'max_positions_per_symbol': 1,  # REDUCED from 3 - ONE position per pair like 2023 style
        'max_sessions_per_symbol': 2,   # REDUCED from 3 - limited session entries
        'consecutive_loss_limit': 2,    # KEEP at 2 - reasonable limit
        'consecutive_loss_pause_hours': 2, # INCREASED from 1 - longer pause after losses
    },
    
    # CONSERVATIVE STRATEGY PARAMETERS
    'STRATEGY': {
        'fvg_deviation_pips': 3,        # TIGHTER from 5 - more precise detection
        'exhaustion_threshold_forex': 20, # KEEP same - reasonable limit
        'exhaustion_threshold_gold': 30,   # KEEP same - reasonable for gold
        'wyckoff_confirmation': True,   # ENABLED - extra confirmation required
        'wyckoff_lookback': 3,          # KEEP same
        'stack_count': 1,               # NO STACKING - single clean entries only
        'stack_offset_points': 0,       # DISABLED - no stacking offset needed
        'sl_buffer_pips': 2,            # KEEP same - reasonable buffer
        'min_rr_ratio': 3.0,            # INCREASED from 2.0 - only high-reward setups
        'displacement_confirmation': True, # ENABLED - need momentum proof
        'displacement_atr_mult': 1.2,   # KEEP same
        'market_order_fallback_bars': 0, # DISABLED - no market order fallback
        'min_confidence_threshold': 0.7, # NEW - minimum confidence filter
    },
    
    # SMC/ICT INTEGRATION (Enhanced filters)
    'SMC': {
        'enable_htf_bias': True,        # KEEP enabled - good filter
        'htf_timeframe': mt5.TIMEFRAME_H1, # KEEP same
        'ltf_timeframe': mt5.TIMEFRAME_M5, # KEEP same
        'enable_premium_discount': True, # KEEP enabled - good filter
        'enable_liquidity_sweep': True, # KEEP enabled - good filter
        'atr_period': 14,               # KEEP same
        'structure_lookback': 20,       # KEEP same
    },
    
    # CONSERVATIVE TRADING SESSIONS
    'SESSIONS': {
        'london_start': 8,              # TRIMMED from 7 - avoid early volatility
        'london_end': 15,               # TRIMMED from 16 - avoid late session risk
        'ny_start': 13,                 # TRIMMED from 12 - avoid early volatility
        'ny_end': 20,                   # TRIMMED from 21 - avoid late session risk
        'gold_session_start': 13,       # OVERLAP only for gold
        'gold_session_end': 16,         # OVERLAP only for gold
        'session_warmup_minutes': 15,   # NEW - no trading first 15min of session
        'session_cooldown_minutes': 30, # NEW - no trading last 30min of session
    },
    
    # TIGHTER SYMBOLS AND SPREADS
    'SYMBOLS': {
        'EURUSD': {'max_spread': 1.0, 'point_multiplier': 10000},  # TIGHTER from 1.5
        'GBPUSD': {'max_spread': 1.0, 'point_multiplier': 10000},  # TIGHTER from 2.0
        'USDJPY': {'max_spread': 1.0, 'point_multiplier': 100},    # TIGHTER from 1.5
        'USDCAD': {'max_spread': 1.5, 'point_multiplier': 10000},  # TIGHTER from 2.0
        'AUDUSD': {'max_spread': 1.5, 'point_multiplier': 10000},  # TIGHTER from 2.0
        'NZDUSD': {'max_spread': 1.5, 'point_multiplier': 10000},  # TIGHTER from 2.5
        'USDCHF': {'max_spread': 1.5, 'point_multiplier': 10000},  # TIGHTER from 2.0
        'EURJPY': {'max_spread': 1.5, 'point_multiplier': 100},    # TIGHTER from 2.5
        'GBPJPY': {'max_spread': 1.5, 'point_multiplier': 100},    # TIGHTER from 3.0
        'XAUUSD': {'max_spread': 3.0, 'point_multiplier': 100},    # WIDER for gold spreads
    },
    
    # PROFIT-FOCUSED TRADE MANAGEMENT
    'TRADE_MGMT': {
        'breakeven_trigger_r': 0.75,    # FASTER from 1.0 - move to BE quicker
        'partial_close_1_r': 1.5,       # EARLIER from 2.0 - take profit sooner  
        'partial_close_1_pct': 0.40,    # MORE from 0.3 - lock 40% profit
        'partial_close_2_r': 2.5,       # EARLIER from 3.0
        'partial_close_2_pct': 0.30,    # SAME - take another 30%
        'trailing_start_r': 2.0,        # KEEP same but with tighter trail
        'trailing_atr_mult': 1.0,       # TIGHTER from 1.5 - closer trailing
        'winner_protection_trigger': 1.0, # EARLIER from 1.5 - protect winners sooner
        'winner_protection_exit': 0.3,  # EARLIER from 0.5 - exit sooner if reversal
        'tp1_target_r': 1.5,            # EARLIER from 2.0
        'tp2_target_r': 2.5,            # EARLIER from 3.0
        'tp3_target_r': 4.0,            # EARLIER from 5.0
        'max_position_hours': 6,        # NEW - max 6 hours regardless
        'profit_exit_hours': 4,         # NEW - exit if profitable after 4 hours
        'anti_loss_sl_tighten': 0.3,    # NEW - tighten SL by 30% if below -0.5R
    },
    
    # SYSTEM SETTINGS
    'SYSTEM': {
        'magic_number_base': 987654,    # KEEP same
        'loop_delay_seconds': 1,        # KEEP same
        'retry_attempts': 3,            # KEEP same
        'retry_delay_ms': 500,          # KEEP same
        'log_level': 'INFO',            # KEEP same
        'log_to_file': True,            # KEEP same
        'connection_timeout': 60000,    # KEEP same
    },
    
    # NEW - ANTI-LOSS SETTINGS
    'ANTI_LOSS': {
        'check_floating_pnl': True,     # Check floating P&L before new trades
        'min_win_rate_threshold': 50,   # Pause if win rate drops below 50%
        'win_rate_lookback': 10,        # Check last 10 trades for win rate
        'spread_protection_multiplier': 2.0, # Don't modify if spread > 2x normal
    }
}

# =============================================================================
# GLOBAL VARIABLES AND CLASSES
# =============================================================================

class TradeState:
    """Track trade states and session data with conservative enhancements"""
    def __init__(self):
        self.session_data = {}
        self.equity_start = 0.0
        self.weekly_equity_start = 0.0
        self.floating_peak = 0.0
        self.stop_all_trading = False
        self.consecutive_losses = 0
        self.pause_until = None
        self.last_session_reset = {}
        self.positions_data = {}
        # NEW CONSERVATIVE TRACKING
        self.trade_history = []  # Track last 10 trades for win rate
        self.daily_summary = {}  # Daily trading summary
        
    def reset_session_counters(self, symbol: str, session: str):
        """Reset session counters for a symbol"""
        if symbol not in self.session_data:
            self.session_data[symbol] = {'london': 0, 'ny': 0}
        self.session_data[symbol][session] = 0
        
    def increment_session_counter(self, symbol: str, session: str, count: int = 1):
        """Increment session counter"""
        if symbol not in self.session_data:
            self.session_data[symbol] = {'london': 0, 'ny': 0}
        self.session_data[symbol][session] += count
        
    def get_session_count(self, symbol: str, session: str) -> int:
        """Get current session count"""
        if symbol not in self.session_data:
            return 0
        return self.session_data[symbol].get(session, 0)
    
    def add_trade_result(self, is_win: bool, pnl: float):
        """Add trade result to history"""
        self.trade_history.append({'win': is_win, 'pnl': pnl, 'time': datetime.now()})
        # Keep only last 10 trades
        if len(self.trade_history) > CONFIG['ANTI_LOSS']['win_rate_lookback']:
            self.trade_history = self.trade_history[-CONFIG['ANTI_LOSS']['win_rate_lookback']:]
    
    def get_win_rate(self) -> float:
        """Calculate current win rate"""
        if not self.trade_history:
            return 100.0  # Default to allow initial trades
        wins = sum(1 for trade in self.trade_history if trade['win'])
        return (wins / len(self.trade_history)) * 100.0

class MarketStructure:
    """Track market structure for SMC/ICT analysis - UNCHANGED"""
    def __init__(self):
        self.swing_highs = {}
        self.swing_lows = {}
        self.htf_bias = {}
        self.premium_discount = {}
        self.liquidity_levels = {}
        
    def update_structure(self, symbol: str, timeframe, rates):
        """Update market structure for symbol"""
        try:
            # Calculate swing highs and lows
            swing_highs, swing_lows = self._calculate_swings(rates)
            self.swing_highs[symbol] = swing_highs
            self.swing_lows[symbol] = swing_lows
            
            # Determine HTF bias
            self.htf_bias[symbol] = self._determine_htf_bias(rates, swing_highs, swing_lows)
            
            # Calculate premium/discount zones
            self.premium_discount[symbol] = self._calculate_premium_discount(rates, swing_highs, swing_lows)
            
            # Identify liquidity levels
            self.liquidity_levels[symbol] = self._identify_liquidity_levels(rates, swing_highs, swing_lows)
            
        except Exception as e:
            logger.error(f"Error updating structure for {symbol}: {e}")
    
    def _calculate_swings(self, rates) -> Tuple[List, List]:
        """Calculate swing highs and lows using fractal approach"""
        highs = []
        lows = []
        lookback = CONFIG['SMC']['structure_lookback']
        
        if len(rates) < lookback * 2 + 1:
            return highs, lows
            
        for i in range(lookback, len(rates) - lookback):
            # Check for swing high
            is_swing_high = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and rates[j]['high'] >= rates[i]['high']:
                    is_swing_high = False
                    break
            if is_swing_high:
                highs.append({'time': rates[i]['time'], 'price': rates[i]['high'], 'index': i})
                
            # Check for swing low
            is_swing_low = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and rates[j]['low'] <= rates[i]['low']:
                    is_swing_low = False
                    break
            if is_swing_low:
                lows.append({'time': rates[i]['time'], 'price': rates[i]['low'], 'index': i})
                
        return highs[-10:], lows[-10:]  # Keep last 10 swings
    
    def _determine_htf_bias(self, rates, swing_highs: List, swing_lows: List) -> str:
        """Determine higher timeframe bias"""
        if not swing_highs or not swing_lows or len(rates) < 2:
            return 'neutral'
            
        try:
            # Check for BOS (Break of Structure)
            latest_swing_high = max(swing_highs, key=lambda x: x['time']) if swing_highs else None
            latest_swing_low = max(swing_lows, key=lambda x: x['time']) if swing_lows else None
            
            if not latest_swing_high or not latest_swing_low:
                return 'neutral'
                
            current_price = rates[-1]['close']
            
            # Simple bias determination based on recent structure breaks
            if latest_swing_high['time'] > latest_swing_low['time']:
                # Recent swing high is more recent
                if current_price > latest_swing_high['price']:
                    return 'bullish'
                elif current_price < latest_swing_low['price']:
                    return 'bearish'
            else:
                # Recent swing low is more recent
                if current_price < latest_swing_low['price']:
                    return 'bearish'
                elif current_price > latest_swing_high['price']:
                    return 'bullish'
                    
            return 'neutral'
            
        except Exception as e:
            logger.error(f"Error determining HTF bias: {e}")
            return 'neutral'
    
    def _calculate_premium_discount(self, rates, swing_highs: List, swing_lows: List) -> Dict:
        """Calculate premium/discount zones"""
        if not swing_highs or not swing_lows:
            return {'premium': False, 'discount': False, 'equilibrium': 0}
            
        try:
            # Find recent swing range
            recent_high = max(swing_highs, key=lambda x: x['time'])['price'] if swing_highs else rates[-1]['high']
            recent_low = max(swing_lows, key=lambda x: x['time'])['price'] if swing_lows else rates[-1]['low']
            
            current_price = rates[-1]['close']
            equilibrium = (recent_high + recent_low) / 2
            
            return {
                'premium': current_price > equilibrium,
                'discount': current_price < equilibrium,
                'equilibrium': equilibrium,
                'range_high': recent_high,
                'range_low': recent_low
            }
            
        except Exception as e:
            logger.error(f"Error calculating premium/discount: {e}")
            return {'premium': False, 'discount': False, 'equilibrium': 0}
    
    def _identify_liquidity_levels(self, rates, swing_highs: List, swing_lows: List) -> Dict:
        """Identify liquidity levels (equal highs/lows)"""
        liquidity = {'buy_side': [], 'sell_side': []}
        
        try:
            # Find equal highs (buy-side liquidity)
            for i, high1 in enumerate(swing_highs[:-1]):
                for high2 in swing_highs[i+1:]:
                    if abs(high1['price'] - high2['price']) <= 5 * 0.00001:  # Within 5 points
                        liquidity['buy_side'].append(high1['price'])
                        break
            
            # Find equal lows (sell-side liquidity)
            for i, low1 in enumerate(swing_lows[:-1]):
                for low2 in swing_lows[i+1:]:
                    if abs(low1['price'] - low2['price']) <= 5 * 0.00001:  # Within 5 points
                        liquidity['sell_side'].append(low1['price'])
                        break
                        
        except Exception as e:
            logger.error(f"Error identifying liquidity levels: {e}")
            
        return liquidity

# Global instances
trade_state = TradeState()
market_structure = MarketStructure()
logger = None

# =============================================================================
# LOGGING SETUP (UNCHANGED)
# =============================================================================

def setup_logging():
    """Setup logging configuration"""
    global logger
    
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('CapitalSniperConservative')
    logger.setLevel(getattr(logging, CONFIG['SYSTEM']['log_level']))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if enabled
    if CONFIG['SYSTEM']['log_to_file']:
        log_filename = f"{log_dir}/capital_sniper_conservative_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_filename, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.info("=" * 60)
    logger.info("Capital Sniper v3.0 CONSERVATIVE - Python EA Starting")
    logger.info("=" * 60)

# =============================================================================
# MT5 CONNECTION AND UTILITY FUNCTIONS (UNCHANGED)
# =============================================================================

def connect_mt5() -> bool:
    """Initialize MT5 connection"""
    try:
        if not mt5.initialize():
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        # Get account info
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Failed to get account info")
            return False
        
        logger.info(f"Connected to MT5 - Account: {account_info.login}, Balance: {account_info.balance}")
        return True
        
    except Exception as e:
        logger.error(f"Error connecting to MT5: {e}")
        return False

def disconnect_mt5():
    """Shutdown MT5 connection"""
    mt5.shutdown()
    logger.info("MT5 connection closed")

def get_symbol_info(symbol: str) -> Optional[Dict]:
    """Get symbol information"""
    try:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.warning(f"Symbol {symbol} not found")
            return None
            
        return {
            'point': symbol_info.point,
            'digits': symbol_info.digits,
            'spread': symbol_info.spread,
            'min_lot': symbol_info.volume_min,
            'max_lot': symbol_info.volume_max,
            'lot_step': symbol_info.volume_step,
            'tick_value': symbol_info.trade_tick_value,
            'tick_size': symbol_info.trade_tick_size,
            'margin_required': symbol_info.margin_initial,
        }
    except Exception as e:
        logger.error(f"Error getting symbol info for {symbol}: {e}")
        return None

def get_current_price(symbol: str, order_type: str) -> Optional[float]:
    """Get current bid/ask price for symbol"""
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return tick.bid if order_type.upper() == 'SELL' else tick.ask
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        return None

def get_spread_pips(symbol: str) -> float:
    """Get spread in pips"""
    try:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return 999.0  # High value to prevent trading
        
        point_multiplier = CONFIG['SYMBOLS'].get(symbol, {}).get('point_multiplier', 10000)
        return symbol_info.spread * symbol_info.point * point_multiplier
    except Exception as e:
        logger.error(f"Error getting spread for {symbol}: {e}")
        return 999.0

def get_market_data(symbol: str, timeframe, count: int = 100) -> Optional[np.ndarray]:
    """Get market data for analysis"""
    try:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None or len(rates) == 0:
            logger.warning(f"No market data for {symbol}")
            return None
        return rates
    except Exception as e:
        logger.error(f"Error getting market data for {symbol}: {e}")
        return None

def calculate_atr(rates, period: int = 14) -> float:
    """Calculate Average True Range"""
    try:
        if len(rates) < period + 1:
            return 0.0
            
        true_ranges = []
        for i in range(1, len(rates)):
            tr1 = rates[i]['high'] - rates[i]['low']
            tr2 = abs(rates[i]['high'] - rates[i-1]['close'])
            tr3 = abs(rates[i]['low'] - rates[i-1]['close'])
            true_ranges.append(max(tr1, tr2, tr3))
        
        if len(true_ranges) < period:
            return 0.0
            
        return np.mean(true_ranges[-period:])
    except Exception as e:
        logger.error(f"Error calculating ATR: {e}")
        return 0.0

# =============================================================================
# POSITION SIZING AND RISK MANAGEMENT (ENHANCED FOR CONSERVATIVE APPROACH)
# =============================================================================

def calculate_position_size(symbol: str, entry_price: float, sl_price: float, risk_amount: float) -> float:
    """Calculate position size based on risk amount and stop loss"""
    try:
        symbol_info = get_symbol_info(symbol)
        if not symbol_info:
            return 0.0
        
        # Calculate risk distance in points
        risk_distance = abs(entry_price - sl_price)
        if risk_distance == 0:
            return 0.0
        
        # Calculate position size
        tick_value = symbol_info['tick_value']
        tick_size = symbol_info['tick_size']
        
        if tick_value == 0 or tick_size == 0:
            return 0.0
        
        position_size = risk_amount / (risk_distance / tick_size * tick_value)
        
        # Normalize to lot step
        lot_step = symbol_info['lot_step']
        position_size = round(position_size / lot_step) * lot_step
        
        # Apply min/max limits
        position_size = max(position_size, symbol_info['min_lot'])
        position_size = min(position_size, symbol_info['max_lot'])
        
        return position_size
        
    except Exception as e:
        logger.error(f"Error calculating position size for {symbol}: {e}")
        return 0.0

def check_risk_limits() -> bool:
    """Check if risk limits allow new trades - ENHANCED CONSERVATIVE VERSION"""
    try:
        account_info = mt5.account_info()
        if not account_info:
            return False
        
        current_equity = account_info.equity
        
        # Check if we're in a pause period
        if trade_state.pause_until and datetime.now() < trade_state.pause_until:
            return False
        
        # Check daily drawdown (TIGHTER)
        if trade_state.equity_start > 0:
            daily_dd = (trade_state.equity_start - current_equity) / trade_state.equity_start * 100
            if daily_dd >= CONFIG['RISK']['max_daily_drawdown']:
                trade_state.stop_all_trading = True
                logger.warning(f"Daily drawdown limit hit: {daily_dd:.2f}%")
                return False
        
        # Check weekly drawdown (TIGHTER)
        if trade_state.weekly_equity_start > 0:
            weekly_dd = (trade_state.weekly_equity_start - current_equity) / trade_state.weekly_equity_start * 100
            if weekly_dd >= CONFIG['RISK']['max_weekly_drawdown']:
                trade_state.stop_all_trading = True
                logger.warning(f"Weekly drawdown limit hit: {weekly_dd:.2f}%")
                return False
        
        # NEW - Check floating P&L before new trades
        if CONFIG['ANTI_LOSS']['check_floating_pnl']:
            floating_pnl = get_total_floating_pnl()
            if floating_pnl < 0:
                logger.info(f"Floating P&L negative ({floating_pnl:.2f}), blocking new trades")
                return False
        
        # NEW - Check win rate
        win_rate = trade_state.get_win_rate()
        if win_rate < CONFIG['ANTI_LOSS']['min_win_rate_threshold']:
            logger.warning(f"Win rate below threshold: {win_rate:.1f}%, pausing trading")
            return False
        
        # Update floating peak
        if current_equity > trade_state.floating_peak:
            trade_state.floating_peak = current_equity
        
        # Check max positions (REDUCED)
        total_positions = len(mt5.positions_get())
        if total_positions >= CONFIG['RISK']['max_positions_total']:
            return False
        
        return True and not trade_state.stop_all_trading
        
    except Exception as e:
        logger.error(f"Error checking risk limits: {e}")
        return False

def get_total_floating_pnl() -> float:
    """Calculate total floating P&L across all positions"""
    try:
        positions = mt5.positions_get()
        if not positions:
            return 0.0
        
        total_pnl = 0.0
        magic_base = CONFIG['SYSTEM']['magic_number_base']
        
        for position in positions:
            if magic_base <= position.magic < magic_base + 10000:
                total_pnl += position.profit
        
        return total_pnl
        
    except Exception as e:
        logger.error(f"Error calculating floating P&L: {e}")
        return 0.0

def update_consecutive_losses(is_loss: bool):
    """Update consecutive loss counter"""
    if is_loss:
        trade_state.consecutive_losses += 1
        if trade_state.consecutive_losses >= CONFIG['RISK']['consecutive_loss_limit']:
            pause_hours = CONFIG['RISK']['consecutive_loss_pause_hours']
            trade_state.pause_until = datetime.now() + timedelta(hours=pause_hours)
            logger.warning(f"Consecutive loss limit hit. Pausing for {pause_hours} hours")
    else:
        trade_state.consecutive_losses = 0

# =============================================================================
# SESSION MANAGEMENT (ENHANCED CONSERVATIVE)
# =============================================================================

def is_trading_session(symbol: str) -> Tuple[bool, str]:
    """Check if current time is within trading session - CONSERVATIVE VERSION"""
    try:
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        # NEW - Check session warmup/cooldown periods
        warmup_mins = CONFIG['SESSIONS']['session_warmup_minutes']
        cooldown_mins = CONFIG['SESSIONS']['session_cooldown_minutes']
        
        london_start = CONFIG['SESSIONS']['london_start']
        london_end = CONFIG['SESSIONS']['london_end']
        ny_start = CONFIG['SESSIONS']['ny_start']
        ny_end = CONFIG['SESSIONS']['ny_end']
        
        # Check if in warmup period (first 15 minutes of session)
        if ((current_hour == london_start and current_minute < warmup_mins) or
            (current_hour == ny_start and current_minute < warmup_mins)):
            return False, 'warmup'
        
        # Check if in cooldown period (last 30 minutes of session)
        if ((current_hour == london_end and current_minute >= 60 - cooldown_mins) or
            (current_hour == ny_end and current_minute >= 60 - cooldown_mins)):
            return False, 'cooldown'
        
        london_active = london_start <= current_hour <= london_end
        ny_active = ny_start <= current_hour <= ny_end
        
        # Special handling for XAUUSD (Gold) - OVERLAP ONLY
        if symbol == 'XAUUSD':
            gold_start = CONFIG['SESSIONS']['gold_session_start']
            gold_end = CONFIG['SESSIONS']['gold_session_end']
            gold_active = gold_start <= current_hour <= gold_end
            
            # Also check warmup/cooldown for gold session
            if ((current_hour == gold_start and current_minute < warmup_mins) or
                (current_hour == gold_end and current_minute >= 60 - cooldown_mins)):
                return False, 'cooldown'
            
            if gold_active:
                return True, 'overlap'
            else:
                return False, 'closed'
        
        # Regular forex pairs
        if london_active and ny_active:
            return True, 'overlap'
        elif london_active:
            return True, 'london'
        elif ny_active:
            return True, 'ny'
        else:
            return False, 'closed'
            
    except Exception as e:
        logger.error(f"Error checking trading session: {e}")
        return False, 'error'

def check_session_limits(symbol: str, session: str) -> bool:
    """Check if session trade limits allow new trades"""
    if session == 'overlap':
        # During overlap, check both session limits
        london_count = trade_state.get_session_count(symbol, 'london')
        ny_count = trade_state.get_session_count(symbol, 'ny')
        max_setups = CONFIG['RISK']['max_sessions_per_symbol']
        
        return london_count < max_setups and ny_count < max_setups
    else:
        current_count = trade_state.get_session_count(symbol, session)
        return current_count < CONFIG['RISK']['max_sessions_per_symbol']

def reset_session_counters_if_needed():
    """Reset session counters at session starts"""
    try:
        now = datetime.now()
        current_hour = now.hour
        today_key = now.strftime('%Y-%m-%d')
        
        # Reset at London session start (once per day)
        london_key = f"london_{today_key}"
        if (current_hour == CONFIG['SESSIONS']['london_start'] and 
            london_key not in trade_state.last_session_reset):
            
            for symbol in CONFIG['SYMBOLS'].keys():
                trade_state.reset_session_counters(symbol, 'london')
            
            trade_state.last_session_reset[london_key] = True
            trade_state.equity_start = mt5.account_info().equity
            trade_state.floating_peak = trade_state.equity_start
            
            # NEW - Reset daily summary
            trade_state.daily_summary = {
                'date': today_key,
                'trades_taken': 0,
                'wins': 0,
                'losses': 0,
                'net_pnl': 0.0,
                'max_dd_hit': 0.0,
                'win_rate': 0.0
            }
            
            logger.info(f"London session reset. Equity baseline: {trade_state.equity_start:.2f}")
        
        # Reset at NY session start (once per day)
        ny_key = f"ny_{today_key}"
        if (current_hour == CONFIG['SESSIONS']['ny_start'] and 
            ny_key not in trade_state.last_session_reset):
            
            for symbol in CONFIG['SYMBOLS'].keys():
                trade_state.reset_session_counters(symbol, 'ny')
            
            trade_state.last_session_reset[ny_key] = True
            logger.info("NY session reset completed")
        
        # Weekly reset (Monday)
        if now.weekday() == 0 and current_hour == CONFIG['SESSIONS']['london_start']:  # Monday
            week_key = f"week_{now.strftime('%Y-W%W')}"
            if week_key not in trade_state.last_session_reset:
                trade_state.weekly_equity_start = mt5.account_info().equity
                trade_state.last_session_reset[week_key] = True
                trade_state.stop_all_trading = False  # Reset weekly halt
                logger.info(f"Weekly reset. Equity baseline: {trade_state.weekly_equity_start:.2f}")
        
        # NEW - End of session summary logging
        if ((current_hour == CONFIG['SESSIONS']['london_end'] and today_key not in trade_state.last_session_reset.get('london_summary', [])) or
            (current_hour == CONFIG['SESSIONS']['ny_end'] and today_key not in trade_state.last_session_reset.get('ny_summary', []))):
            log_daily_summary()
        
    except Exception as e:
        logger.error(f"Error resetting session counters: {e}")

def log_daily_summary():
    """Log daily trading summary"""
    try:
        summary = trade_state.daily_summary
        win_rate = (summary['wins'] / max(summary['trades_taken'], 1)) * 100
        
        logger.info("=" * 50)
        logger.info("DAILY TRADING SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Date: {summary['date']}")
        logger.info(f"Trades Taken: {summary['trades_taken']}")
        logger.info(f"Wins: {summary['wins']}")
        logger.info(f"Losses: {summary['losses']}")
        logger.info(f"Net P&L: ${summary['net_pnl']:.2f}")
        logger.info(f"Max Drawdown Hit: {summary['max_dd_hit']:.2f}%")
        logger.info(f"Win Rate: {win_rate:.1f}%")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Error logging daily summary: {e}")

# =============================================================================
# MARKET ANALYSIS AND SIGNAL DETECTION (CONSERVATIVE ENHANCEMENTS)
# =============================================================================

def detect_fvg_patterns(symbol: str, rates) -> List[Dict]:
    """Detect Fair Value Gap patterns - CONSERVATIVE VERSION"""
    signals = []
    
    try:
        if len(rates) < 5:
            return signals
        
        symbol_info = get_symbol_info(symbol)
        if not symbol_info:
            return signals
        
        point = symbol_info['point']
        point_multiplier = CONFIG['SYMBOLS'].get(symbol, {}).get('point_multiplier', 10000)
        deviation = CONFIG['STRATEGY']['fvg_deviation_pips'] * point * point_multiplier
        
        # Check last 5 bars for FVG patterns
        for i in range(2, len(rates) - 2):
            bar1 = rates[i-2]
            bar2 = rates[i-1]
            bar3 = rates[i]
            current_bar = rates[-1]
            
            # Bullish FVG: bar1.high < bar3.low (gap up)
            if bar1['high'] < bar3['low'] - deviation:
                entry_price = bar1['high'] + deviation
                
                # Confirm entry is still valid
                if current_bar['low'] > entry_price:
                    sl_price = bar1['low'] - CONFIG['STRATEGY']['sl_buffer_pips'] * point * point_multiplier
                    
                    confidence = calculate_signal_confidence(rates, 'BUY', i)
                    
                    # NEW - Apply minimum confidence filter
                    if confidence >= CONFIG['STRATEGY']['min_confidence_threshold']:
                        signals.append({
                            'type': 'BUY',
                            'entry_price': entry_price,
                            'sl_price': sl_price,
                            'pattern': 'FVG_BULLISH',
                            'confidence': confidence,
                            'bar_index': i
                        })
            
            # Bearish FVG: bar1.low > bar3.high (gap down)
            if bar1['low'] > bar3['high'] + deviation:
                entry_price = bar1['low'] - deviation
                
                # Confirm entry is still valid
                if current_bar['high'] < entry_price:
                    sl_price = bar1['high'] + CONFIG['STRATEGY']['sl_buffer_pips'] * point * point_multiplier
                    
                    confidence = calculate_signal_confidence(rates, 'SELL', i)
                    
                    # NEW - Apply minimum confidence filter
                    if confidence >= CONFIG['STRATEGY']['min_confidence_threshold']:
                        signals.append({
                            'type': 'SELL',
                            'entry_price': entry_price,
                            'sl_price': sl_price,
                            'pattern': 'FVG_BEARISH',
                            'confidence': confidence,
                            'bar_index': i
                        })
        
        return signals
        
    except Exception as e:
        logger.error(f"Error detecting FVG patterns for {symbol}: {e}")
        return []

# REMOVED ORDER BLOCK DETECTION - Per requirement #9 "Remove order block detection for now — FVG only"

def calculate_signal_confidence(rates, signal_type: str, bar_index: int) -> float:
    """Calculate signal confidence based on multiple factors - ENHANCED"""
    try:
        confidence = 0.5  # Base confidence
        
        # ATR-based momentum check
        atr = calculate_atr(rates[max(0, bar_index-14):bar_index+1])
        if atr > 0:
            recent_range = rates[bar_index]['high'] - rates[bar_index]['low']
            if recent_range < atr * 0.8:  # Lower volatility = higher confidence
                confidence += 0.2
        
        # Volume proxy (tick volume if available)
        if 'tick_volume' in rates[0]:
            avg_volume = np.mean([bar['tick_volume'] for bar in rates[max(0, bar_index-5):bar_index]])
            current_volume = rates[bar_index]['tick_volume']
            if current_volume > avg_volume * 1.2:  # Higher volume = higher confidence
                confidence += 0.2
        
        # Trend alignment check
        ma_period = 20
        if bar_index >= ma_period:
            close_prices = [bar['close'] for bar in rates[bar_index-ma_period:bar_index]]
            ma = np.mean(close_prices)
            current_close = rates[bar_index]['close']
            
            if signal_type == 'BUY' and current_close > ma:
                confidence += 0.15
            elif signal_type == 'SELL' and current_close < ma:
                confidence += 0.15
        
        # NEW - Additional confidence factors for conservative approach
        # Recent price action stability
        if bar_index >= 5:
            recent_bars = rates[bar_index-5:bar_index]
            price_volatility = np.std([bar['close'] for bar in recent_bars])
            if price_volatility < atr * 0.5:  # Lower volatility = more stable
                confidence += 0.1
        
        return min(confidence, 1.0)  # Cap at 1.0
        
    except Exception as e:
        logger.error(f"Error calculating signal confidence: {e}")
        return 0.5

def apply_wyckoff_filter(symbol: str, rates, signal_type: str) -> bool:
    """Apply Wyckoff confirmation filter - NOW MANDATORY"""
    try:
        lookback = CONFIG['STRATEGY']['wyckoff_lookback']
        if len(rates) < lookback + 2:
            return False
        
        # Check recent bars for Wyckoff patterns
        bar0 = rates[-2]  # Most recent closed bar
        bar1 = rates[-3]  # Previous bar
        
        if signal_type == 'BUY':
            # Look for lower lows (accumulation/spring)
            return bar0['low'] < bar1['low']
        else:  # SELL
            # Look for higher highs (distribution/upthrust)
            return bar0['high'] > bar1['high']
            
    except Exception as e:
        logger.error(f"Error applying Wyckoff filter: {e}")
        return False

def apply_exhaustion_filter(symbol: str, rates) -> bool:
    """Apply exhaustion filter to avoid entering after large moves"""
    try:
        if len(rates) < 2:
            return False
        
        symbol_info = get_symbol_info(symbol)
        if not symbol_info:
            return False
        
        point = symbol_info['point']
        point_multiplier = CONFIG['SYMBOLS'].get(symbol, {}).get('point_multiplier', 10000)
        
        # Get appropriate threshold
        threshold_pips = (CONFIG['STRATEGY']['exhaustion_threshold_gold'] 
                         if symbol == 'XAUUSD' 
                         else CONFIG['STRATEGY']['exhaustion_threshold_forex'])
        
        threshold_distance = threshold_pips * point * point_multiplier
        
        # Check most recent closed bar
        recent_bar = rates[-2]
        bar_range = recent_bar['high'] - recent_bar['low']
        
        return bar_range < threshold_distance  # True if NOT exhausted
        
    except Exception as e:
        logger.error(f"Error applying exhaustion filter: {e}")
        return False

def apply_smc_filters(symbol: str, rates, signal_type: str) -> bool:
    """Apply SMC/ICT filters - ALL ENABLED FOR CONSERVATIVE APPROACH"""
    try:
        # Update market structure
        market_structure.update_structure(symbol, CONFIG['SMC']['htf_timeframe'], rates)
        
        # HTF Bias Filter (MANDATORY)
        htf_bias = market_structure.htf_bias.get(symbol, 'neutral')
        if signal_type == 'BUY' and htf_bias == 'bearish':
            return False
        if signal_type == 'SELL' and htf_bias == 'bullish':
            return False
        
        # Premium/Discount Filter (MANDATORY)
        pd_data = market_structure.premium_discount.get(symbol, {})
        if signal_type == 'BUY' and pd_data.get('premium', False):
            return False  # Only longs in discount
        if signal_type == 'SELL' and pd_data.get('discount', False):
            return False  # Only shorts in premium
        
        # Displacement Filter (MANDATORY)
        atr = calculate_atr(rates[-15:])
        if atr > 0:
            recent_bar = rates[-2]
            body_size = abs(recent_bar['close'] - recent_bar['open'])
            required_body = atr * CONFIG['STRATEGY']['displacement_atr_mult']
            
            if body_size < required_body:
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error applying SMC filters: {e}")
        return False  # Conservative: reject if filter fails

def check_liquidity_sweep(symbol: str, rates) -> bool:
    """Check for liquidity sweep (enhanced SMC feature)"""
    try:
        liquidity_levels = market_structure.liquidity_levels.get(symbol, {})
        current_price = rates[-1]['close']
        recent_high = max([bar['high'] for bar in rates[-5:]])
        recent_low = min([bar['low'] for bar in rates[-5:]])
        
        # Check if recent price action swept liquidity
        buy_side_swept = any(recent_high >= level for level in liquidity_levels.get('buy_side', []))
        sell_side_swept = any(recent_low <= level for level in liquidity_levels.get('sell_side', []))
        
        return buy_side_swept or sell_side_swept
        
    except Exception as e:
        logger.error(f"Error checking liquidity sweep: {e}")
        return True

# =============================================================================
# ORDER EXECUTION AND MANAGEMENT (CONSERVATIVE - NO STACKING)
# =============================================================================

def place_single_order(symbol: str, signal: Dict, session: str) -> bool:
    """Place single limit order - NO STACKING in conservative version"""
    try:
        signal_type = signal['type']
        entry_price = signal['entry_price']
        sl_price = signal['sl_price']
        
        # Calculate risk amount
        account_info = mt5.account_info()
        risk_amount = account_info.equity * CONFIG['RISK']['risk_percent'] / 100.0
        
        # Calculate position size
        position_size = calculate_position_size(symbol, entry_price, sl_price, risk_amount)
        if position_size <= 0:
            logger.warning(f"Invalid position size calculated for {symbol}")
            return False
        
        symbol_info = get_symbol_info(symbol)
        if not symbol_info:
            return False
        
        # Calculate TP levels
        risk_distance = abs(entry_price - sl_price)
        tp1_price = entry_price + (risk_distance * CONFIG['TRADE_MGMT']['tp1_target_r'] * (1 if signal_type == 'BUY' else -1))
        
        # Prepare order request
        magic_number = CONFIG['SYSTEM']['magic_number_base'] + hash(symbol) % 1000
        comment = f"CapSniper_Conservative_{signal['pattern']}"
        
        if signal_type == 'BUY':
            order_type = mt5.ORDER_TYPE_BUY_LIMIT
        else:
            order_type = mt5.ORDER_TYPE_SELL_LIMIT
        
        request = {
            'action': mt5.TRADE_ACTION_PENDING,
            'symbol': symbol,
            'volume': position_size,
            'type': order_type,
            'price': entry_price,
            'sl': sl_price,
            'tp': tp1_price,
            'deviation': 10,
            'magic': magic_number,
            'comment': comment,
            'type_time': mt5.ORDER_TIME_DAY,
        }
        
        # Place order with retry logic
        success = place_order_with_retry(request)
        if success:
            # Register trade
            if session == 'overlap':
                trade_state.increment_session_counter(symbol, 'london', 1)
                trade_state.increment_session_counter(symbol, 'ny', 1)
            else:
                trade_state.increment_session_counter(symbol, session, 1)
            
            trade_state.daily_summary['trades_taken'] += 1
            logger.info(f"Conservative order placed: {comment} at {entry_price:.5f}")
            return True
        else:
            logger.warning(f"Failed to place conservative order for {symbol}")
            return False
        
    except Exception as e:
        logger.error(f"Error placing conservative order for {symbol}: {e}")
        return False

def place_order_with_retry(request: Dict) -> bool:
    """Place order with retry logic - LIMIT ORDERS ONLY"""
    for attempt in range(CONFIG['SYSTEM']['retry_attempts']):
        try:
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return True
            else:
                if result:
                    logger.warning(f"Order failed (attempt {attempt + 1}): {result.retcode} - {result.comment}")
                else:
                    logger.warning(f"Order failed (attempt {attempt + 1}): No result returned")
                
                if attempt < CONFIG['SYSTEM']['retry_attempts'] - 1:
                    time.sleep(CONFIG['SYSTEM']['retry_delay_ms'] / 1000)
        
        except Exception as e:
            logger.error(f"Order placement error (attempt {attempt + 1}): {e}")
            if attempt < CONFIG['SYSTEM']['retry_attempts'] - 1:
                time.sleep(CONFIG['SYSTEM']['retry_delay_ms'] / 1000)
    
    # NO MARKET ORDER FALLBACK - Per requirement #9
    logger.info(f"Limit order not filled after retries, moving on (no market order fallback)")
    return False

def count_open_positions(symbol: str = None) -> int:
    """Count open positions for symbol or total"""
    try:
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None:
            return 0
        
        # Filter by magic number range
        magic_base = CONFIG['SYSTEM']['magic_number_base']
        our_positions = [
            pos for pos in positions 
            if magic_base <= pos.magic < magic_base + 10000
        ]
        
        return len(our_positions)
        
    except Exception as e:
        logger.error(f"Error counting positions: {e}")
        return 0

# =============================================================================
# TRADE MANAGEMENT (CONSERVATIVE - PROFIT-FOCUSED)
# =============================================================================

def manage_open_positions():
    """Manage all open positions with conservative trade management"""
    try:
        positions = mt5.positions_get()
        if not positions:
            return
        
        magic_base = CONFIG['SYSTEM']['magic_number_base']
        
        for position in positions:
            if magic_base <= position.magic < magic_base + 10000:
                manage_single_position(position)
                
    except Exception as e:
        logger.error(f"Error managing open positions: {e}")

def manage_single_position(position):
    """Manage individual position - CONSERVATIVE PROFIT-FOCUSED APPROACH"""
    try:
        symbol = position.symbol
        ticket = position.ticket
        pos_type = position.type
        open_price = position.price_open
        open_time = datetime.fromtimestamp(position.time)
        current_sl = position.sl
        
        # Get current price
        current_price = get_current_price(symbol, 'SELL' if pos_type == mt5.POSITION_TYPE_BUY else 'BUY')
        if not current_price:
            return
        
        # Calculate position age
        position_age = (datetime.now() - open_time).total_seconds() / 3600  # Hours
        
        # Calculate profit in R multiples
        risk_distance = abs(open_price - current_sl) if current_sl > 0 else 0
        if risk_distance == 0:
            return
        
        if pos_type == mt5.POSITION_TYPE_BUY:
            profit_distance = current_price - open_price
        else:
            profit_distance = open_price - current_price
        
        r_multiple = profit_distance / risk_distance if risk_distance > 0 else 0
        
        # Store position state
        if ticket not in trade_state.positions_data:
            trade_state.positions_data[ticket] = {
                'breakeven_applied': False,
                'partial_1_applied': False,
                'partial_2_applied': False,
                'trailing_active': False,
                'max_r_reached': 0,
                'sl_tightened': False
            }
        
        pos_data = trade_state.positions_data[ticket]
        pos_data['max_r_reached'] = max(pos_data['max_r_reached'], r_multiple)
        
        # NEW - TIME-BASED EXITS (Requirement #5)
        # Close if profitable after 4 hours
        if position_age >= CONFIG['TRADE_MGMT']['profit_exit_hours'] and r_multiple > 0:
            close_position_at_profit(position, "4-hour profit rule")
            return
        
        # Close regardless after 6 hours
        if position_age >= CONFIG['TRADE_MGMT']['max_position_hours']:
            close_position_force(position, "6-hour time limit")
            return
        
        # NEW - Close all positions 30 minutes before session end
        if is_near_session_end(symbol):
            close_position_force(position, "session end approach")
            return
        
        # NEW - Anti-loss logic: tighten SL if position drops below -0.5R
        if r_multiple <= -0.5 and not pos_data['sl_tightened']:
            tighten_stop_loss(position)
            pos_data['sl_tightened'] = True
        
        # Stage 1: Move to breakeven FASTER (0.75R instead of 1R)
        if (r_multiple >= CONFIG['TRADE_MGMT']['breakeven_trigger_r'] and 
            not pos_data['breakeven_applied']):
            move_to_breakeven_conservative(position)
            pos_data['breakeven_applied'] = True
        
        # Stage 2: First partial close EARLIER (1.5R, take 40%)
        elif (r_multiple >= CONFIG['TRADE_MGMT']['partial_close_1_r'] and 
              not pos_data['partial_1_applied']):
            partial_close_position(position, CONFIG['TRADE_MGMT']['partial_close_1_pct'])
            pos_data['partial_1_applied'] = True
        
        # Stage 3: Second partial close (2.5R, take 30%)
        elif (r_multiple >= CONFIG['TRADE_MGMT']['partial_close_2_r'] and 
              not pos_data['partial_2_applied']):
            partial_close_position(position, CONFIG['TRADE_MGMT']['partial_close_2_pct'])
            pos_data['partial_2_applied'] = True
        
        # Stage 4: Tighter trailing stop (1.0x ATR instead of 1.5x)
        elif (r_multiple >= CONFIG['TRADE_MGMT']['trailing_start_r'] and 
              pos_data['breakeven_applied']):
            apply_trailing_stop_conservative(position, current_price)
            pos_data['trailing_active'] = True
        
        # ENHANCED Winner protection: If trade reached +1R but falls back to +0.3R
        if (pos_data['max_r_reached'] >= CONFIG['TRADE_MGMT']['winner_protection_trigger'] and
            r_multiple <= CONFIG['TRADE_MGMT']['winner_protection_exit'] and
            pos_data['breakeven_applied']):
            close_position_at_profit(position, "winner protection")
        
    except Exception as e:
        logger.error(f"Error managing position {position.ticket}: {e}")

def is_near_session_end(symbol: str) -> bool:
    """Check if we're within 30 minutes of session end"""
    try:
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        # Check if within 30 minutes of any session end
        london_end = CONFIG['SESSIONS']['london_end']
        ny_end = CONFIG['SESSIONS']['ny_end']
        gold_end = CONFIG['SESSIONS']['gold_session_end']
        
        if symbol == 'XAUUSD':
            return current_hour == gold_end and current_minute >= 30
        else:
            return ((current_hour == london_end and current_minute >= 30) or
                    (current_hour == ny_end and current_minute >= 30))
        
    except Exception as e:
        logger.error(f"Error checking session end: {e}")
        return False

def tighten_stop_loss(position):
    """Tighten SL by 30% if position drops below -0.5R"""
    try:
        current_sl = position.sl
        open_price = position.price_open
        
        if current_sl == 0:
            return
        
        # Calculate 30% tighter SL
        sl_distance = abs(open_price - current_sl)
        tighter_distance = sl_distance * (1 - CONFIG['TRADE_MGMT']['anti_loss_sl_tighten'])
        
        if position.type == mt5.POSITION_TYPE_BUY:
            new_sl = open_price - tighter_distance
            if new_sl > current_sl:  # Only move if better
                modify_position(position.ticket, new_sl, position.tp)
                logger.info(f"Tightened SL for {position.symbol} (anti-loss): {new_sl:.5f}")
        else:
            new_sl = open_price + tighter_distance
            if new_sl < current_sl:  # Only move if better
                modify_position(position.ticket, new_sl, position.tp)
                logger.info(f"Tightened SL for {position.symbol} (anti-loss): {new_sl:.5f}")
                
    except Exception as e:
        logger.error(f"Error tightening stop loss: {e}")

def move_to_breakeven_conservative(position):
    """Move stop loss to breakeven + small buffer - PROFIT-ONLY LOGIC"""
    try:
        symbol = position.symbol
        symbol_info = get_symbol_info(symbol)
        if not symbol_info:
            return
        
        buffer = CONFIG['STRATEGY']['sl_buffer_pips'] * symbol_info['point'] * CONFIG['SYMBOLS'].get(symbol, {}).get('point_multiplier', 10000)
        
        if position.type == mt5.POSITION_TYPE_BUY:
            # Set SL above entry to ensure PROFIT-ONLY CLOSE
            new_sl = position.price_open + buffer
            if new_sl > position.sl:  # Only move if better
                modify_position(position.ticket, new_sl, position.tp)
                logger.info(f"Conservative breakeven applied to {symbol}: {new_sl:.5f}")
        else:
            # Set SL below entry to ensure PROFIT-ONLY CLOSE
            new_sl = position.price_open - buffer
            if position.sl == 0 or new_sl < position.sl:  # Only move if better
                modify_position(position.ticket, new_sl, position.tp)
                logger.info(f"Conservative breakeven applied to {symbol}: {new_sl:.5f}")
                
    except Exception as e:
        logger.error(f"Error moving to conservative breakeven: {e}")

def partial_close_position(position, close_percentage: float):
    """Partially close position"""
    try:
        close_volume = round(position.volume * close_percentage, 2)
        
        # Check minimum volume
        symbol_info = get_symbol_info(position.symbol)
        if symbol_info and close_volume >= symbol_info['min_lot']:
            request = {
                'action': mt5.TRADE_ACTION_DEAL,
                'symbol': position.symbol,
                'volume': close_volume,
                'type': mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                'position': position.ticket,
                'deviation': 10,
                'magic': position.magic,
                'comment': f"Partial_Close_{close_percentage*100:.0f}pct",
            }
            
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Conservative partial close: {position.symbol} {close_percentage*100:.0f}% at {close_volume} lots")
                
                # Update daily summary
                trade_state.daily_summary['wins'] += 1
                trade_state.daily_summary['net_pnl'] += position.profit * close_percentage
            else:
                logger.warning(f"Partial close failed: {result.comment if result else 'Unknown error'}")
                
    except Exception as e:
        logger.error(f"Error in partial close: {e}")

def apply_trailing_stop_conservative(position, current_price: float):
    """Apply TIGHTER ATR-based trailing stop"""
    try:
        symbol = position.symbol
        
        # Get recent rates for ATR calculation
        rates = get_market_data(symbol, CONFIG['SMC']['ltf_timeframe'], 50)
        if rates is None:
            return
        
        atr = calculate_atr(rates)
        if atr == 0:
            return
        
        # TIGHTER trailing distance (1.0x ATR instead of 1.5x)
        trail_distance = atr * CONFIG['TRADE_MGMT']['trailing_atr_mult']
        
        if position.type == mt5.POSITION_TYPE_BUY:
            new_sl = current_price - trail_distance
            if new_sl > position.sl:  # Only move if better
                modify_position(position.ticket, new_sl, position.tp)
                logger.debug(f"Conservative trailing stop: {symbol}: {new_sl:.5f}")
        else:
            new_sl = current_price + trail_distance
            if position.sl == 0 or new_sl < position.sl:  # Only move if better
                modify_position(position.ticket, new_sl, position.tp)
                logger.debug(f"Conservative trailing stop: {symbol}: {new_sl:.5f}")
                
    except Exception as e:
        logger.error(f"Error applying conservative trailing stop: {e}")

def close_position_at_profit(position, reason: str):
    """Close position at current profit level"""
    try:
        if position.profit <= 0:
            logger.info(f"Position {position.symbol} not profitable, keeping open despite {reason}")
            return
        
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': position.symbol,
            'volume': position.volume,
            'type': mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            'position': position.ticket,
            'deviation': 10,
            'magic': position.magic,
            'comment': f"Conservative_Close_{reason}",
        }
        
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Conservative profit close: {position.symbol} - {reason} - P&L: ${position.profit:.2f}")
            
            # Update daily summary
            trade_state.daily_summary['wins'] += 1
            trade_state.daily_summary['net_pnl'] += position.profit
            
            # Clean up position data
            if position.ticket in trade_state.positions_data:
                del trade_state.positions_data[position.ticket]
        else:
            logger.warning(f"Failed to close position: {result.comment if result else 'Unknown error'}")
                
    except Exception as e:
        logger.error(f"Error closing position at profit: {e}")

def close_position_force(position, reason: str):
    """Force close position regardless of P&L"""
    try:
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': position.symbol,
            'volume': position.volume,
            'type': mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            'position': position.ticket,
            'deviation': 10,
            'magic': position.magic,
            'comment': f"Force_Close_{reason}",
        }
        
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            is_win = position.profit > 0
            logger.info(f"Force close: {position.symbol} - {reason} - P&L: ${position.profit:.2f}")
            
            # Update daily summary
            if is_win:
                trade_state.daily_summary['wins'] += 1
            else:
                trade_state.daily_summary['losses'] += 1
            trade_state.daily_summary['net_pnl'] += position.profit
            
            # Update trade history
            trade_state.add_trade_result(is_win, position.profit)
            
            # Clean up position data
            if position.ticket in trade_state.positions_data:
                del trade_state.positions_data[position.ticket]
        else:
            logger.warning(f"Failed to force close position: {result.comment if result else 'Unknown error'}")
                
    except Exception as e:
        logger.error(f"Error force closing position: {e}")

def modify_position(ticket: int, sl: float, tp: float):
    """Modify position SL/TP with spread protection"""
    try:
        # Get position info
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return False
        
        position = positions[0]
        symbol = position.symbol
        
        # Check spread protection - don't modify if spread too wide
        current_spread = get_spread_pips(symbol)
        normal_spread = CONFIG['SYMBOLS'].get(symbol, {}).get('max_spread', 2.0)
        max_allowed_spread = normal_spread * CONFIG['ANTI_LOSS']['spread_protection_multiplier']
        
        if current_spread > max_allowed_spread:
            logger.info(f"Spread too wide for modification {symbol}: {current_spread:.1f} pips > {max_allowed_spread:.1f}")
            return False
        
        request = {
            'action': mt5.TRADE_ACTION_SLTP,
            'position': ticket,
            'sl': sl,
            'tp': tp,
        }
        
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return True
        else:
            logger.warning(f"Position modification failed: {result.comment if result else 'Unknown error'}")
            return False
            
    except Exception as e:
        logger.error(f"Error modifying position: {e}")
        return False

# =============================================================================
# MAIN TRADING LOGIC (CONSERVATIVE)
# =============================================================================

def scan_for_signals():
    """Scan all symbols for trading signals - CONSERVATIVE VERSION"""
    try:
        signals_found = []
        
        for symbol in CONFIG['SYMBOLS'].keys():
            try:
                # Check basic eligibility
                if not is_symbol_eligible_for_trading(symbol):
                    continue
                
                # Get market data
                rates = get_market_data(symbol, CONFIG['SMC']['ltf_timeframe'])
                if rates is None:
                    continue
                
                # Detect ONLY FVG patterns (order blocks removed per requirement #9)
                fvg_signals = detect_fvg_patterns(symbol, rates)
                
                # Apply filters to each signal
                for signal in fvg_signals:
                    if validate_signal_conservative(symbol, rates, signal):
                        signals_found.append((symbol, signal))
                        
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
        
        return signals_found
        
    except Exception as e:
        logger.error(f"Error in signal scanning: {e}")
        return []

def is_symbol_eligible_for_trading(symbol: str) -> bool:
    """Check if symbol is eligible for trading - CONSERVATIVE VERSION"""
    try:
        # Check if symbol exists and is active
        if not mt5.symbol_select(symbol, True):
            return False
        
        # Check trading session (with warmup/cooldown)
        in_session, session = is_trading_session(symbol)
        if not in_session:
            return False
        
        # Check session limits
        if not check_session_limits(symbol, session):
            return False
        
        # TIGHTER spread check
        spread_pips = get_spread_pips(symbol)
        max_spread = CONFIG['SYMBOLS'].get(symbol, {}).get('max_spread', 3.0)
        if spread_pips > max_spread:
            return False
        
        # STRICT position limits (max 1 per symbol)
        open_positions = count_open_positions(symbol)
        if open_positions >= CONFIG['RISK']['max_positions_per_symbol']:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking symbol eligibility for {symbol}: {e}")
        return False

def validate_signal_conservative(symbol: str, rates, signal: Dict) -> bool:
    """Validate signal against ALL conservative filters"""
    try:
        signal_type = signal['type']
        
        # MANDATORY Wyckoff filter
        if not apply_wyckoff_filter(symbol, rates, signal_type):
            return False
        
        # Apply exhaustion filter
        if not apply_exhaustion_filter(symbol, rates):
            return False
        
        # MANDATORY SMC/ICT filters
        if not apply_smc_filters(symbol, rates, signal_type):
            return False
        
        # Check liquidity sweep
        if not check_liquidity_sweep(symbol, rates):
            return False
        
        # Check HIGHER minimum R:R ratio (3.0 instead of 2.0)
        entry_price = signal['entry_price']
        sl_price = signal['sl_price']
        risk_distance = abs(entry_price - sl_price)
        
        if signal_type == 'BUY':
            tp_price = entry_price + (risk_distance * CONFIG['STRATEGY']['min_rr_ratio'])
        else:
            tp_price = entry_price - (risk_distance * CONFIG['STRATEGY']['min_rr_ratio'])
        
        # Store TP in signal for later use
        signal['tp_price'] = tp_price
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating conservative signal for {symbol}: {e}")
        return False

def execute_signals(signals: List[Tuple[str, Dict]]):
    """Execute validated trading signals - CONSERVATIVE VERSION"""
    for symbol, signal in signals:
        try:
            # Final checks before execution
            if not check_risk_limits():
                logger.info("Conservative risk limits prevent new trades")
                break
            
            # Determine session
            _, session = is_trading_session(symbol)
            
            # Place SINGLE order (no stacking)
            success = place_single_order(symbol, signal, session)
            
            if success:
                logger.info(f"Conservative signal executed: {symbol} {signal['pattern']} {signal['type']} at {signal['entry_price']:.5f} (Confidence: {signal['confidence']:.2f})")
            else:
                logger.warning(f"Failed to execute conservative signal for {symbol}")
                
        except Exception as e:
            logger.error(f"Error executing conservative signal for {symbol}: {e}")

# =============================================================================
# GRACEFUL SHUTDOWN AND ERROR HANDLING (UNCHANGED)
# =============================================================================

class GracefulShutdown:
    """Handle graceful shutdown of the EA"""
    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Shutdown signal received: {signum}")
        self.shutdown_requested = True
    
    def should_shutdown(self):
        return self.shutdown_requested

def cleanup_on_shutdown():
    """Cleanup operations before shutdown"""
    try:
        logger.info("Performing conservative cleanup operations...")
        
        # Log final summary
        log_daily_summary()
        
        # Disconnect from MT5
        disconnect_mt5()
        
        logger.info("Conservative cleanup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def handle_connection_issues():
    """Handle MT5 connection issues"""
    max_reconnection_attempts = 3
    attempt = 0
    
    while attempt < max_reconnection_attempts:
        try:
            logger.warning(f"Attempting to reconnect to MT5 (attempt {attempt + 1})")
            
            # Shutdown existing connection
            mt5.shutdown()
            time.sleep(5)  # Wait before reconnecting
            
            # Reconnect
            if connect_mt5():
                logger.info("Successfully reconnected to MT5")
                return True
            
            attempt += 1
            
        except Exception as e:
            logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
            attempt += 1
            time.sleep(10)
    
    logger.error("Failed to reconnect to MT5 after maximum attempts")
    return False

# =============================================================================
# MAIN LOOP (CONSERVATIVE)
# =============================================================================

def main_loop():
    """Main trading loop - CONSERVATIVE VERSION"""
    shutdown_handler = GracefulShutdown()
    last_connection_check = time.time()
    connection_check_interval = 60  # Check connection every minute
    
    logger.info("Starting CONSERVATIVE trading loop...")
    
    try:
        while not shutdown_handler.should_shutdown():
            loop_start_time = time.time()
            
            try:
                # Check MT5 connection periodically
                if time.time() - last_connection_check > connection_check_interval:
                    if not mt5.terminal_info():
                        logger.warning("MT5 connection lost, attempting to reconnect...")
                        if not handle_connection_issues():
                            break
                    last_connection_check = time.time()
                
                # Reset session counters if needed
                reset_session_counters_if_needed()
                
                # Check CONSERVATIVE risk limits
                if not check_risk_limits():
                    logger.info("Conservative risk limits active, skipping trading logic")
                    time.sleep(CONFIG['SYSTEM']['loop_delay_seconds'])
                    continue
                
                # Manage existing positions with conservative approach
                manage_open_positions()
                
                # Scan for new signals (FVG only)
                signals = scan_for_signals()
                
                # Execute signals with conservative logic
                if signals:
                    logger.info(f"Found {len(signals)} conservative trading signals")
                    execute_signals(signals)
                
                # Calculate sleep time to maintain consistent loop timing
                loop_duration = time.time() - loop_start_time
                sleep_time = max(0, CONFIG['SYSTEM']['loop_delay_seconds'] - loop_duration)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in conservative main loop: {e}")
                logger.error(traceback.format_exc())
                time.sleep(5)  # Wait before continuing
                
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error in conservative main loop: {e}")
        logger.error(traceback.format_exc())
    finally:
        cleanup_on_shutdown()

def main():
    """Entry point of the CONSERVATIVE EA"""
    try:
        # Setup logging
        setup_logging()
        
        # Display startup information
        logger.info("Capital Sniper v3.0 CONSERVATIVE - Python EA")
        logger.info("Built by OpenClaw AI Assistant")
        logger.info("CONSERVATIVE MODE: Profit-focused with enhanced risk management")
        logger.info("=" * 60)
        logger.info("CONSERVATIVE Configuration Summary:")
        logger.info(f"Risk per trade: {CONFIG['RISK']['risk_percent']}% (REDUCED)")
        logger.info(f"Max daily drawdown: {CONFIG['RISK']['max_daily_drawdown']}% (REDUCED)")
        logger.info(f"Max positions per symbol: {CONFIG['RISK']['max_positions_per_symbol']} (REDUCED)")
        logger.info(f"Min R:R ratio: {CONFIG['STRATEGY']['min_rr_ratio']} (INCREASED)")
        logger.info(f"Min confidence threshold: {CONFIG['STRATEGY']['min_confidence_threshold']} (NEW)")
        logger.info(f"Stacking disabled: Single entries only")
        logger.info(f"Wyckoff confirmation: {CONFIG['STRATEGY']['wyckoff_confirmation']} (ENABLED)")
        logger.info(f"Displacement confirmation: {CONFIG['STRATEGY']['displacement_confirmation']} (ENABLED)")
        logger.info(f"Breakeven trigger: {CONFIG['TRADE_MGMT']['breakeven_trigger_r']}R (FASTER)")
        logger.info(f"Max position time: {CONFIG['TRADE_MGMT']['max_position_hours']} hours (NEW)")
        logger.info("=" * 60)
        
        # Connect to MT5
        if not connect_mt5():
            logger.error("Failed to connect to MT5. Exiting.")
            return
        
        # Initialize trading state
        account_info = mt5.account_info()
        if account_info:
            trade_state.equity_start = account_info.equity
            trade_state.weekly_equity_start = account_info.equity
            trade_state.floating_peak = account_info.equity
            logger.info(f"Initial account equity: {account_info.equity:.2f}")
        
        # Start main loop
        main_loop()
        
    except Exception as e:
        logger.error(f"Fatal error in conservative main(): {e}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("Capital Sniper v3.0 CONSERVATIVE shutting down...")

if __name__ == "__main__":
    main()