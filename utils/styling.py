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
        white-space: pre-wrap;
        font-family: monospace;
    }
    .mastication-rating {
        color: #2c3e50;
        font-weight: bold;
        margin: 5px 0;
        padding: 5px;
        border-left: 3px solid #1f77b4;
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
    content = []
    content.append("NO APPORTIONMENT     100%" if not with_apportionment else "WITH APPORTIONMENT 90% and 80% CS LS")
    content.append("")
    
    for detail in details:
        content.append(detail['body_part'])
        content.append(detail['formatted_string'])
        content.append("")  # Add blank line between impairments
    
    return "\n".join(content)

def render_combinations_card(upper_extremities, lower_extremities, spine, other, result):
    from utils.calculations import combine_wpi_values
    content = []
    
    # Get the appropriate result section (no_apportionment or with_apportionment)
    rating_section = result.get('no_apportionment', {}) if 'no_apportionment' in result else result
    
    # Display mastication ratings first if present
    mastication_ratings = [d for d in other if any(term in d['body_part'].lower() for term in ['mastication', 'jaw', 'dental', 'teeth', 'tmj', 'temporomandibular'])]
    if mastication_ratings:
        content.append("<div class='mastication-rating'>")
        content.append("Mastication/Dental Ratings:")
        for m in mastication_ratings:
            content.append(f"• {m['body_part']}: {round(m['wpi'])}%")
        content.append("</div>")
        content.append("")
    
    # All ratings combination
    all_ratings = []
    if upper_extremities:
        all_ratings.extend([str(round(d['wpi'])) for d in upper_extremities])
    if lower_extremities:
        all_ratings.extend([str(round(d['wpi'])) for d in lower_extremities])
    for s in spine:
        all_ratings.append(str(round(s['wpi'])))
    for o in other:
        all_ratings.append(str(round(o['wpi'])))
    
    content.append(f"{' C '.join(all_ratings)} = {round(rating_section.get('final_pd_percent', 0))}%")
    content.append("")
    content.append(f"Combined Rating {round(rating_section.get('final_pd_percent', 0))}%")
    content.append(f"Total of All Add-ons for Pain 2%")
    content.append(f"Total Weeks of PD {round(rating_section.get('weeks', 0), 2)}")
    content.append(f"Age on DOI {result.get('age', 'N/A')}")
    content.append(f"Average Weekly Earnings ${rating_section.get('pd_weekly_rate', '435.00')} (PD Statutory Max)")
    content.append(f"PD Weekly Rate: ${rating_section.get('pd_weekly_rate', '290.00')}")
    content.append(f"Total PD Payout ${round(rating_section.get('total_pd_dollars', 0), 2)}")
    
    # Add life pension info if available
    if rating_section.get('life_pension_weekly_rate'):
        content.append("")
        content.append("Return to Work Adjustments")
        content.append("")
        content.append("No RTW Adjustments for injuries on/after 1/1/2013.")
        content.append(f"Average Weekly Earnings ${rating_section.get('life_pension_max_earnings', '515.38')} (Life Pension Statutory Max)")
        content.append(f"Life Pension Weekly Rate ${rating_section.get('life_pension_weekly_rate', '85.0')}")
        content.append("")
    
    # Add CMS Analysis if this is the no_apportionment section
    if 'no_apportionment' in result:
        total_pd = rating_section.get('total_pd_dollars', 0)
        cms_amount = round(total_pd * 0.4, 2)
        lp_amount = round(total_pd * 0.2, 2)
        total_demand = cms_amount + lp_amount
        
        content.append(f"CMS Analysis ${cms_amount}")
        content.append(f"I would propose a split between {round(rating_section.get('final_pd_percent', 0))}% and {round(rating_section.get('final_pd_percent', 0) * 0.9)}%")
        content.append("")
        content.append(f"CMS     =     ${cms_amount}")
        content.append(f"LP      =     ${lp_amount}")
        content.append("")
        content.append(f"Demand =     ${total_demand}  With a Voucher.")
        content.append("(Also may change based on Benefits print out.)")
    
    return "\n".join(content)

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
    rating_section = result.get('no_apportionment', {})
    content = f"Combined Rating: {round(rating_section.get('final_pd_percent', 0))}%\n"
    content += f"Total Weeks of PD: {round(rating_section.get('weeks', 0), 2)}\n"
    content += f"Age on DOI: {result.get('age', 'N/A')}\n"
    content += f"PD Weekly Rate: ${rating_section.get('pd_weekly_rate', 290.00)}\n"
    content += f"Total PD Payout: ${round(rating_section.get('total_pd_dollars', 0), 2)}\n"
    
    # Add mastication ratings if present
    mastication_ratings = [d for d in rating_section.get('formatted_impairments', [])
                         if any(term in d['body_part'].lower() 
                               for term in ['mastication', 'jaw', 'dental', 'teeth', 'tmj', 'temporomandibular'])]
    if mastication_ratings:
        content += "\n<div class='mastication-rating'>\n"
        content += "Mastication/Dental Ratings:\n"
        for m in mastication_ratings:
            content += f"• {m['body_part']}: {round(m['wpi'])}%\n"
        content += "</div>"
    
    return render_styled_card(
        "Final Calculations",
        content,
        "final_calcs"
    )
