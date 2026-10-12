import { useEffect, useRef, useState } from 'react';
import { api } from './api';
import OCRUpload from './OCRUpload';
import History from './History';
import CriteriaDetails, { CriteriaEditor } from './CriteriaDetails';
import NavigationIcon from './NavigationIcon';

const makeRow = () => ({subject: '', grade: ''});
const makeSitting = () => ({board: 'WAEC', exam_type: 'School', year: new Date().getFullYear(), subjects: [makeRow()]});
const newRules = () => ({programme: '', academic_session: 'All sessions', admission_type: 'All Admission Type', source: '', criteria: {}, minimum_jamb: 100, minimum_credits: 5, max_sittings: 2, allow_combining: true, active: true, required_subjects: [{subject: 'English Language', minimum_grade: 'C6'}, {subject: 'Mathematics', minimum_grade: 'C6'}]});

function Field({label, children, ...props}) {
  return <label className="field" {...props}><span>{label}</span>{children}</label>;
}
function Options({values}) { return values.map(value => <option key={value} value={value}>{value}</option>); }
function ErrorBox({message}) { return message ? <div className="error" role="alert">{message}</div> : null; }

export default function App() {
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('mapoly.sidebar.collapsed') === 'true'; }
    catch { return false; }
  });
  useEffect(() => {
    try { localStorage.setItem('mapoly.sidebar.collapsed', String(collapsed)); }
    catch { /* Navigation still works when browser storage is unavailable. */ }
  }, [collapsed]);
  const [tab, setTab] = useState('screen');
  const [user, setUser] = useState(null);
  const [rules, setRules] = useState([]);
  const [catalogue, setCatalogue] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [authOpen, setAuthOpen] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState('');

  async function load() {
    setError(''); setLoading(true);
    try {
      const session = await api('session');
      if (!session.user) { setUser(null); setCatalogue(null); setRules([]); return; }
      const [catalogue, response] = await Promise.all([api('catalogue'), api('rules')]);
      setUser(session.user); setCatalogue(catalogue); setRules(response.rules);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);
  useEffect(() => {
    function expired() { setUser(null); setRules([]); setCatalogue(null); setTab('screen'); setLoading(false); setAuthError('Your session ended. Please sign in again.'); }
    window.addEventListener('session-expired', expired);
    return () => window.removeEventListener('session-expired', expired);
  }, []);
  async function refreshRules() { const data = await api('rules'); setRules(data.rules); }
  async function login(event) {
    event.preventDefault(); setAuthBusy(true); setAuthError('');
    const form = new FormData(event.currentTarget);
    try {
      const data = await api('login', {method: 'POST', body: Object.fromEntries(form)});
      setAuthOpen(false); await load();
    } catch (e) { setAuthError(e.message); }
    finally { setAuthBusy(false); }
  }
  async function logout() {
    setAuthBusy(true);
    try { await api('logout', {method: 'POST'}); setUser(null); setRules([]); setCatalogue(null); setTab('screen'); }
    catch (e) { setError(e.message); }
    finally { setAuthBusy(false); }
  }
  const accountAction = user ? logout : () => { setAuthError(''); setAuthOpen(true); };
  if (!user) return <main className="login-page">
    <section className="login-panel" aria-labelledby="login-heading">
      <div className="login-brand"><img src="/mapoly-logo.png" alt="MAPOLY crest" width="64" height="72"/><div><strong>Moshood Abiola Polytechnic</strong><span>Admissions administration</span></div></div>
      <div className="login-intro"><span className="login-eyebrow">STAFF PORTAL</span><h1 id="login-heading">Welcome back</h1><p>Sign in to your screening workspace.</p></div>
      {loading ? <div className="session-loader" role="status" aria-live="polite"><span className="session-spinner" aria-hidden="true"/><div><strong>Opening your workspace</strong><span>Verifying your sign-in securely</span></div></div> : <form onSubmit={login}>
        <Field label="Username"><input name="username" autoComplete="username" placeholder="Enter your username" autoCapitalize="none" spellCheck={false} required/></Field>
        <div className="field"><label htmlFor="login-password">Password</label><div className="password-input"><input id="login-password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Enter your password" required/><button type="button" className="password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-controls="login-password" onClick={() => setShowPassword(value => !value)}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>{showPassword && <path d="m3 3 18 18"/>}</svg></button></div></div>
        <ErrorBox message={authError || error}/>
        <button className="button login-submit" disabled={authBusy}>{authBusy ? 'Signing in...' : 'Sign in'}<span aria-hidden="true">&rarr;</span></button>
        {error && <button type="button" className="button secondary" onClick={load}>Retry connection</button>}
      </form>}
    </section>
    <p className="login-footer">MAPOLY &middot; Student result screening</p>
  </main>;
  return <div className={`app-shell${collapsed ? ' sidebar-collapsed' : ''}`}>
    <a className="skip-link" href="#workspace">Skip to content</a>
    <header className="mobile-header"><div className="mobile-brand"><img src="/mapoly-logo.png" alt="MAPOLY crest"/><div><strong>MAPOLY</strong><span>Admission screening</span></div></div><button className="mobile-account" disabled={authBusy} onClick={accountAction} aria-label={user ? `Sign out ${user.username}` : 'Sign in'}><NavigationIcon name="account"/><span>{user ? 'Sign out' : 'Sign in'}</span></button></header>
    <aside className="sidebar" aria-label="Workspace navigation">
      <div className="brand"><img className="brand-logo" src="/mapoly-logo.png" alt="Moshood Abiola Polytechnic crest"/><div>MAPOLY<small>ADMISSION SCREENING</small></div></div>
      <div className="workspace-label">STAFF WORKSPACE</div>
      <button className="sidebar-toggle" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} aria-expanded={!collapsed} aria-controls="workspace-navigation" onClick={() => setCollapsed(value => !value)}><NavigationIcon name={collapsed ? 'expand' : 'collapse'}/><span className="toggle-label">Collapse sidebar</span><span className="nav-tooltip" role="tooltip">{collapsed ? 'Expand sidebar' : 'Collapse sidebar'}</span></button>
      <nav id="workspace-navigation" aria-label="Main navigation">
        {[['screen', 'Screening'], ['rules', 'Admission rules'], ['history', 'History']].map(([key, label]) => <button key={key} className={tab === key ? 'nav-item active' : 'nav-item'} aria-label={label} onClick={() => {setTab(key); window.scrollTo({top: 0, behavior: 'instant'});}} aria-current={tab === key ? 'page' : undefined}><NavigationIcon name={key}/><span className="nav-label">{label}</span><span className="nav-tooltip" role="tooltip">{label}</span></button>)}
      </nav>
      <div className="sidebar-note"><span className="status-dot"/> Admission services<p>Student records, requirements<br/>and screening in one place.</p></div>
      <div className="account"><div className="avatar">{user ? user.username[0].toUpperCase() : 'G'}</div><div><strong>{user?.username || 'Guest session'}</strong><small>{user?.is_staff ? 'Administrator' : user ? 'Screening user' : 'History is not saved'}</small></div></div>
      <button className="sidebar-auth" disabled={authBusy} aria-label={user ? `Sign out ${user.username}` : 'Sign in to save history'} onClick={accountAction}><NavigationIcon name="account"/><span className="auth-label">{user ? 'Sign out' : 'Sign in to save history'}</span><span className="nav-tooltip" role="tooltip">{user ? `Sign out ${user.username}` : 'Sign in'}</span></button>
    </aside>
    <main id="workspace" tabIndex="-1">
      <header className="topbar"><span>Moshood Abiola Polytechnic <span className="divider">/</span> Screening workspace</span></header>
      <div className="content">

        {loading ? <div className="empty" role="status">Loading the screening workspace…</div> : error ? <><ErrorBox message={error}/><button className="button secondary" onClick={load}>Retry connection</button></> : <>
          <div hidden={tab !== 'screen'}><Screening rules={rules.filter(r => r.active)} catalogue={catalogue} user={user} refreshRules={refreshRules}/></div>
          {tab === 'rules' && <Rules rules={rules} catalogue={catalogue} user={user} refreshRules={refreshRules}/>}
          {tab === 'history' && <History user={user} onLogin={() => setAuthOpen(true)} renderResult={result => <Result result={result}/>}/>}
        </>}
        <footer>Automated Student Result Screening System <span>MAPOLY · Admission services</span></footer>
      </div>
    </main>
    {authOpen && <div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="login-title"><button className="close" aria-label="Close sign in" onClick={() => setAuthOpen(false)}>×</button><div className="eyebrow">YOUR WORKSPACE</div><h2 id="login-title">Sign in</h2><p>Save screenings and access your history. Staff accounts can also edit admission rules.</p><form onSubmit={login}><Field label="Username"><input name="username" autoFocus autoComplete="username" required/></Field><Field label="Password"><input name="password" type="password" autoComplete="current-password" required/></Field><ErrorBox message={authError}/><button className="button" disabled={authBusy}>{authBusy ? 'Signing in…' : 'Sign in'}</button></form><small>Create your administrator account using the setup instructions in the README.</small></section></div>}
  </div>;
}

