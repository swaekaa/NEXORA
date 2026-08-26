import pytest
from decimal import Decimal
from app.payments.utils import convert_decimal_to_paise

def test_valid_conversion():
    assert convert_decimal_to_paise(Decimal("10500.00")) == 1050000
    assert convert_decimal_to_paise(Decimal("1.00")) == 100
    assert convert_decimal_to_paise(Decimal("0.50")) == 50
    assert convert_decimal_to_paise(Decimal("0.01")) == 1

def test_rejects_negative_or_zero():
    with pytest.raises(ValueError, match="strictly positive"):
        convert_decimal_to_paise(Decimal("0.00"))
        
    with pytest.raises(ValueError, match="strictly positive"):
        convert_decimal_to_paise(Decimal("-10.00"))

def test_rejects_fractional_paise():
    with pytest.raises(ValueError, match="fractional paise"):
        convert_decimal_to_paise(Decimal("10.505"))
        
    with pytest.raises(ValueError, match="fractional paise"):
        convert_decimal_to_paise(Decimal("0.001"))

def test_rejects_float():
    with pytest.raises(TypeError, match="must be Decimal"):
        convert_decimal_to_paise(10500.00)  # type: ignore
