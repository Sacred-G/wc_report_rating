import re
import unicodedata

def clean_latex_expression(latex_text):
    """
    Clean and sanitize LaTeX expressions for proper rendering in Streamlit.
    
    This function:
    1. Normalizes Unicode characters
    2. Escapes special LaTeX characters
    3. Handles common Unicode math symbols that cause rendering issues
    
    Args:
        latex_text (str): The LaTeX text to clean
        
    Returns:
        str: Cleaned LaTeX text ready for rendering
    """
    if not latex_text:
        return latex_text
    
    # Normalize Unicode characters
    latex_text = unicodedata.normalize('NFKD', latex_text)
    
    # Replace problematic Unicode math symbols with LaTeX equivalents
    replacements = {
        '±': r'\pm',
        '×': r'\times',
        '÷': r'\div',
        '≤': r'\leq',
        '≥': r'\geq',
        '≠': r'\neq',
        '≈': r'\approx',
        '∑': r'\sum',
        '∏': r'\prod',
        '∫': r'\int',
        '∞': r'\infty',
        '√': r'\sqrt',
        '∂': r'\partial',
        '∆': r'\Delta',
        '∇': r'\nabla',
        '∈': r'\in',
        '∉': r'\notin',
        '∋': r'\ni',
        '∩': r'\cap',
        '∪': r'\cup',
        '⊂': r'\subset',
        '⊃': r'\supset',
        '⊆': r'\subseteq',
        '⊇': r'\supseteq',
        '⊕': r'\oplus',
        '⊗': r'\otimes',
        '⊥': r'\perp',
        '⋅': r'\cdot',
        '⌈': r'\lceil',
        '⌉': r'\rceil',
        '⌊': r'\lfloor',
        '⌋': r'\rfloor',
        '〈': r'\langle',
        '〉': r'\rangle',
        '→': r'\rightarrow',
        '←': r'\leftarrow',
        '↔': r'\leftrightarrow',
        '↑': r'\uparrow',
        '↓': r'\downarrow',
        '↕': r'\updownarrow',
        '°': r'^{\circ}',
    }
    
    for unicode_char, latex_cmd in replacements.items():
        latex_text = latex_text.replace(unicode_char, latex_cmd)
    
    # Escape special LaTeX characters that aren't part of commands
    special_chars = ['%', '$', '&', '#', '_', '{', '}']
    for char in special_chars:
        # Only escape if not preceded by backslash
        latex_text = re.sub(r'(?<!\\)' + re.escape(char), r'\\' + char, latex_text)
    
    # Fix common LaTeX command issues
    # Ensure proper spacing after commands
    latex_text = re.sub(r'(\\[a-zA-Z]+)([a-zA-Z])', r'\1 \2', latex_text)
    
    return latex_text

def render_latex(latex_text):
    """
    Prepare LaTeX text for rendering in Streamlit by cleaning and wrapping it.
    
    Args:
        latex_text (str): The LaTeX text to render
        
    Returns:
        str: Markdown string ready for st.markdown()
    """
    if not latex_text:
        return latex_text
    
    # Clean the LaTeX expression
    cleaned_latex = clean_latex_expression(latex_text)
    
    # Wrap in LaTeX delimiters if not already wrapped
    if not cleaned_latex.startswith('$') and not cleaned_latex.startswith('\\('):
        # Inline math mode
        cleaned_latex = f"${cleaned_latex}$"
    
    return cleaned_latex
