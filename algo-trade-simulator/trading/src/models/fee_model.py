"""
Fee model for calculating trading fees based on exchange fee tiers.
"""
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeeModel:
    """
    Model for calculating trading fees based on exchange fee tiers.
    """
    def __init__(self):
        """
        Initialize the fee model with default fee tiers.
        """
        # Default fee tiers for OKX
        # Source: https://www.okx.com/fees
        self.fee_tiers = {
            'OKX': {
                'spot': {
                    'maker': {
                        'VIP0': 0.0010,  # 0.10%
                        'VIP1': 0.0008,  # 0.08%
                        'VIP2': 0.0006,  # 0.06%
                        'VIP3': 0.0004,  # 0.04%
                        'VIP4': 0.0002,  # 0.02%
                        'VIP5': 0.0000,  # 0.00%
                    },
                    'taker': {
                        'VIP0': 0.0015,  # 0.15%
                        'VIP1': 0.0010,  # 0.10%
                        'VIP2': 0.0008,  # 0.08%
                        'VIP3': 0.0005,  # 0.05%
                        'VIP4': 0.0003,  # 0.03%
                        'VIP5': 0.0001,  # 0.01%
                    }
                },
                'futures': {
                    'maker': {
                        'VIP0': 0.0002,  # 0.02%
                        'VIP1': 0.0001,  # 0.01%
                        'VIP2': 0.0000,  # 0.00%
                        'VIP3': -0.0001,  # -0.01% (rebate)
                        'VIP4': -0.0002,  # -0.02% (rebate)
                        'VIP5': -0.0003,  # -0.03% (rebate)
                    },
                    'taker': {
                        'VIP0': 0.0005,  # 0.05%
                        'VIP1': 0.0004,  # 0.04%
                        'VIP2': 0.0003,  # 0.03%
                        'VIP3': 0.0002,  # 0.02%
                        'VIP4': 0.0001,  # 0.01%
                        'VIP5': 0.0000,  # 0.00%
                    }
                }
            }
        }
        
    def get_fee_rate(self, 
                    exchange: str, 
                    market_type: str, 
                    fee_tier: str, 
                    is_maker: bool) -> float:
        """
        Get the fee rate for a specific exchange, market type, fee tier, and order type.
        
        Args:
            exchange: Exchange name (e.g., 'OKX')
            market_type: Market type (e.g., 'spot', 'futures')
            fee_tier: Fee tier (e.g., 'VIP0', 'VIP1')
            is_maker: Whether the order is a maker order
            
        Returns:
            float: Fee rate as a decimal (e.g., 0.001 for 0.1%)
        """
        if exchange not in self.fee_tiers:
            logger.warning(f"Unknown exchange: {exchange}, using default OKX fees")
            exchange = 'OKX'
            
        if market_type not in self.fee_tiers[exchange]:
            logger.warning(f"Unknown market type: {market_type}, using spot fees")
            market_type = 'spot'
            
        order_type = 'maker' if is_maker else 'taker'
        
        if fee_tier not in self.fee_tiers[exchange][market_type][order_type]:
            logger.warning(f"Unknown fee tier: {fee_tier}, using VIP0 fees")
            fee_tier = 'VIP0'
            
        return self.fee_tiers[exchange][market_type][order_type][fee_tier]
        
    def calculate_fee(self, 
                     order_value: float, 
                     exchange: str, 
                     market_type: str, 
                     fee_tier: str, 
                     maker_proportion: float) -> Dict[str, float]:
        """
        Calculate the fee for an order.
        
        Args:
            order_value: Value of the order in quote currency
            exchange: Exchange name (e.g., 'OKX')
            market_type: Market type (e.g., 'spot', 'futures')
            fee_tier: Fee tier (e.g., 'VIP0', 'VIP1')
            maker_proportion: Proportion of the order executed as maker (0.0 to 1.0)
            
        Returns:
            Dict: Dictionary with maker_fee, taker_fee, and total_fee
        """
        maker_rate = self.get_fee_rate(exchange, market_type, fee_tier, True)
        taker_rate = self.get_fee_rate(exchange, market_type, fee_tier, False)
        
        maker_value = order_value * maker_proportion
        taker_value = order_value * (1 - maker_proportion)
        
        maker_fee = maker_value * maker_rate
        taker_fee = taker_value * taker_rate
        total_fee = maker_fee + taker_fee
        
        return {
            'maker_fee': maker_fee,
            'taker_fee': taker_fee,
            'total_fee': total_fee,
            'effective_rate': total_fee / order_value if order_value > 0 else 0
        }
        
    def add_exchange_fee_tiers(self, exchange: str, fee_tiers: Dict):
        """
        Add or update fee tiers for an exchange.
        
        Args:
            exchange: Exchange name
            fee_tiers: Fee tier structure
        """
        self.fee_tiers[exchange] = fee_tiers
        logger.info(f"Updated fee tiers for {exchange}")
        
    def get_available_exchanges(self) -> List[str]:
        """
        Get a list of available exchanges.
        
        Returns:
            List[str]: List of exchange names
        """
        return list(self.fee_tiers.keys())
        
    def get_available_fee_tiers(self, exchange: str, market_type: str) -> List[str]:
        """
        Get a list of available fee tiers for an exchange and market type.
        
        Args:
            exchange: Exchange name
            market_type: Market type
            
        Returns:
            List[str]: List of fee tier names
        """
        if exchange not in self.fee_tiers:
            return []
            
        if market_type not in self.fee_tiers[exchange]:
            return []
            
        # Assuming maker and taker have the same tiers
        return list(self.fee_tiers[exchange][market_type]['maker'].keys())
