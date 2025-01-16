import streamlit as st

def get_card_css():
    return """
    <style>
    .card {
        background: white;
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

def render_impairments_card(details):
    impairments_content = ""
    for detail in details:
        impairment_str = (
            f"({detail['impairment_code']} - {detail['original_wpi']} - [1.4] "
            f"{round(detail['adjusted_wpi'], 2)} - {detail['group_number']}{detail['variant'].upper()} - "
            f"{round(detail['occupant_adjusted_wpi'], 2)} - {round(detail['age_adjusted_wpi'], 2)}%) "
            f"{round(detail['age_adjusted_wpi'], 2)}% {detail['body_part']}<br>"
        )
        impairments_content += impairment_str
    
    return render_styled_card(
        "Impairments", 
        impairments_content,
        "impairments"
    )

def render_combinations_card(upper_extremities, lower_extremities, spine, other, result):
    from utils.calculations import combine_wpi_values
    combination_content = ""
    
    # Combine upper extremities first if present
    if len(upper_extremities) > 1:
        ue_ratings = [str(round(d['age_adjusted_wpi'])) for d in upper_extremities]
        combination_content += f"{' C '.join(ue_ratings)} = {round(combine_wpi_values([d['age_adjusted_wpi'] for d in upper_extremities]))}%<br>"
    
    # Combine lower extremities if present
    if len(lower_extremities) > 1:
        le_ratings = [str(round(d['age_adjusted_wpi'])) for d in lower_extremities]
        combination_content += f"{' C '.join(le_ratings)} = {round(combine_wpi_values([d['age_adjusted_wpi'] for d in lower_extremities]))}%<br>"
    
    # Final combination of all regions
    all_ratings = []
    if upper_extremities:
        all_ratings.append(str(round(combine_wpi_values([d['age_adjusted_wpi'] for d in upper_extremities]))))
    if lower_extremities:
        all_ratings.append(str(round(combine_wpi_values([d['age_adjusted_wpi'] for d in lower_extremities]))))
    for s in spine:
        all_ratings.append(str(round(s['age_adjusted_wpi'])))
    for o in other:
        all_ratings.append(str(round(o['age_adjusted_wpi'])))
    
    combination_content += f"{' C '.join(all_ratings)} = {round(result['final_pd_percent'])}%"
    
    return render_styled_card(
        "Combination Steps",
        combination_content,
        "combinations"
    )

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
    final_calc_content = (
        f"Combined Rating: {round(result['final_pd_percent'])}%<br>"
        f"Total of All Add-ons for Pain: {result.get('pain_addon', 0)}%<br>"
        f"Total Weeks of PD: {round(result['weeks'], 2)}<br>"
        f"Age on DOI: {result.get('age', 'N/A')}<br>"
        f"PD Weekly Rate: $290.00<br>"
        f"Total PD Payout: ${round(result['total_pd_dollars'], 2)}"
    )
    return render_styled_card(
        "Final Calculations",
        final_calc_content,
        "final_calcs"
    )
