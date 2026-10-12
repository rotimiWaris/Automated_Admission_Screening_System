import {useEffect, useRef, useState} from 'react';
import {api} from './api';

function ScreeningModal({record, onDismiss, renderResult}) {
  const dialog = useRef(null);
  useEffect(() => {
    const opener = document.activeElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const node = dialog.current;
    node.showModal();
    return () => {node.close(); document.body.style.overflow = overflow; opener?.focus();};
  }, []);
  return <dialog ref={dialog} className="history-dialog" aria-labelledby="screening-dialog-title" onCancel={event => {event.preventDefault(); onDismiss();}}>
    <div className="history-dialog-heading"><h2 id="screening-dialog-title">Saved screening #{record.id}</h2><button className="button secondary" type="button" onClick={onDismiss}>Close details</button></div>
    {renderResult(record)}
  </dialog>;
}

export default function History({user, onLogin, renderResult}) {
  const [data, setData] = useState({history: [], count: 0, page: 1, num_pages: 1});
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!user) return;
    let current = true;
    setLoading(true); setError('');
    api('history', {query: {page, q: search}}).then(response => {
      if (current) setData(response);
    }).catch(error => {if (current) setError(error.message);}).finally(() => {if (current) setLoading(false);});
    return () => {current = false;};
  }, [user, page, search, refresh]);
  if (!user) return <div className="empty"><h1>Your screening history</h1><p>Sign in to save and revisit your screenings.</p><button className="button" onClick={onLogin}>Sign in</button></div>;
  function find(event) {event.preventDefault(); setPage(1); setSearch(query.trim()); setRefresh(value => value + 1);}
  return <>
    <div className="page-heading"><div><div className="eyebrow">ADMISSIONS / HISTORY</div><h1>Every decision, explained.</h1><p>All your saved screenings, 50 per page, with the requirements used at the time.</p></div><button className="button secondary" disabled={loading} onClick={() => setRefresh(value => value + 1)}>Refresh</button></div>
    <form className="history-search" onSubmit={find}><label className="field"><span>Search screenings</span><input type="search" value={query} maxLength={150} onChange={event => setQuery(event.target.value)} placeholder="Name, registration, programme or status" aria-describedby="history-search-help"/></label><button className="button" type="submit">Search</button>{search && <button className="button secondary" type="button" onClick={() => {setQuery(''); setSearch(''); setPage(1);}}>Clear search</button>}</form>
    <p id="history-search-help" className="muted">Search by status: pending, qualified, unqualified, eligible or not eligible. Tags such as #pending also work.</p>
    {error && <div className="error" role="alert">{error}</div>}
    {loading ? <p role="status">Loading history…</p> : !error && <>
      <p className="muted" role="status">{data.count ? `${(data.page - 1) * 50 + 1}–${Math.min(data.page * 50, data.count)} of ${data.count} screenings` : '0 screenings'}</p>
      <div className="card history-list">{data.history.length ? data.history.map(record => <button key={record.id} className="history-row" aria-haspopup="dialog" onClick={() => setSelected(record)}><div><strong>{record.student.name}</strong><small>{record.rules.programme} · {new Date(record.created_at).toLocaleString()}</small></div><span className={`result-badge ${record.status === 'Eligible' ? 'passed' : record.status === 'Pending Review' ? 'pending' : 'failed'}`}>{record.status}</span><span aria-hidden="true">↗</span></button>) : <p className="empty">{search ? 'No matching screenings.' : 'No saved screenings yet.'}</p>}</div>
      <nav className="history-pagination" aria-label="History pages"><button className="button secondary" disabled={data.page <= 1} onClick={() => setPage(data.page - 1)}>Previous page</button><span>Page {data.page} of {data.num_pages}</span><button className="button secondary" disabled={data.page >= data.num_pages} onClick={() => setPage(data.page + 1)}>Next page</button></nav>
    </>}
    {selected && <ScreeningModal record={selected} onDismiss={() => setSelected(null)} renderResult={renderResult}/>}
  </>;
}
