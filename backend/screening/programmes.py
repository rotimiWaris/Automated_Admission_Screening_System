"""Conservative programme aliases; never use substring or fuzzy department matching."""
import re


def programme_key(value):
    text = str(value or '').lower().replace('&',' and ').replace('/',' and ')
    text = re.sub(r'[^a-z0-9 ]',' ',text)
    text = re.sub(r'\b(?:higher national diploma|national diploma|full time|part time|fulltime|parttime|nd|hnd)\b',' ',text)
    text = ' '.join(text.split())
    text = re.sub(r'\bengineering technology\b','engineering',text)
    aliases = {
        'accounting':'accountancy',
        'business administration':'business administration and management',
        'electrical electronics engineering':'electrical and electronics engineering',
        'electrical engineering':'electrical and electronics engineering',
        'estate management':'estate management and valuation',
        'surveying and geoinformatics':'surveying and geo informatics',
        'library and information sciences':'library and information science',
    }
    return aliases.get(text,text)
