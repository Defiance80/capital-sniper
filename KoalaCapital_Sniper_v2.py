#!/usr/bin/env python3
"""
KoalaCapital Sniper v2.0 - Python Implementation
Copyright 2025, Koala Capital Sniper AI

Complete rewrite of the MQL5 EA fixing all 10 documented bugs and implementing
production enhancements for automated FVG/Wyckoff trading strategy.

Version 2.00 Changelog:
- FIXED: Division by zero on sessionEquityStart initialization
- FIXED: Session reset firing every tick - now uses proper static flags
- FIXED: Per-symbol point/digits handling throughout all calculations
- FIXED: CountOpenTrades() stale data - proper position selection
- FIXED: Partial close rounding to 0.00 - volume validation
- FIXED: Wyckoff array overrun - dynamic sizing
- FIXED: RegisterTrade() undercount - proper StackCount increment
- FIXED: Session overlap 13-15 now counts for both London AND NY
- FIXED: Trade management stages now use proper else-if gating
- FIXED: Dead code removed, BaseRiskPercent properly implemented
- ENHANCED: Dynamic position sizing based on risk percentage
- ENHANCED: Per-symbol magic numbers to avoid conflicts
- ENHANCED: Trailing drawdown from peak tracking
- ENHANCED: Complete trade logging to file
- ENHANCED: Error handling with retries on OrderSend
- ENHANCED: Max spread filter
- ENHANCED: Proper order comments for identification
"""

import MetaTrader5 as mt5
import time
import logging
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import math
import os


@dataclass
class SessionData:
    """Per-symbol session tracking data"""
    setup_count_london: int = 0
    setup_count_ny: int = 0
    london_session_started: bool = False
    ny_session_started: bool = False
    last_session_reset: datetime = None


@dataclass
class TradeConfig:
    """Configuration parameters for the EA"""
    # Risk Management
    base_risk_percent: float = 0.75
    max_daily_loss_percent: float = 30.0
    max_drawdown_from_peak: float = 20.0
    max_setups_per_session: int = 3
    max_trades_per_symbol: int = 3
    max_spread_pips: float = 3.0
    
    # Strategy Parameters
    sl_buffer_pips: int = 2
    break_even_points: int = 15
    partial_close_pct: float = 0.25
    trailing_start_pips: int = 25
    trailing_step_pips: int = 15
    stack_count: int = 2
    fvg_deviation_pips: int = 10
    wyckoff_lookback: int = 3
    exhaustion_pips: int = 20
    
    # System Settings
    magic_base: int = 987654
    enable_logging: bool = True
    order_retries: int = 3
    scan_interval_seconds: int = 5