function Screening({rules, catalogue, user, refreshRules}) {
  const resultRef = useRef(null);
  const formRef = useRef(null);
  const [ruleId, setRuleId] = useState('');
  const [name, setName] = useState('');
  const [registration, setRegistration] = useState('');
  const [dob, setDob] = useState('');
  const [score, setScore] = useState('');
  const [jambSubjects, setJambSubjects] = useState(['', '', '', '']);
  const [sittings, setSittings] = useState([makeSitting()]);
  const [confirmed, setConfirmed] = useState(false);
  const [save, setSave] = useState(false);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const selected = rules.find(r => String(r.id) === ruleId);
  useEffect(() => { setResult(null); }, [rules, user]);
  useEffect(() => { if (result) resultRef.current?.scrollIntoView?.({behavior: 'smooth', block: 'start'}); }, [result]);
  function change(action) { setResult(null); setError(''); setConfirmed(false); action(); }
  function applyOCR(draft, mode) {
    change(() => {
      if (mode === 'complete') {
        setDob(draft.applicant?.dob || draft.dob || ''); setName(draft.student_name || ''); setRegistration(draft.registration_number || '');
        // A course printed on a document is not necessarily an approved rule set.
        // Require explicit programme selection instead of a fuzzy automatic match.
        const match = rules.filter(r => r.programme.trim().toLowerCase() === draft.course.trim().toLowerCase());
        setRuleId(match.length === 1 ? String(match[0].id) : '');
      }
      if (mode !== 'olevel') { setScore(draft.jamb_score === null ? '' : String(draft.jamb_score)); setJambSubjects(Array.from({length: 4}, (_, i) => draft.jamb_subjects?.[i] || '')); }
      if (mode !== 'jamb') setSittings(draft.sittings.length ? draft.sittings.map(s => ({...s, subjects: s.subjects.length ? s.subjects : [makeRow()]})) : [{board: '', exam_type: '', year: '', subjects: [makeRow()]}]);
    });
    formRef.current?.scrollIntoView?.({behavior: 'smooth', block: 'start'});
  }
  function updateSitting(index, key, value) { change(() => setSittings(old => old.map((s, i) => i === index ? {...s, [key]: value} : s))); }
  function updateRow(index, rowIndex, key, value) { updateSitting(index, 'subjects', sittings[index].subjects.map((row, i) => i === rowIndex ? {...row, [key]: value} : row)); }
  async function submit(event) {
    event.preventDefault(); setError(''); setResult(null); setBusy(true);
    try {
      if (!selected) throw new Error('Select a programme before screening.');
      const data = await api('screen', {method: 'POST', body: {rule_id: selected.id, rule_revision: selected.revision, student_name: name, dob, registration_number: registration, jamb_score: score === '' ? null : Number(score), jamb_subjects: jambSubjects.filter(Boolean), sittings: sittings.map(s => ({...s, year: Number(s.year)})), confirmed, save: Boolean(user && save)}});
      setResult(data);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  return <>
    <div className="page-heading"><div><div className="eyebrow">ADMISSIONS / NEW SCREENING</div><h1>Admission screening</h1><p>Upload results, screen an entire document, or enter a student below.</p></div></div>
    <OCRUpload onApply={applyOCR} disabled={busy} rules={rules} user={user}/>
    <div className="screen-layout"><form ref={formRef} onSubmit={submit}>
      <fieldset disabled={busy} className="form-fieldset">
      <section className="card"><div className="card-heading"><div className="step">01</div><div><h2>Student & programme</h2><p>Start with the applicant’s basic details.</p></div></div>
        <Field label="Date of birth"><input type="date" value={dob} onChange={e => change(() => setDob(e.target.value))}/><small>Must be 16 by September 30 of the processing year. Missing DOB or an underage applicant requires review.</small></Field>
        <div className="fields two"><Field label="Student’s full name"><input required maxLength={150} value={name} onChange={e => change(() => setName(e.target.value))} placeholder="e.g. Adeola Oluwaseun"/></Field><Field label="JAMB registration number"><input required maxLength={80} value={registration} onChange={e => change(() => setRegistration(e.target.value))} placeholder="Enter registration number"/></Field></div>
        <Field label="Programme & admission session"><select required value={ruleId} onChange={e => change(() => setRuleId(e.target.value))}><option value="">Select a programme</option>{rules.map(r => <option key={r.id} value={r.id}>{r.programme} / {r.admission_type || "ND Full-Time"} / {r.academic_session}</option>)}</select></Field>
        {!rules.length && <p className="muted">No active rules. An administrator can create them in Admission rules.</p>}
      </section>
      <section className="card"><div className="card-heading"><div className="step">02</div><div><h2>O’level results</h2><p>Enter each subject once per sitting. Credits are counted across distinct subjects.</p></div></div>
        {sittings.map((sitting, index) => <div className="sitting" key={index}>
          <div className="sitting-heading"><h3>Sitting {index + 1}</h3>{sittings.length > 1 && <button type="button" className="text-button danger" onClick={() => change(() => setSittings(sittings.filter((_, i) => i !== index)))}>Remove sitting</button>}</div>
          <div className="fields two"><Field label="O’level examination"><select required value={catalogue.examinations.some(exam => exam.board === sitting.board && exam.exam_type === sitting.exam_type) ? `${sitting.board}:${sitting.exam_type}` : ''} onChange={e => {
            const exam = catalogue.examinations.find(exam => `${exam.board}:${exam.exam_type}` === e.target.value);
            change(() => setSittings(old => old.map((s, i) => i === index ? {...s, board: exam.board, exam_type: exam.exam_type} : s)));
          }}><option value="" disabled>Select examination</option>{catalogue.examinations.map(exam => <option key={`${exam.board}:${exam.exam_type}`} value={`${exam.board}:${exam.exam_type}`}>{exam.label}</option>)}</select></Field><Field label="Examination year"><input required type="number" min="1980" max="2100" value={sitting.year} onChange={e => updateSitting(index, 'year', e.target.value)}/></Field></div>
          <div className="subject-head"><span>SUBJECT</span><span>GRADE</span><span/></div>
          {sitting.subjects.map((row, rowIndex) => <div className="subject-row" key={rowIndex}><select aria-label={`Sitting ${index + 1} subject ${rowIndex + 1}`} required value={row.subject} onChange={e => updateRow(index, rowIndex, 'subject', e.target.value)}><option value="">Select subject</option><Options values={catalogue.subjects.filter(s => s === row.subject || !sitting.subjects.some(r => r.subject === s))}/></select><select aria-label={`Sitting ${index + 1} grade ${rowIndex + 1}`} required value={row.grade} onChange={e => updateRow(index, rowIndex, 'grade', e.target.value)}><option value="">Grade</option><Options values={catalogue.grades}/></select><button type="button" className="remove" aria-label={`Remove subject ${rowIndex + 1} from sitting ${index + 1}`} disabled={sitting.subjects.length === 1} onClick={() => updateSitting(index, 'subjects', sitting.subjects.filter((_, i) => i !== rowIndex))}>×</button></div>)}
          <button type="button" className="text-button" disabled={sitting.subjects.length >= 9} onClick={() => updateSitting(index, 'subjects', [...sitting.subjects, makeRow()])}>＋ Add subject</button>
        </div>)}
        {sittings.length < 2 && <button className="button secondary small" type="button" onClick={() => change(() => setSittings([...sittings, makeSitting()]))}>＋ Add second sitting</button>}
      </section>
      <section className="card"><div className="card-heading"><div className="step">03</div><div><h2>JAMB result & confirmation</h2><p>Leave the score empty if the result is not yet available.</p></div></div>
        <Field label="JAMB total score"><div className="score-input"><input type="number" min="0" max="400" step="1" value={score} onChange={e => change(() => setScore(e.target.value))} placeholder="0"/><span>/ 400</span></div></Field>
        {selected?.criteria?.jamb_groups && <div><h3>Four JAMB subjects</h3><p>Enter the subjects taken in UTME, separately from O-level subjects. Missing combinations stay pending review.</p><div className="fields two">{jambSubjects.map((subject, index) => <Field key={index} label={`JAMB subject ${index + 1}`}><select value={subject} onChange={e => change(() => setJambSubjects(old => old.map((s, i) => i === index ? e.target.value : s)))}><option value="">Select subject</option><Options values={catalogue.subjects.filter(s => s === subject || !jambSubjects.includes(s))}/></select></Field>)}</div></div>}
        <label className="checkbox"><input type="checkbox" checked={confirmed} onChange={e => { setConfirmed(e.target.checked); setResult(null); }}/><span>I have reviewed the entries and included all available subjects. Missing subjects can be assessed as absent.</span></label>
        <label className="checkbox"><input type="checkbox" disabled={!user} checked={Boolean(user && save)} onChange={e => { setSave(e.target.checked); setResult(null); }}/><span>Save this screening to my history {!user && <small>— sign in to enable</small>}</span></label>
        <ErrorBox message={error}/>
        <div className="form-actions"><span>Unconfirmed results stay pending review.</span><button className="button" disabled={busy || !rules.length}>{busy ? 'Checking requirements…' : 'Screen student →'}</button></div>
      </section>
      </fieldset>
    </form><aside className="requirements-panel"><div className="card requirement-card"><div className="eyebrow">YOUR SCREENING GUIDE</div><h2>What we’re checking</h2>{selected ? <><p>{selected.programme}</p><div className="rule-stats"><div><strong>{selected.minimum_jamb ?? 'Not set'}</strong><span>Minimum JAMB</span></div><div><strong>{selected.minimum_credits}</strong><span>O’level credits</span></div></div><h3>Required subjects</h3><ul className="requirements-list">{selected.required_subjects.map(r => <li key={r.subject}><span>{r.subject}</span><b>{r.minimum_grade}+</b></li>)}</ul><div className="note">{selected.max_sittings ? `Up to ${selected.max_sittings} sitting(s).` : 'Sitting limit needs clarification.'} {selected.allow_combining ? 'Best grade per subject is used when combining.' : 'Combining results is not allowed.'}</div><CriteriaDetails rule={selected}/><small>Rule revision {selected.revision}</small></> : <p>Select a programme to view its admission requirements.</p>}<button className="text-button" onClick={async () => { try { await refreshRules(); } catch (e) { setError(e.message); } }}>↻ Reload programmes</button></div><div className="help-note"><strong>Grades at a glance</strong><p>A1–C6 count as credits. D7, E8 and F9 do not. Awaiting, withheld and unreadable grades need review.</p></div></aside></div>
    {result && <div ref={resultRef} className="result-wrap" role="status"><Result result={result}/></div>}
  </>;
}

export function Result({result}) {
  const passed = result.checks.filter(c => c.status === 'passed').length;
  return <section className="card result-card">{result.warnings?.map((warning, index) => <p className="note" key={index}>{warning}</p>)}{result.duplicate_notice && <p className="note">{result.duplicate_notice}</p>}<div className="result-heading"><div><div className="eyebrow">SCREENING OUTCOME</div><h2>{result.student.name}</h2><p>{result.rules.programme} · {result.student.registration_number}</p></div><span className={`result-badge ${result.status === 'Eligible' ? 'passed' : result.status === 'Pending Review' ? 'pending' : 'failed'}`}>{result.status}</span></div><p>{passed} of {result.checks.length} checks passed. Assessed against rule revision {result.rules.revision}.{result.id ? ` Saved as screening #${result.id}.` : ' Not saved.'}</p><div className="check-list">{result.checks.map((check, i) => <div className="check" key={i}><span className={`check-icon ${check.status}`}>{check.status === 'passed' ? '✓' : check.status === 'failed' ? '×' : '!'}</span><div><strong>{check.label}</strong><p>{check.detail}</p></div><span className={`check-status ${check.status}`}>{check.status}</span></div>)}</div><details><summary>View submitted results and rule snapshot</summary><div className="snapshot"><p>JAMB: {result.jamb_score ?? 'Not entered'} / 400 · Session: {result.rules.academic_session}</p>{result.sittings.map((s, i) => <div key={i}><h3>Sitting {i + 1} · {s.board} · {s.exam_type} · {s.year}</h3><p>{s.subjects.map(r => `${r.subject}: ${r.grade}`).join(' · ')}</p></div>)}<p>JAMB subjects: {result.jamb_subjects?.join(", ") || "Not supplied"}</p><CriteriaDetails rule={result.rules}/><p>Required credits: {result.rules.minimum_credits}; minimum JAMB: {result.rules.minimum_jamb}; maximum sittings: {result.rules.max_sittings}; combining: {result.rules.allow_combining ? 'allowed' : 'not allowed'}.</p><p>Required subjects: {result.rules.required_subjects.map(s => `${s.subject} ${s.minimum_grade}+`).join(', ')}.</p></div></details></section>;
}

function Rules({rules, catalogue, user, refreshRules}) {
  const [draft, setDraft] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [criteriaValid, setCriteriaValid] = useState(true);
  const [busy, setBusy] = useState(false);
  function update(key, value) { setDraft(d => ({...d, [key]: value})); }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try {
      await api(draft.id ? `rules/${draft.id}` : 'rules', {method: draft.id ? 'PUT' : 'POST', body: {...draft, minimum_jamb: draft.minimum_jamb === '' || draft.minimum_jamb === null ? null : Number(draft.minimum_jamb), minimum_credits: Number(draft.minimum_credits), max_sittings: draft.max_sittings === null || draft.max_sittings === '' ? null : Number(draft.max_sittings)}});
      await refreshRules(); setDraft(null); setNotice('Admission rules saved. Existing screening history is unchanged.');
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  return <><div className="page-heading"><div><div className="eyebrow">ADMISSIONS / REQUIREMENTS</div><h1>Rules you can review.</h1><p>Configure the criteria used for each programme and session.</p></div>{user?.is_staff && <button className="button" onClick={() => { setCriteriaValid(true); setDraft(newRules()); setError(''); setNotice(''); }}>＋ New rule set</button>}</div>
    {!user?.is_staff && <div className="note">You can view active rules. Sign in with a staff account to create or edit them.</div>}
    {notice && <div className="success" role="status">{notice}</div>}
    <ErrorBox message={error}/>
    {draft && <section className="card"><h2>{draft.id ? 'Edit admission rules' : 'Create admission rules'}</h2><form onSubmit={submit}><fieldset className="form-fieldset" disabled={busy}><div className="fields two"><Field label="Admission type"><select value={draft.admission_type || "ND Full-Time"} onChange={e => update("admission_type", e.target.value)}><Options values={["All Admission Type", "ND Full-Time", "ND Part-Time", "HND Full-Time", "HND Part-Time"]}/></select></Field><Field label="Programme name"><input required maxLength={150} value={draft.programme} onChange={e => update('programme', e.target.value)}/></Field><Field label="Academic session"><input required maxLength={30} value={draft.academic_session} onChange={e => update('academic_session', e.target.value)}/></Field></div><div className="fields three"><Field label="Minimum JAMB score"><input type="number" min="0" max="400" value={draft.minimum_jamb ?? ""} onChange={e => update('minimum_jamb', e.target.value)}/></Field><Field label="Required credit subjects"><input required type="number" min="1" max="9" value={draft.minimum_credits} onChange={e => update('minimum_credits', e.target.value)}/></Field><Field label="Maximum sittings"><select value={draft.max_sittings ?? ""} onChange={e => setDraft(d => ({...d, max_sittings: e.target.value === '' ? null : Number(e.target.value), allow_combining: e.target.value === '1' ? false : d.allow_combining}))}><option value="">Not specified</option><Options values={[1, 2]}/></select></Field></div><label className="checkbox"><input type="checkbox" disabled={Number(draft.max_sittings) === 1} checked={draft.allow_combining} onChange={e => update('allow_combining', e.target.checked)}/>Allow combining the best grades from two sittings</label><h3>Required subjects & minimum grades</h3>{draft.required_subjects.map((row, index) => <div className="subject-row" key={index}><select aria-label={`Required subject ${index + 1}`} value={row.subject} required onChange={e => update('required_subjects', draft.required_subjects.map((r, i) => i === index ? {...r, subject: e.target.value} : r))}><option value="">Select subject</option><Options values={catalogue.subjects.filter(s => s === row.subject || !draft.required_subjects.some(r => r.subject === s))}/></select><select aria-label={`Minimum grade ${index + 1}`} value={row.minimum_grade} onChange={e => update('required_subjects', draft.required_subjects.map((r, i) => i === index ? {...r, minimum_grade: e.target.value} : r))}><Options values={catalogue.grades.slice(0, 9)}/></select><button type="button" className="remove" aria-label={`Remove required subject ${index + 1}`} disabled={draft.required_subjects.length === 1} onClick={() => update('required_subjects', draft.required_subjects.filter((_, i) => i !== index))}>×</button></div>)}<button type="button" className="text-button" disabled={draft.required_subjects.length >= 9} onClick={() => update('required_subjects', [...draft.required_subjects, {subject: '', minimum_grade: 'C6'}])}>＋ Add required subject</button><CriteriaDetails rule={draft}/>{draft.criteria?.credit_paths && <CriteriaEditor key={draft.id || "new"} value={draft.criteria} subjects={catalogue.subjects} onChange={value => update("criteria", value)} onValidityChange={setCriteriaValid}/>}<label className="checkbox"><input type="checkbox" checked={draft.active} onChange={e => update('active', e.target.checked)}/>Active and available for screening</label><div className="form-actions"><button className="button secondary" type="button" onClick={() => { setDraft(null); setError(''); }}>Cancel</button><button className="button" disabled={!criteriaValid}>{busy ? 'Saving…' : 'Save admission rules'}</button></div></fieldset></form></section>}
    <p className="note">The supplied compendium covers all admission types across all sessions. UTME checks apply to ND Full-Time; HND also requires ND grade and CGPA checks. Review any highlighted clarifications and the session-specific UTME cutoff before final decisions.</p><div className="rule-grid">{rules.map(rule => <section className="card" key={rule.id}><div className="eyebrow">{rule.active ? 'ACTIVE' : 'INACTIVE'} · REVISION {rule.revision}</div><h2>{rule.programme}</h2><p>{rule.admission_type || "ND Full-Time"} / {rule.academic_session}</p><div className="rule-stats"><div><strong>{rule.minimum_jamb ?? 'Not set'}</strong><span>JAMB minimum</span></div><div><strong>{rule.minimum_credits}</strong><span>Credit subjects</span></div></div><ul className="requirements-list">{rule.required_subjects.map(r => <li key={r.subject}><span>{r.subject}</span><b>{r.minimum_grade}+</b></li>)}</ul><CriteriaDetails rule={rule}/><p className="muted">Maximum {rule.max_sittings ?? "unspecified"} sitting(s) · Combining {rule.allow_combining ? 'allowed' : 'not allowed'}</p>{user?.is_staff && <button className="button secondary small" onClick={() => { setCriteriaValid(true); setDraft(structuredClone(rule)); setError(''); setNotice(''); window.scrollTo({top: 0, behavior: 'smooth'}); }}>Edit rules ↗</button>}</section>)}</div>
    {!rules.length && <div className="empty">No rules yet. Create an admission rule set to begin.</div>}
  </>;
}
