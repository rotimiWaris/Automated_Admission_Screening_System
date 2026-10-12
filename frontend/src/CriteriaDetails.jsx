export { default as CriteriaEditor } from './CriteriaEditor';

function Groups({groups}) {
  return <ul className="criteria-groups">{groups.map((g, i) => <li key={i}><strong>{g.count === 1 ? 'One' : g.count} from: </strong>{g.options.map(o => o.join(' / ')).join(', ')}</li>)}</ul>;
}

export default function CriteriaDetails({rule}) {
  const criteria = rule.criteria;
  if (!criteria?.credit_paths) return null;
  return <div className="criteria-details">
    <p><strong>{rule.admission_type}</strong> · {rule.academic_session}<br/>{criteria.school}</p>
    {!!criteria.review_notes?.length && <div className="note"><strong>Clarification required before a final decision</strong><ul>{criteria.review_notes.map((note, i) => <li key={i}>{note}</li>)}</ul></div>}
    <details><summary>Full subject requirements</summary>
      <h3>Five distinct O’level credits (A1–C6)</h3>
      <p>Each subject counts once. Subjects separated by / are alternatives within a selection.</p>
      {criteria.credit_paths.map((groups, i) => <div key={i}>{criteria.credit_paths.length > 1 && <h4>Accepted path {i + 1}</h4>}<Groups groups={groups}/></div>)}
      {!!criteria.pass_groups?.length && <><h3>Additional passes (E8 or above)</h3><Groups groups={criteria.pass_groups}/><p>A credit also satisfies a pass requirement.</p></>}
      {(!rule.admission_type || ['ND Full-Time', 'All Admission Type'].includes(rule.admission_type)) && <><h3>JAMB subject combination (ND Full-Time)</h3><Groups groups={criteria.jamb_groups}/></>}
      {criteria.advisories?.map((note, i) => <p key={i}>{note}</p>)}
    </details>
    <details><summary>Compendium source · row {criteria.source_row}</summary><p>{rule.source}</p><p className="compendium-source">{criteria.source_text}</p></details>
    {criteria.cutoff_source && (!rule.admission_type || ['ND Full-Time', 'All Admission Type'].includes(rule.admission_type)) && <p className="muted">UTME default: {criteria.cutoff_source.score}, sourced for {criteria.cutoff_source.session}. <a href={criteria.cutoff_source.url} target="_blank" rel="noreferrer">MAPOLY notice</a>. Review the cutoff for subsequent sessions.</p>}
  </div>;
}
