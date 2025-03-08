# AI-Enhanced Impairment Extraction  
  
## Overview  
  
The PDF Calculator now includes three processing options:  
  
1. **No AI (Fast)** - Uses only regex-based extraction  
2. **Enhanced Extraction (Balanced)** - Uses both regex and AI  
3. **Full AI Processing (Slow)** - Uses the complete AI pipeline 
  
## Implementation  
  
- `utils/ai_extractor.py` - AI-based extraction functionality  
- `testing/test_ai_extractor.py` - Unit tests  
- `pages/PDF_Calculator.py` - Updated UI integration  
  
## How It Works  
  
The Enhanced Extraction option:  
1. Uses regex patterns to quickly extract impairments  
2. Uses AI to extract additional impairments  
3. Merges results, with AI results taking precedence  
4. Processes impairments locally 
  
## Usage  
  
1. Upload a PDF to the PDF Calculator  
2. Select an AI processing option  
3. Click "Process with AI"  
4. The extracted impairments will be imported into the calculator  
  
## Benefits  
  
- Improved accuracy over regex-only extraction  
- Better performance than full AI processing  
- Fallback to regex if AI extraction fails 
