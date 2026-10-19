import {useEffect, useRef, useState} from 'react';
import {api} from './api';

import {programmeKey as normalise} from './programmes';

export default function BatchScreening({pages, rules, user, onReview, automatic = true, admissionType = 'ND Full-Time'}) {
  const drafts = pages.flatMap(page => page.drafts.map(draft => ({...draft, page: page.page})));
  const courses = [...new Set(drafts.map(draft => draft.course))];
  const [mapping, setMapping] = useState(() => Object.fromEntries(courses.map(course => {
    const matches = rules.filter(rule => normalise(rule.programme) === normalise(course));
    return [course, matches.length === 1 ? String(matches[0].id) : ''];
  })));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [batch, setBatch] = useState(null);
  const [resultPage, setResultPage] = useState(0);
  const [save, setSave] = useState(Boolean(user));
  const automaticStarted = useRef(false);
  const inFlight = useRef(false);
  function downloadExcel(report) {
    if (!report) return;
    const bytes = Uint8Array.from(atob(report.base64), c => c.charCodeAt(0));
    const url = URL.createObjectURL(new Blob([bytes], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}));
    const link = document.createElement('a'); link.href = url; link.download = report.filename; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function screenBatch() {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true); setError(''); setBatch(null);
    try {
      const course_rules = Object.fromEntries(courses.map(course => {
        const rule = rules.find(rule => String(rule.id) === mapping[course]);
        return [course, rule ? {id: rule.id, revision: rule.revision} : null];
      }));
      const response = await api('screen-batch', {method: 'POST', body: {pages: pages.map(page => page.token), course_rules, admission_type: admissionType, save: Boolean(user && save)}});
      setBatch(response); setResultPage(0);
      downloadExcel(response.excel);
    } catch (e) { setError(e.message); }
    finally { inFlight.current = false; setBusy(false); }
  }
  useEffect(() => {
    if (automatic && drafts.length && !automaticStarted.current) {
      automaticStarted.current = true;
      screenBatch();
    }
  }, []);
  useEffect(() => { setBatch(null); }, [rules, user]);
  if (!drafts.length) return null;
  return <section className="batch-section" aria-label="Batch screening">
    <div className="section-title"><div><div className="eyebrow">DOCUMENT RESULTS</div><h3>Screen every extracted student</h3><p>{drafts.length} students across {pages.length} processed page(s). Results use the configured admission rules.</p></div></div>
    <details open={courses.some(course => !mapping[course])}><summary>Programme matching</summary><p>Programme names and recognised naming variants are matched automatically. For other names, choose the rules once per course; no result retyping is needed.</p>
      <div className="course-mappings">{courses.map(course => <label className="field" key={course}><span>{course || 'Course not detected'}</span><select disabled={busy} value={mapping[course]} onChange={e => {setMapping({...mapping, [course]: e.target.value}); setBatch(null);}}><option value="">Choose admission rules</option>{rules.map(rule => <option key={rule.id} value={rule.id}>{rule.programme} · {rule.academic_session}</option>)}</select></label>)}</div>
    </details>
    <label className="checkbox"><input type="checkbox" disabled={!user || busy} checked={Boolean(user && save)} onChange={e => {setSave(e.target.checked); setBatch(null);}}/>Save evaluated students to my history{!user && ' (sign in to enable)'}</label>
    <button type="button" className="button" disabled={busy || Boolean(batch && save)} onClick={screenBatch}>{busy ? 'Screening students…' : 'Screen all students'}</button>
    {busy && <p role="status">Comparing each student with their programme requirements…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {batch && <>
        {batch.export_notice && <p role="status">{batch.export_notice}</p>}
      {batch.excel && <button type="button" className="button secondary" onClick={() => downloadExcel(batch.excel)}>Download Excel results</button>}
      <div className="batch-stats">{['Eligible', 'Not Eligible', 'Pending Review'].map(status => <div key={status}><strong>{batch.summary[status] || 0}</strong><span>{status}</span></div>)}</div>
      {batch.results.length > 50 && <div className="history-pagination"><button type="button" className="button secondary" disabled={resultPage===0} onClick={()=>setResultPage(p=>p-1)}>Previous results</button><span>Page {resultPage+1} of {Math.ceil(batch.results.length/50)}</span><button type="button" className="button secondary" disabled={(resultPage+1)*50>=batch.results.length} onClick={()=>setResultPage(p=>p+1)}>Next results</button></div>}
      <div className="batch-list">{batch.results.slice(resultPage * 50, (resultPage + 1) * 50).map((item, index) => <article className="batch-student" key={index}>
        <div className="result-heading"><div><h3>{item.student_name || 'Unnamed student'}</h3><p>{item.registration_number || 'Registration missing'} · Page {item.page}<br/>{item.course || 'Course missing'}</p></div><span className={`result-badge ${item.status === 'Eligible' ? 'passed' : item.status === 'Not Eligible' ? 'failed' : 'pending'}`}>{item.status}</span></div>
        {item.storage_notice && <p className="note">{item.storage_notice} This is a fresh assessment using the uploaded results.</p>}
        {item.issues.map((issue, i) => <p className="note" key={i}>{issue}</p>)}
        {item.applicant && <p>Age: {item.applicant.age ?? 'Unavailable'} {item.applicant.age_source && `(${item.applicant.age_source})`}</p>}
        {item.applicant?.warnings?.map((warning, i) => <p className="note" key={i}>{warning}</p>)}
        {item.result?.remark && <p><strong>Remark: {item.result.remark}</strong>{item.original_remark && <> · Previous: {item.original_remark} · {item.result.remark_check.mark} {item.result.remark_check.detail}</>}</p>}
        {item.result && <details><summary>View requirement checks</summary>{item.result.checks.map((check, i) => <div className="check" key={i}><span className={`check-icon ${check.status}`}>{check.status === 'passed' ? '✓' : check.status === 'failed' ? '×' : '!'}</span><div><strong>{check.label}</strong><p>{check.detail}</p></div></div>)}{item.result.id && <p>Saved as screening #{item.result.id}.</p>}</details>}
        {admissionType === 'ND Full-Time' ? <button type="button" className="text-button" onClick={() => onReview(drafts[resultPage * 50 + index], 'complete')}>Open student for corrections →</button> : <p className="muted">Correct this student in the source workbook and re-import to reassess.</p>}
      </article>)}</div>
    </>}
  </section>;
}
