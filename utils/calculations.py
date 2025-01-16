from typing import List

def combine_wpi_values(wpi_values: List[float]) -> float:
    """Combine multiple WPI values using the standard formula."""
    product_term = 1.0
    for wpi in wpi_values:
        product_term *= (1 - wpi/100.0)
    combined_decimal = 1 - product_term
    return round(combined_decimal * 100, 2)