class KoalaCapitalSniper:
    """
    KoalaCapital Sniper v2.0 - Python Implementation
    
    Automated FVG/Wyckoff trading strategy with comprehensive risk management,
    trade management, and bug fixes from the original MQL5 version.
    """
    
    def __init__(self, config: TradeConfig = None):
        """Initialize the trading bot with configuration"""
        self.config = config or TradeConfig()
        self.traded_symbols = [
            "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD",
            "NZDUSD", "USDCHF", "EURJPY", "GBPJPY", "XAUUSD"
        ]
        
        # Session tracking - fixed array sizing
        self.session_data: Dict[str, SessionData] = {
            symbol: SessionData() for symbol in self.traded_symbols
        }
        
        # Equity tracking - fixed initialization
        self.session_equity_start: float = 0.0
        self.floating_peak: float = 0.0
        self.stop_all_trading: bool = False
        self.equity_initialized: bool = False
        
        # Session reset flags - fixed to prevent every-tick resets
        self.london_reset_done: bool = False
        self.ny_reset_done: bool = False
        self.last_reset_date: str = ""
        
        # Partial close tracking - prevent multiple closes
        self.last_partial_close: Dict[str, datetime] = {}
        
        # Setup logging
        self._setup_logging()
        
        # Initialize MT5 connection
        self._initialize_mt5()
    
    def _setup_logging(self) -> None:
        """Setup logging to both file and console"""
        if not self.config.enable_logging:
            return
            
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Setup file handler
        log_filename = f"logs/KoalaSniper_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("KoalaCapital Sniper v2.0 - Python Implementation Started")
    
    def _initialize_mt5(self) -> bool:
        """Initialize MetaTrader5 connection"""
        if not mt5.initialize():
            self.logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
            
        # Log account info
        account_info = mt5.account_info()
        if account_info is None:
            self.logger.error("Failed to get account info")
            return False
            
        self.logger.info(f"Connected to account: {account_info.login}")
        self.logger.info(f"Account balance: {account_info.balance}")
        self.logger.info(f"Account equity: {account_info.equity}")
        
        # Initialize equity tracking - fixed division by zero
        self.session_equity_start = account_info.equity
        self.floating_peak = self.session_equity_start
        self.equity_initialized = True
        
        self.logger.info(f"Equity tracking initialized - Baseline: {self.session_equity_start}")
        return True
    
    def _get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol-specific information - fixed per-symbol handling"""
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return None
            
        return {
            'point': symbol_info.point,
            'digits': symbol_info.digits,
            'tick_value': symbol_info.trade_tick_value,
            'tick_size': symbol_info.trade_tick_size,
            'min_lot': symbol_info.volume_min,
            'max_lot': symbol_info.volume_max,
            'step_lot': symbol_info.volume_step,
            'spread': symbol_info.spread
        }
    
    def _get_spread_in_pips(self, symbol: str) -> float:
        """Calculate spread in pips for the specific symbol"""
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            return float('inf')  # Skip trading if we can't get info
            
        spread = symbol_info['spread']
        point = symbol_info['point']
        digits = symbol_info['digits']
        
        # Convert to pips (handle 5-digit vs 4-digit quotes)
        pip_factor = 10 if digits in [3, 5] else 1
        return spread * point * pip_factor / point
    
    def _check_session_reset(self) -> None:
        """Check and handle session resets - fixed to prevent every-tick resets"""
        current_time = datetime.now()
        current_date = current_time.strftime("%Y-%m-%d")
        current_hour = current_time.hour
        
        # Reset daily flags if date changed
        if self.last_reset_date != current_date:
            self.london_reset_done = False
            self.ny_reset_done = False
            self.last_reset_date = current_date
        
        # London session reset (08:00) - once per day
        if current_hour == 8 and not self.london_reset_done:
            self._reset_session_counters(reset_london=True, reset_ny=False)
            self.london_reset_done = True
            self.logger.info("London session reset at 08:00")
            self._reset_equity_tracking("London session start")
        
        # NY session reset (13:00) - once per day  
        if current_hour == 13 and not self.ny_reset_done:
            self._reset_session_counters(reset_london=False, reset_ny=True)
            self.ny_reset_done = True
            self.logger.info("NY session reset at 13:00")
            self._reset_equity_tracking("NY session start")
    
    def _reset_session_counters(self, reset_london: bool, reset_ny: bool) -> None:
        """Reset session counters for all symbols"""
        for symbol in self.traded_symbols:
            if reset_london:
                self.session_data[symbol].setup_count_london = 0
                self.session_data[symbol].london_session_started = True
            if reset_ny:
                self.session_data[symbol].setup_count_ny = 0
                self.session_data[symbol].ny_session_started = True
    
    def _reset_equity_tracking(self, reason: str) -> None:
        """Reset equity tracking baseline"""
        account_info = mt5.account_info()
        if account_info:
            self.session_equity_start = account_info.equity
            self.floating_peak = self.session_equity_start
            self.stop_all_trading = False
            self.logger.info(f"Equity tracking reset - {reason} - New baseline: {self.session_equity_start}")
    
    def _update_floating_peak(self) -> None:
        """Update floating peak for trailing drawdown tracking - fixed implementation"""
        account_info = mt5.account_info()
        if account_info and account_info.equity > self.floating_peak:
            self.floating_peak = account_info.equity
    
    def _check_drawdown_limits(self) -> bool:
        """Check if drawdown limits are breached"""
        if not self.equity_initialized or self.session_equity_start <= 0:
            return False
            
        account_info = mt5.account_info()
        if not account_info:
            return False
            
        current_equity = account_info.equity
        
        # Daily drawdown check - fixed division by zero
        daily_drawdown = (self.session_equity_start - current_equity) / self.session_equity_start * 100.0
        if daily_drawdown >= self.config.max_daily_loss_percent:
            if not self.stop_all_trading:
                self.stop_all_trading = True
                self.logger.warning(f"DAILY DRAWDOWN HALT: {daily_drawdown:.2f}%")
                self._close_all_profitable_positions()
            return True
        
        # Trailing drawdown from peak check - fixed implementation
        if self.floating_peak > 0:
            peak_drawdown = (self.floating_peak - current_equity) / self.floating_peak * 100.0
            if peak_drawdown >= self.config.max_drawdown_from_peak:
                if not self.stop_all_trading:
                    self.stop_all_trading = True
                    self.logger.warning(f"PEAK DRAWDOWN HALT: {peak_drawdown:.2f}% from peak {self.floating_peak}")
                    self._close_all_profitable_positions()
                return True
        
        return False
    
    def _is_in_trading_session(self, symbol: str) -> bool:
        """Check if symbol is in valid trading session - fixed overlap handling"""
        current_hour = datetime.now().hour
        symbol_data = self.session_data[symbol]
        
        # London: 08:00 - 15:59
        in_london = 8 <= current_hour <= 15
        # NY: 13:00 - 20:59
        in_ny = 13 <= current_hour <= 20
        
        # Fixed: Overlap 13:00-15:59 counts for BOTH sessions
        if 13 <= current_hour <= 15:
            # Check both session limits during overlap
            london_ok = symbol_data.setup_count_london < self.config.max_setups_per_session
            ny_ok = symbol_data.setup_count_ny < self.config.max_setups_per_session
            return london_ok or ny_ok  # Can trade if either session has space
        
        # London only (08-12)
        if in_london and not in_ny:
            return symbol_data.setup_count_london < self.config.max_setups_per_session
        
        # NY only (16-20)
        if in_ny and not in_london:
            return symbol_data.setup_count_ny < self.config.max_setups_per_session
        
        return False  # Outside trading hours
    
    def _count_open_trades(self, symbol: str) -> int:
        """Count open positions for symbol - fixed stale data issue"""
        count = 0
        positions = mt5.positions_get(symbol=symbol)
        
        if positions is None:
            return 0
            
        for position in positions:
            # Check if it's our position based on magic number range
            magic_range_start = self.config.magic_base
            magic_range_end = self.config.magic_base + len(self.traded_symbols)
            
            if magic_range_start <= position.magic < magic_range_end:
                count += 1
        
        return count
    
    def _get_symbol_index(self, symbol: str) -> int:
        """Get symbol index for magic number calculation"""
        try:
            return self.traded_symbols.index(symbol)
        except ValueError:
            return -1
    
    def _calculate_lot_size(self, symbol: str, risk_amount: float, sl_distance: float) -> float:
        """Calculate dynamic lot size based on risk - fixed implementation"""
        if sl_distance <= 0:
            return 0.0
            
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            return 0.0
            
        tick_value = symbol_info['tick_value']
        tick_size = symbol_info['tick_size']
        min_lot = symbol_info['min_lot']
        max_lot = symbol_info['max_lot']
        step_lot = symbol_info['step_lot']
        
        if tick_value == 0 or tick_size == 0:
            return 0.0
        
        # Calculate lot size
        lot_size = risk_amount / (sl_distance / tick_size * tick_value)
        
        # Normalize to step
        lot_size = math.floor(lot_size / step_lot) * step_lot
        lot_size = round(lot_size, 2)
        
        # Apply limits
        lot_size = max(lot_size, min_lot)
        lot_size = min(lot_size, max_lot)
        
        return lot_size
    
    def _get_rates_data(self, symbol: str, count: int = 10) -> Optional[List]:
        """Get M5 rates data for symbol"""
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, count)
        if rates is None or len(rates) < count:
            return None
        
        # Convert to list and reverse so [0] = oldest, [4] = newest closed bar
        rates_list = rates.tolist()
        rates_list.reverse()
        return rates_list
    
    def _detect_fvg_pattern(self, symbol: str, rates: List) -> Optional[Tuple[str, float]]:
        """Detect Fair Value Gap patterns - fixed per-symbol calculations"""
        if len(rates) < 5:
            return None
            
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            return None
            
        point = symbol_info['point']
        digits = symbol_info['digits']
        
        # Calculate deviation based on symbol's point size
        pip_factor = 10 if digits in [3, 5] else 1
        deviation = self.config.fvg_deviation_pips * point * pip_factor
        
        # Bearish FVG (rates[3].high > rates[4].high + deviation)
        if rates[3]['high'] > rates[4]['high'] + deviation:
            entry_price = rates[3]['high'] - deviation
            return ("SELL", entry_price)
        
        # Bullish FVG (rates[3].low < rates[4].low - deviation)
        if rates[3]['low'] < rates[4]['low'] - deviation:
            entry_price = rates[3]['low'] + deviation
            return ("BUY", entry_price)
        
        return None
    
    def _confirm_wyckoff_signal(self, direction: str, rates: List) -> bool:
        """Confirm Wyckoff signal - fixed dynamic array sizing"""
        if len(rates) < max(2, self.config.wyckoff_lookback):
            return False
        
        if direction == "BUY":
            # Check for lower lows (accumulation/spring)
            return rates[0]['low'] < rates[1]['low']
        elif direction == "SELL":
            # Check for higher highs (distribution/upthrust)
            return rates[0]['high'] > rates[1]['high']
        
        return False
    
    def _check_exhaustion_filter(self, symbol: str, rates: List) -> bool:
        """Check exhaustion filter - fixed per-symbol calculations"""
        if len(rates) < 1:
            return True  # Skip if no data
            
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            return True
            
        point = symbol_info['point']
        digits = symbol_info['digits']
        
        # Calculate exhaustion distance based on symbol's point size
        pip_factor = 10 if digits in [3, 5] else 1
        exhaustion_distance = self.config.exhaustion_pips * point * pip_factor
        
        # Check most recent closed bar range
        recent_range = rates[0]['high'] - rates[0]['low']
        return recent_range >= exhaustion_distance
    
    def _calculate_sl_tp(self, symbol: str, direction: str, entry_price: float, rates: List) -> Tuple[float, float]:
        """Calculate stop loss and take profit - fixed per-symbol calculations"""
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            return None, None
            
        point = symbol_info['point']
        digits = symbol_info['digits']
        
        # Calculate buffer and BE distance based on symbol's point size
        pip_factor = 10 if digits in [3, 5] else 1
        sl_buffer = self.config.sl_buffer_pips * point * pip_factor
        be_distance = self.config.break_even_points * point
        
        if direction == "SELL":
            sl_price = rates[4]['high'] + sl_buffer
            tp_price = entry_price - be_distance * 2
        else:  # BUY
            sl_price = rates[4]['low'] - sl_buffer
            tp_price = entry_price + be_distance * 2
        
        return round(sl_price, digits), round(tp_price, digits)
    
    def _place_order_with_retry(self, symbol: str, order_type: int, volume: float, 
                               price: float, sl: float, tp: float, magic: int, comment: str) -> bool:
        """Place order with retry mechanism"""
        for attempt in range(self.config.order_retries):
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_DAY,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                self.logger.info(f"Order placed successfully: {comment}")
                return True
            else:
                self.logger.warning(f"Order failed (attempt {attempt + 1}): {result.retcode} - {result.comment}")
                time.sleep(0.5)  # Wait before retry
        
        return False
    
    def _place_stacked_orders(self, symbol: str, direction: str, entry_price: float, rates: List) -> bool:
        """Place stacked orders - fixed stack count tracking"""
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            return False
            
        # Calculate SL and TP
        sl_price, tp_price = self._calculate_sl_tp(symbol, direction, entry_price, rates)
        if sl_price is None or tp_price is None:
            return False
        
        # Calculate position size - fixed dynamic sizing
        account_info = mt5.account_info()
        if not account_info:
            return False
            
        risk_amount = account_info.equity * self.config.base_risk_percent / 100.0
        sl_distance = abs(entry_price - sl_price)
        lot_size = self._calculate_lot_size(symbol, risk_amount, sl_distance)
        
        if lot_size <= 0:
            self.logger.warning(f"Invalid lot size calculated for {symbol}")
            return False
        
        # Determine order type
        order_type = mt5.ORDER_TYPE_SELL_LIMIT if direction == "SELL" else mt5.ORDER_TYPE_BUY_LIMIT
        
        # Calculate magic number - fixed per-symbol magic
        symbol_index = self._get_symbol_index(symbol)
        if symbol_index < 0:
            return False
        magic_number = self.config.magic_base + symbol_index
        
        orders_placed = 0
        point = symbol_info['point']
        
        # Place stacked orders
        for i in range(self.config.stack_count):
            stack_entry = entry_price
            if i > 0:
                # Offset subsequent orders by 2 points
                offset = i * 2 * point
                if direction == "SELL":
                    stack_entry -= offset
                else:
                    stack_entry += offset
            
            # Create descriptive comment
            comment = f"KoalaSniper_v2_{symbol}_{direction}_Stack{i+1}"
            
            # Place order
            if self._place_order_with_retry(symbol, order_type, lot_size, stack_entry, 
                                          sl_price, tp_price, magic_number, comment):
                orders_placed += 1
                self.logger.info(f"Stacked order {i+1} placed: {comment} Entry={stack_entry:.{symbol_info['digits']}f}")
        
        # Register trade - fixed to count actual stack count
        if orders_placed > 0:
            self._register_trade(symbol, orders_placed)
            return True
        
        return False
    
    def _register_trade(self, symbol: str, trade_count: int) -> None:
        """Register trade in session counters - fixed stack count and overlap handling"""
        current_hour = datetime.now().hour
        symbol_data = self.session_data[symbol]
        
        # Fixed: Overlap 13-15 increments both sessions
        if 13 <= current_hour <= 15:
            symbol_data.setup_count_london += trade_count
            symbol_data.setup_count_ny += trade_count
            self.logger.info(f"Trade registered for {symbol} in BOTH sessions (overlap). Count: {trade_count}")
        # London only
        elif 8 <= current_hour <= 15:
            symbol_data.setup_count_london += trade_count
            self.logger.info(f"Trade registered for {symbol} in London session. Count: {trade_count}")
        # NY only
        elif 13 <= current_hour <= 20:
            symbol_data.setup_count_ny += trade_count
            self.logger.info(f"Trade registered for {symbol} in NY session. Count: {trade_count}")
    
    def _check_symbol_for_entry(self, symbol: str) -> None:
        """Check individual symbol for entry opportunities"""
        # Check if symbol is available
        if not mt5.symbol_select(symbol, True):
            return
        
        # Check trading session
        if not self._is_in_trading_session(symbol):
            return
        
        # Check max trades per symbol
        if self._count_open_trades(symbol) >= self.config.max_trades_per_symbol:
            return
        
        # Check spread filter
        if self._get_spread_in_pips(symbol) > self.config.max_spread_pips:
            return
        
        # Get rates data
        rates = self._get_rates_data(symbol)
        if not rates:
            return
        
        # Check for FVG pattern
        fvg_result = self._detect_fvg_pattern(symbol, rates)
        if not fvg_result:
            return
        
        direction, entry_price = fvg_result
        
        # Confirm with Wyckoff filter
        if not self._confirm_wyckoff_signal(direction, rates):
            return
        
        # Check exhaustion filter (skip if exhausted)
        if self._check_exhaustion_filter(symbol, rates):
            return
        
        # Place stacked orders
        self._place_stacked_orders(symbol, direction, entry_price, rates)
    
    def _is_net_profitable(self, position) -> bool:
        """Check if position is net profitable after all costs"""
        profit = position.profit
        swap = position.swap
        volume = position.volume
        symbol = position.symbol
        
        # Estimate commission (rough calculation)
        commission = volume * 7.0
        
        # Calculate spread cost
        symbol_info = self._get_symbol_info(symbol)
        if symbol_info:
            spread = symbol_info['spread']
            point = symbol_info['point']
            tick_value = symbol_info['tick_value']
            spread_cost = spread * point * tick_value * volume
        else:
            spread_cost = 0
        
        net_profit = profit + swap - commission - spread_cost
        return net_profit > 0
    
    def _move_to_break_even(self, position) -> None:
        """Move position to break-even - fixed per-symbol calculations"""
        symbol = position.symbol
        ticket = position.ticket
        open_price = position.price_open
        current_sl = position.sl
        position_type = position.type
        
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            return
        
        point = symbol_info['point']
        digits = symbol_info['digits']
        pip_factor = 10 if digits in [3, 5] else 1
        buffer = self.config.sl_buffer_pips * point * pip_factor
        
        if position_type == mt5.ORDER_TYPE_BUY:
            new_sl = open_price + buffer
            if new_sl > current_sl:  # Only move if better
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "position": ticket,
                    "sl": round(new_sl, digits),
                    "tp": position.tp
                }
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.logger.info(f"Break-even applied to {symbol} ticket {ticket}")
        else:  # SELL
            new_sl = open_price - buffer
            if new_sl < current_sl:  # Only move if better
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "position": ticket,
                    "sl": round(new_sl, digits),
                    "tp": position.tp
                }
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.logger.info(f"Break-even applied to {symbol} ticket {ticket}")
    
    def _partial_close_position(self, position) -> None:
        """Partially close position - fixed volume validation"""
        symbol = position.symbol
        ticket = position.ticket
        current_volume = position.volume
        
        close_volume = round(current_volume * self.config.partial_close_pct, 2)
        
        # Fixed: Check minimum volume before attempting close
        symbol_info = self._get_symbol_info(symbol)
        if symbol_info and close_volume < symbol_info['min_lot']:
            self.logger.info(f"Partial close skipped for {symbol} - volume too small: {close_volume}")
            return
        
        # Check cooldown period to prevent multiple partial closes
        last_close = self.last_partial_close.get(symbol)
        if last_close and (datetime.now() - last_close).total_seconds() < 300:  # 5 minutes
            return
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": close_volume,
            "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "position": ticket,
            "comment": f"Partial close {self.config.partial_close_pct*100:.0f}%"
        }
        
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.last_partial_close[symbol] = datetime.now()
            self.logger.info(f"Partial close executed for {symbol} ticket {ticket} Volume: {close_volume}")
    
    def _apply_trailing_stop(self, position) -> None:
        """Apply trailing stop - fixed per-symbol calculations"""
        symbol = position.symbol
        ticket = position.ticket
        current_sl = position.sl
        position_type = position.type
        
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return
        
        current_price = tick.bid if position_type == mt5.ORDER_TYPE_BUY else tick.ask
        
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            return
        
        point = symbol_info['point']
        digits = symbol_info['digits']
        pip_factor = 10 if digits in [3, 5] else 1
        trail_distance = self.config.trailing_step_pips * point * pip_factor
        
        if position_type == mt5.ORDER_TYPE_BUY:
            new_sl = current_price - trail_distance
            if new_sl > current_sl:  # Only move if better
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "position": ticket,
                    "sl": round(new_sl, digits),
                    "tp": position.tp
                }
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.logger.info(f"Trailing stop applied to {symbol} ticket {ticket} New SL: {new_sl:.{digits}f}")
        else:  # SELL
            new_sl = current_price + trail_distance
            if new_sl < current_sl:  # Only move if better
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "position": ticket,
                    "sl": round(new_sl, digits),
                    "tp": position.tp
                }
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.logger.info(f"Trailing stop applied to {symbol} ticket {ticket} New SL: {new_sl:.{digits}f}")
    
    def _manage_position(self, position) -> None:
        """Manage individual position - fixed else-if gating"""
        if not self._is_net_profitable(position):
            return
        
        symbol = position.symbol
        open_price = position.price_open
        position_type = position.type
        
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return
        
        current_price = tick.bid if position_type == mt5.ORDER_TYPE_BUY else tick.ask
        
        # Calculate profit in pips - fixed per-symbol calculations
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            return
        
        point = symbol_info['point']
        if position_type == mt5.ORDER_TYPE_BUY:
            profit_pips = (current_price - open_price) / point
        else:
            profit_pips = (open_price - current_price) / point
        
        # Fixed: Management stages with proper else-if gating
        if profit_pips >= self.config.trailing_start_pips:
            # Stage 3: Trailing Stop
            self._apply_trailing_stop(position)
        elif profit_pips >= self.config.break_even_points * 2:
            # Stage 2: Partial Close
            self._partial_close_position(position)
        elif profit_pips >= self.config.break_even_points:
            # Stage 1: Break Even
            self._move_to_break_even(position)
    
    def _manage_all_trades(self) -> None:
        """Manage all open trades"""
        positions = mt5.positions_get()
        if positions is None:
            return
        
        for position in positions:
            # Check if it's our position
            magic_range_start = self.config.magic_base
            magic_range_end = self.config.magic_base + len(self.traded_symbols)
            
            if magic_range_start <= position.magic < magic_range_end:
                self._manage_position(position)
    
    def _close_all_profitable_positions(self) -> None:
        """Close all profitable positions during emergency halt"""
        positions = mt5.positions_get()
        if positions is None:
            return
        
        for position in positions:
            # Check if it's our position
            magic_range_start = self.config.magic_base
            magic_range_end = self.config.magic_base + len(self.traded_symbols)
            
            if magic_range_start <= position.magic < magic_range_end:
                if self._is_net_profitable(position):
                    request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": position.symbol,
                        "volume": position.volume,
                        "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                        "position": position.ticket,
                        "comment": "Emergency close - drawdown halt"
                    }
                    
                    result = mt5.order_send(request)
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        self.logger.info(f"Emergency close: {position.symbol} ticket {position.ticket}")
    
    def _check_all_symbols_for_entry(self) -> None:
        """Check all symbols for entry opportunities"""
        if self.stop_all_trading:
            return
        
        for symbol in self.traded_symbols:
            try:
                self._check_symbol_for_entry(symbol)
            except Exception as e:
                self.logger.error(f"Error checking {symbol} for entry: {str(e)}")
    
    def run(self) -> None:
        """Main trading loop"""
        self.logger.info("KoalaCapital Sniper v2.0 started")
        
        try:
            while True:
                # Check session resets
                self._check_session_reset()
                
                # Update floating peak
                self._update_floating_peak()
                
                # Check drawdown limits
                if self._check_drawdown_limits():
                    time.sleep(self.config.scan_interval_seconds)
                    continue
                
                # Manage existing trades
                self._manage_all_trades()
                
                # Look for new entries
                self._check_all_symbols_for_entry()
                
                # Sleep before next iteration
                time.sleep(self.config.scan_interval_seconds)
                
        except KeyboardInterrupt:
            self.logger.info("Trading bot stopped by user")
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
        finally:
            self._shutdown()
    
    def _shutdown(self) -> None:
        """Clean shutdown"""
        self.logger.info("Shutting down KoalaCapital Sniper v2.0")
        mt5.shutdown()


if __name__ == "__main__":
    """
    Entry point for the KoalaCapital Sniper v2.0 Python implementation
    
    To run with custom configuration:
    config = TradeConfig()
    config.base_risk_percent = 1.0  # 1% risk per trade
    config.max_daily_loss_percent = 25.0  # 25% daily halt
    bot = KoalaCapitalSniper(config)
    bot.run()
    """
    
    # Use default configuration
    config = TradeConfig()
    
    # Create and run the bot
    bot = KoalaCapitalSniper(config)
    bot.run()