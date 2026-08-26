"""
NEXORA — Payment Utilities

Deterministic financial math utilities.
"""
from decimal import Decimal


def convert_decimal_to_paise(amount: Decimal) -> int:
    """
    Converts a Decimal amount (INR) to an exact integer (paise) for Razorpay.
    
    Requirements:
    - Rejects negative or zero amounts.
    - Rejects fractional paise (e.g., 10.505).
    - Returns exact int.
    """
    if not isinstance(amount, Decimal):
        raise TypeError(f"Amount must be Decimal, got {type(amount)}")
        
    if amount <= 0:
        raise ValueError("Amount must be strictly positive")
        
    # Check for fractional paise
    # Quantize to 0.01. If it doesn't match original, there are fractional paise.
    rounded = amount.quantize(Decimal("0.01"))
    if rounded != amount:
        raise ValueError(f"Amount {amount} contains fractional paise which are not supported.")
        
    return int(rounded * Decimal("100"))
