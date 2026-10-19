export function programmeKey(value) {
  let text=String(value || '').toLowerCase().replace(/[&/]/g,' and ').replace(/[^a-z0-9 ]/g,' ')
    .replace(/\b(higher national diploma|national diploma|full time|part time|fulltime|parttime|nd|hnd)\b/g,' ')
    .trim().replace(/\s+/g,' ').replace(/\bengineering technology\b/g,'engineering');
  const aliases={
    'accounting':'accountancy',
    'business administration':'business administration and management',
    'electrical electronics engineering':'electrical and electronics engineering',
    'electrical engineering':'electrical and electronics engineering',
    'estate management':'estate management and valuation',
    'surveying and geoinformatics':'surveying and geo informatics',
    'library and information sciences':'library and information science',
  };
  return aliases[text] || text;
}
