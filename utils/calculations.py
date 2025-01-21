from typing import List

def combine_two_values(a: float, b: float) -> float:
    """Combine two WPI values using the CVC formula: C = A + B(1-A/100)."""
    # Ensure A is the larger value
    a, b = max(a, b), min(a, b)
    combined = a + b * (1 - a/100.0)
    return round(combined, 2)

def combine_wpi_values(wpi_values: List[float]) -> float:
    """Combine multiple WPI values using the CVC formula."""
    if not wpi_values:
        return 0.0
    if len(wpi_values) == 1:
        return wpi_values[0]
        
    # Sort values in descending order
    values = sorted([float(v) for v in wpi_values], reverse=True)
    
    # Combine values two at a time
    result = values[0]
    for i in range(1, len(values)):
        result = combine_two_values(result, values[i])
    
    return result
