import streamlit as st

def get_card_css():
    return """
    <style>
    .card {
        background: #f0f0f0; /* Light gray background for better contrast */
        border-radius: 8px;
        padding: 20px;
        margin: 10px 0;

        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .card h3 {
        color: #1f77b4;
        margin-bottom: 10px;
    }
    .card h4 {
        color: #2c3e50;
        margin: 15px 0 10px 0;
    }
    .card-content {
        margin: 10px 0;
     
    }
    .button-row {
        display: flex;
        gap: 10px;
        margin-top: 10px;
    }
    .copy-btn, .download-btn {
        background-color: #1f77b4;
        color: white;
        border: none;
        padding: 5px 15px;
        border-radius: 4px;
        cursor: pointer;
    }
    .copy-btn:hover, .download-btn:hover {
        background-color: #155987;
    }
    </style>
    """

def render_styled_card(title, content, card_id):
    download_fn = f"downloadData_{card_id}"
    copy_fn = f"copyData_{card_id}"
    
    js_code = f"""
    <script>
    function {download_fn}() {{
        const data = `{content}`;
        const blob = new Blob([data], {{ type: 'text/plain' }});
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = '{title.lower().replace(" ", "_")}.txt';
        a.click();
    }}
    
    function {copy_fn}() {{
        const data = `{content}`;
        navigator.clipboard.writeText(data).then(() => {{
            alert('Copied to clipboard!');
        }});
    }}
    </script>
    
    <div class="card">
        <h3>{title}</h3>
        <div class="card-content">
            {content}
        </div>
        <div class="button-row">
            <button onclick="{copy_fn}()" class="copy-btn">Copy</button>
            <button onclick="{download_fn}()" class="download-btn">Download</button>
        </div>
    </div>
    """
    return js_code

def render_impairments_card(details, with_apportionment=False):
    content = "NO APPORTIONMENT     100%" if not with_apportionment else "WITH APPORTIONMENT 90% and 80% CS LS"
    content += "\n\n"
    
    for detail in details:
        content += (
            f"({detail['impairment_code']} - {detail['original_wpi']} - [1.4] "
            f"{round(detail['adjusted_wpi'])} - {detail['group_number']}{detail['variant'].upper()} - "
            f"{round(detail['occupant_adjusted_wpi'])} - {round(detail['age_adjusted_wpi'])}%) "
            f"{round(detail['age_adjusted_wpi'])}%\n"
            f"{detail['body_part']}\n"
        )
    
    return content

def render_combinations_card(upper_extremities, lower_extremities, spine, other, result):
    from utils.calculations import combine_wpi_values
    content = "\n"
    
    # Display mastication ratings first if present
    mastication_ratings = [d for d in other if any(term in d['body_part'].lower() for term in ['mastication', 'jaw', 'dental', 'teeth', 'tmj', 'temporomandibular'])]
    if mastication_ratings:
        content += "Mastication/Dental Ratings:\n"
        for m in mastication_ratings:
            content += f"{round(m['age_adjusted_wpi'])}%\n"
        content += "\n"
    
    # All ratings combination
    all_ratings = []
    if upper_extremities:
        all_ratings.extend([str(round(d['age_adjusted_wpi'])) for d in upper_extremities])
    if lower_extremities:
        all_ratings.extend([str(round(d['age_adjusted_wpi'])) for d in lower_extremities])
    for s in spine:
        all_ratings.append(str(round(s['age_adjusted_wpi'])))
    for o in other:
        all_ratings.append(str(round(o['age_adjusted_wpi'])))
    
    content += f"{' C '.join(all_ratings)} = {round(result['final_pd_percent'])}%\n"
    content += f"Combined Rating {round(result['final_pd_percent'])}%\n"
    content += f"Total of All Add-ons for Pain 2%\n"
    content += f"Total Weeks of PD{round(result['weeks'], 2)}\n"
    content += f"Age on DOI {result.get('age', 'N/A')}\n"
    content += f"Average Weekly Earnings${result.get('weekly_earnings', '435.00')} (PD Statutory Max)\n"
    content += f"PD Weekly Rate:${result.get('weekly_rate', '290.00')}\n"
    content += f"Total PD Payout${round(result['total_pd_dollars'], 2)}\n"
    content += "Return to Work Adjustments\n\n"
    content += "No RTW Adjustments for injuries on/after 1/1/2013.\n"
    content += f"Average Weekly Earnings ${result.get('life_pension_max', '515.38')} (Life Pension Statutory Max)\n"
    content += f"Life Pension Weekly Rate ${result.get('life_pension_rate', '85.0')}\n\n"
    
    # Add CMS Analysis
    content += f"CMS Analysis ${round(result['total_pd_dollars'] * 0.4, 2)}\n"
    content += f"I would propose a split between {round(result['final_pd_percent'])}% and {round(result['final_pd_percent'] * 0.9)}%\n\n"
    
    # Add final calculations
    cms_amount = round(result['total_pd_dollars'] * 0.4, 2)
    lp_amount = round(result['total_pd_dollars'] * 0.2, 2)
    total_demand = cms_amount + lp_amount
    
    content += f"CMS     =     ${cms_amount}\n"
    content += f"LP      =     ${lp_amount}\n\n"
    content += f"Demand =     ${total_demand}  With a Voucher.\n"
    content += "(Also may change based on Benefits print out.)"
    
    return content

def render_detailed_summary_card(detailed_summary):
    detailed_content = (
        f"<h4>Medical History</h4>{detailed_summary['medical_history']}<br><br>"
        f"<h4>Injury Mechanism</h4>{detailed_summary['injury_mechanism']}<br><br>"
        f"<h4>Treatment History</h4>{detailed_summary['treatment_history']}<br><br>"
        f"<h4>Work Restrictions</h4>{detailed_summary['work_restrictions']}<br><br>"
        f"<h4>Future Medical Needs</h4>{detailed_summary['future_medical']}<br><br>"
        f"<h4>Apportionment</h4>{detailed_summary['apportionment']}"
    )
    if detailed_summary['additional_findings']:
        detailed_content += f"<br><br><h4>Additional Findings</h4>{detailed_summary['additional_findings']}"
    
    return render_styled_card(
        "Detailed Analysis",
        detailed_content,
        "detailed_summary"
    )

def render_final_calculations_card(result):
    content = ""
    # This function is now handled within render_combinations_card
    return content
