import { useEffect, useState } from 'react';
import { api } from './api';
import BatchScreening from './BatchScreening';

export default function OCRUpload({onApply, disabled = false, rules = [], user = null}) {
  const [allPages, setAllPages] = useState(true);
  const [admissionType, setAdmissionType] = useState('ND Full-Time');
  const availableRules = rules.filter(rule => (rule.admission_type || 'ND Full-Time') === admissionType || (['All Admission Type', 'ND Full-Time'].includes(rule.admission_type || 'ND Full-Time') && !rules.some(other => other.admission_type === admissionType && other.programme === rule.programme)));
  const [smartProcessing, setSmartProcessing] = useState(false);
  const [automatic, setAutomatic] = useState(true);
  const [progress, setProgress] = useState('');
  const [complete, setComplete] = useState(false);
  const [runId, setRunId] = useState(0);
  const [file, setFile] = useState(null);
  const isTable = /\.(csv|xlsx|xls)$/i.test(file?.name || '');
  const [page, setPage] = useState(1);
  const [mode, setMode] = useState('complete');
  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [replace, setReplace] = useState(false);
  const [available, setAvailable] = useState(null);
  useEffect(() => { api('ocr').then(data => setAvailable(data.available)).catch(() => {}); }, []);
  async function extract(event) {
    event.preventDefault(); setError(''); setNotice(''); setResult(null); setReplace(false); setBusy(true); setComplete(false); setRunId(id => id + 1);
    try {
      if (!file) throw new Error('Choose a result document first.');
      if (file.size > 10 * 1024 * 1024) throw new Error('Choose a document smaller than 10 MB.');
      const pages = [];
      let nextPage = allPages ? 1 : Number(page), lastPage = nextPage;
      do {
        setProgress(`Reading page ${nextPage}${pages.length ? ` of ${lastPage}` : ''}...`);
        const body = new FormData(); body.append('file', file); body.append('page', String(nextPage));
        body.append('admission_type', admissionType);
        body.append('smart_processing', String(smartProcessing));
        const data = await api('ocr', {method: 'POST', body});
        pages.push(data);
        if (allPages) lastPage = data.page_count;
        setResult({...pages[0], pages: [...pages], drafts: pages.flatMap(p => p.drafts.map(d => ({...d, page: p.page}))), text: pages.map(p => `PAGE ${p.page}\n${p.text}`).join('\n\n')});
        setSelected(0); if (!isTable) setAvailable(true);
        nextPage += 1;
      } while (nextPage <= lastPage);
      setComplete(true);
      setProgress(`Finished ${pages.length} page(s).`);
    } catch (e) { setError(isTable ? e.message : `${e.message} Any completed pages remain available below; the whole document has not finished processing.`); }
    finally { setBusy(false); }
  }
  const draft = result?.drafts[selected];
  const previewPage = result?.pages?.find(p => p.page === draft?.page) || result;
  const canApply = admissionType === 'ND Full-Time' && draft && (mode === 'complete' || (mode === 'olevel' ? draft.sittings.length > 0 : draft.jamb_score !== null));
  return <section className="card ocr-card" aria-labelledby="ocr-title">
    <div className="card-heading"><div className="step">↑</div><div><h2 id="ocr-title">Import a result document</h2><p>Upload a form, result slip or register. Extract all pages and screen students against their programme requirements.</p></div></div>
    {available === false && <div className="note">The OCR engine is not configured. Install Tesseract and restart Django; manual entry remains available.</div>}
    <form onSubmit={extract}><fieldset disabled={busy || disabled} className="form-fieldset">
      <div className="ocr-controls">
        <label className="field"><span>Admission type</span><select value={admissionType} onChange={e => {setAdmissionType(e.target.value); setResult(null); setComplete(false); setProgress(''); setRunId(id => id + 1);}}>{['ND Full-Time','ND Part-Time','HND Full-Time','HND Part-Time'].map(type => <option key={type}>{type}</option>)}</select></label>
        <label className="field"><span>Result document</span><input type="file" accept=".png,.jpg,.jpeg,.pdf,.csv,.xlsx,image/png,image/jpeg,application/pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={e => {setComplete(false); setProgress(''); setFile(e.target.files[0] || null); setResult(null); setPage(1); setError(''); setNotice(''); setReplace(false);}}/></label>
        <label className="field" hidden={allPages}><span>PDF page</span><input type="number" min="1" max={result?.page_count || 10} value={page} disabled={!file?.name.toLowerCase().endsWith('.pdf')} onChange={e => {setPage(e.target.value); setResult(null); setReplace(false);}}/></label>
        <button className="button" disabled={!file}>{busy ? 'Reading document…' : isTable ? 'Import records' : 'Extract text'}</button>
      </div>
    <label className="checkbox"><input type="checkbox" checked={allPages} onChange={e => {setAllPages(e.target.checked); setResult(null); setComplete(false);}}/>Extract every page automatically</label>
      <label className="checkbox"><input type="checkbox" checked={smartProcessing} onChange={e => {setSmartProcessing(e.target.checked); setResult(null); setComplete(false); setNotice(''); setRunId(id => id + 1);}}/>Smart processing: tolerate minor name typos and note them in the comments</label>
      <label className="checkbox"><input type="checkbox" checked={automatic} onChange={e => setAutomatic(e.target.checked)}/>Automatically screen students when extraction finishes</label>
    </fieldset></form>
    <p className="muted">PNG, JPG/JPEG, PDF, CSV or Excel (.xlsx) · up to 10 MB and 10 PDF pages · All pages are processed in order, with progress shown below.</p>
    <p className="muted">Spreadsheets: {admissionType === 'ND Full-Time' ? '21' : admissionType === 'ND Part-Time' ? '15' : '19'} columns, one row per student. Up to 10,000 students. Upload a merged register or an XLSX with school and JAMB portal sheets; matching uses JAMB registration numbers. <a href={admissionType === 'ND Full-Time' ? '/templates/mapoly-student-register-sample.xlsx' : admissionType === 'ND Part-Time' ? '/templates/nd-part-time-register.xlsx' : '/templates/hnd-register.xlsx'} download>Download Excel template</a>.</p>
    {admissionType !== 'ND Full-Time' && <p className="note">Use the spreadsheet layout for this route. Screening uses the programme O?level baseline without UTME checks. HND also checks ND grade/CGPA; IT and accreditation are excluded. Correct entries in the workbook and re-import.</p>}
    {!availableRules.length && <p className="note">No admission rules are configured for {admissionType}. You can extract records, but screening remains pending until rules are added for this admission type.</p>}
    {progress && <div className="extraction-progress" role="status">{busy && <span className="working-dot"/>}{progress}</div>}
    {error && <div className="error" role="alert">{error}</div>}
    {notice && <div className="success" role="status">{notice}</div>}
    {complete && result?.drafts.length > 0 && <BatchScreening key={runId} pages={result.pages} rules={availableRules} admissionType={admissionType} user={user} onReview={onApply} automatic={automatic}/> }
    {result && <div className="ocr-review">
      <div>{previewPage.table ? <><h3>Spreadsheet preview</h3>{previewPage.merge_report && <div className="note"><strong>Portal merge: {previewPage.merge_report.matched} matched candidates</strong><p>{previewPage.merge_report.school_rows} school rows; {previewPage.merge_report.jamb_rows} JAMB rows. {previewPage.merge_report.excluded_school_rows.length} school rows excluded; {previewPage.merge_report.unused_jamb_rows} JAMB rows unused. School order and serial numbers are preserved.</p><details><summary>Excluded school rows</summary>{previewPage.merge_report.excluded_school_rows.map((row,i)=><p key={i}>S/N {row.serial || row.sheet_row}: {row.registration_number || 'No registration'}: {row.reason}</p>)}</details></div>}<p>Showing the first {previewPage.table.rows.length} of {previewPage.table.count} rows.</p><div className="table-preview" tabIndex="0" role="region" aria-label="Imported spreadsheet"><table><thead><tr>{previewPage.table.headers.map(header => <th key={header}>{header}</th>)}</tr></thead><tbody>{previewPage.table.rows.map((row, index) => <tr key={index}>{row.map((value, cell) => <td key={cell}>{value}</td>)}</tr>)}</tbody></table></div></> : <><a href={previewPage.preview} target="_blank" rel="noreferrer" aria-label="Open document preview"><img className="ocr-preview" src={previewPage.preview} alt={`Uploaded document, page ${previewPage.page} of ${result.page_count}`}/></a><p className="muted">Page {previewPage.page} of {result.page_count}</p></>}</div>
      <div>
        <h3>Review the extraction</h3>{previewPage.table ? <p className="note">Values imported directly from the spreadsheet.</p> : <p className="confidence-score">Recognition score: {draft?.confidence ?? previewPage.confidence ?? 0} / 100 <small>Not a probability of correctness</small></p>}
        {result.warnings.map((warning, i) => <p className="note" key={i}>{warning}</p>)}
        {previewPage.low_confidence_words.length > 0 && <details><summary>Words to double-check ({previewPage.low_confidence_words.length})</summary><p>{previewPage.low_confidence_words.slice(0, 80).join(', ')}</p></details>}
        {result.drafts.length > 0 ? <>
          <label className="field"><span>Student draft</span><select value={selected} onChange={e => {setSelected(Number(e.target.value)); setReplace(false);}}>{result.drafts.map((draft, i) => <option key={i} value={i}>{i + 1}. {draft.student_name || 'Name not detected'} {draft.registration_number && `· ${draft.registration_number}`}</option>)}</select></label>
          <dl className="ocr-summary"><dt>Name</dt><dd>{draft.student_name || 'Not detected'}</dd><dt>Registration</dt><dd>{draft.registration_number || 'Not detected'}</dd><dt>Course on document</dt><dd>{draft.course || 'Not detected'}</dd><dt>JAMB score</dt><dd>{draft.jamb_score ?? 'Not detected / awaiting'}</dd><dt>O’level results</dt><dd>{draft.sittings.length} sitting(s), {draft.sittings.reduce((n, sitting) => n + sitting.subjects.length, 0)} subject entries</dd></dl>
          <label className="field"><span>Load into the form</span><select value={mode} onChange={e => {setMode(e.target.value); setReplace(false);}}><option value="complete">Complete student draft</option><option value="olevel">O’level results only</option><option value="jamb">JAMB score only</option></select></label>
          <label className="checkbox"><input type="checkbox" checked={replace} onChange={e => setReplace(e.target.checked)}/>Replace the corresponding current form entries with this draft. I will review and correct them before screening.</label>
          <button type="button" className="button secondary" disabled={!replace || !canApply || busy || disabled} onClick={() => {onApply(draft, mode); setNotice('Draft loaded below. Choose the programme, correct any missing fields, and confirm the results before screening.'); setReplace(false);}}>Load draft for review ↓</button>
        </> : <p>No student draft could be separated reliably. You can still use the extracted text below for manual entry.</p>}
        <details className="ocr-raw"><summary>Show extracted text / first 100 spreadsheet rows</summary><textarea aria-label="Extracted document text" readOnly value={result.text}/></details>
      </div>
    </div>}
  </section>;
}
