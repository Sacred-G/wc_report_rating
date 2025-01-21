from typing import List, Dict, Any
from utils.calculations import combine_wpi_values

def format_rating_combinations(wpi_values: List[float]) -> List[str]:
    """Format the rating combination steps according to CVC process."""
    if len(wpi_values) < 2:
        return []
        
    result = []
    # Sort values in descending order
    values = sorted([float(v) for v in wpi_values], reverse=True)
    
    # Take first three highest values
    if len(values) >= 3:
        first_three = values[:3]
        first_combined = combine_wpi_values(first_three)
        result.append(f"{' C '.join(map(str, map(int, first_three)))} = {int(first_combined)}")
        
        # If there are more values, show combination with remaining values
        if len(values) > 3:
            remaining = values[3:]
            value_strs = [str(int(first_combined))] + [str(int(v)) for v in remaining]
            final_combined = combine_wpi_values(values)
            result.append(f"{' C '.join(value_strs)} = {int(final_combined)}")
    elif len(values) == 2:
        combined = combine_wpi_values(values)
        result.append(f"{' C '.join(map(str, map(int, values)))} = {int(combined)}")
    
    return result

def format_rating_output(result: Dict[str, Any]) -> str:
    """Format rating calculations in the requested layout."""
    output = []
    
    # No Apportionment Section
    if result.get("no_apportionment"):
        na = result["no_apportionment"]
        output.append("NO APPORTIONMENT     100%")
        
        # Add each impairment on its own line
        for imp in na["formatted_impairments"]:
            output.append(f"({imp['formatted_string']}) {int(imp['wpi'])}%")
            output.append(f"{imp['body_part']}")
            output.append("")  # Add blank line between impairments
        
        # Add rating combinations
        wpi_values = [imp["wpi"] for imp in na["formatted_impairments"]]
        combinations = format_rating_combinations(wpi_values)
        if combinations:
            output.extend(combinations)
            output.append(f"Combined Rating {int(na['final_pd_percent'])}%")
            
        output.append("")  # Add blank line before statistics
        output.append(f"Total of All Add-ons for Pain 2%")
        output.append("")  # Add blank line
        output.append(f"Total Weeks of PD {na['weeks']:.2f}")
        output.append("")  # Add blank line
        output.append(f"Age on DOI {na['age']}")
        output.append("")  # Add blank line
        output.append(f"Average Weekly Earnings ${na['pd_weekly_rate']:.2f} (PD Statutory Max)")
        output.append("")  # Add blank line
        output.append(f"PD Weekly Rate: ${na['pd_weekly_rate']:.2f}")
        output.append("")  # Add blank line
        output.append(f"Total PD Payout ${na['total_pd_dollars']:.2f}")
        
        if na.get("life_pension_weekly_rate"):
            output.append("")
            output.append("Return to Work Adjustments")
            output.append("")
            output.append("No RTW Adjustments for injuries on/after 1/1/2013.")
            output.append(f"Average Weekly Earnings ${na['life_pension_max_earnings']:.2f} (Life Pension Statutory Max)")
            output.append(f"Life Pension Weekly Rate ${na['life_pension_weekly_rate']:.2f}")
    
    # With Apportionment Section
    if result.get("with_apportionment"):
        wa = result["with_apportionment"]
        output.append("\nWITH APPOTIONMENT 90% and 80% CS LS")
        
        # Add each impairment on its own line
        for imp in wa["formatted_impairments"]:
            output.append(f"({imp['formatted_string']}) {int(imp['wpi'])}%")
            output.append(f"{imp['body_part']}")
            output.append("")  # Add blank line between impairments
        
        # Add rating combinations
        wpi_values = [imp["wpi"] for imp in wa["formatted_impairments"]]
        combinations = format_rating_combinations(wpi_values)
        if combinations:
            output.extend(combinations)
            output.append(f"Combined Rating {int(wa['final_pd_percent'])}%")
            
        output.append("")  # Add blank line before statistics
        output.append(f"Total of All Add-ons for Pain 2%")
        output.append("")  # Add blank line
        output.append(f"Total Weeks of PD {wa['weeks']:.2f}")
        output.append("")  # Add blank line
        output.append(f"Age on DOI {wa['age']}")
        output.append("")  # Add blank line
        output.append(f"Average Weekly Earnings ${wa['pd_weekly_rate']:.2f} (PD Statutory Max)")
        output.append("")  # Add blank line
        output.append(f"PD Weekly Rate: ${wa['pd_weekly_rate']:.2f}")
        output.append("")  # Add blank line
        output.append(f"Total PD Payout ${wa['total_pd_dollars']:.2f}")
        
        if wa.get("life_pension_weekly_rate"):
            output.append("")
            output.append("Return to Work Adjustments")
            output.append("")
            output.append("No RTW Adjustments for injuries on/after 1/1/2013.")
            output.append(f"Average Weekly Earnings ${wa['life_pension_max_earnings']:.2f} (Life Pension Statutory Max)")
            output.append(f"Life Pension Weekly Rate ${wa['life_pension_weekly_rate']:.2f}")
    
    # Add CMS analysis if available
    if result.get("detailed_summary", {}).get("cms_analysis"):
        output.append("\nCMS Analysis")
        output.append(f"CMS Analysis ${result['detailed_summary']['cms_analysis']:.2f}")
        
    return "\n".join(output)
