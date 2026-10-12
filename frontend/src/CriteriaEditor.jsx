import { useEffect } from 'react';

const newGroup = () => ({count: 1, options: [[]], label: 'Subject selection'});
const total = groups => groups.reduce((sum, group) => sum + group.count, 0);

function problems(value) {
  const errors = [];
  const validate = (groups, title, expected) => {
    if (expected && total(groups) !== expected) errors.push(`${title}: choose a total of ${expected} subjects (currently ${total(groups)}).`);
    groups.forEach((group, index) => {
      if (group.count > group.options.length) errors.push(`${title}, requirement ${index + 1}: add more choices or reduce the number required.`);
      if (group.options.some(option => !option.length || option.some(subject => !subject))) errors.push(`${title}, requirement ${index + 1}: select a subject in every choice.`);
      const subjects = group.options.flat();
      if (new Set(subjects).size !== subjects.length) errors.push(`${title}, requirement ${index + 1}: a subject appears more than once.`);
    });
  };
  value.credit_paths.forEach((groups, index) => validate(groups, `Credit path ${index + 1}`, 5));
  validate(value.jamb_groups, 'JAMB combination', 4);
  validate(value.pass_groups, 'Additional passes');
  return errors;
}

function Selection({groups, onChange, subjects, title}) {
  const update = (index, group) => onChange(groups.map((item, i) => i === index ? {...group, label: `${title} requirement ${index + 1}`} : item));
  return <div className="selection-builder">
    {groups.map((group, index) => <fieldset className="selection-requirement" key={index}>
      <legend>{title} · requirement {index + 1}</legend>
      <div className="selection-toolbar"><label className="field"><span>Number of subjects required</span><select value={group.count} onChange={e => update(index, {...group, count: Number(e.target.value)})}>{Array.from({length: 9}, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}</select></label><button type="button" className="button secondary small" onClick={() => onChange(groups.filter((_, i) => i !== index))}>Remove requirement</button></div>
      <p>Choose {group.count} distinct {group.count === 1 ? 'subject' : 'subjects'} from the choices below. An “or” choice counts as one.</p>
      {group.options.map((option, optionIndex) => <div className="selection-choice" key={optionIndex}>
        <strong>Choice {optionIndex + 1}</strong>
        {(option.length ? option : ['']).map((subject, subjectIndex) => <div className="selection-subject" key={subjectIndex}>
          {subjectIndex > 0 && <span>or</span>}
          <label className="field"><span className="sr-only">{title}, requirement {index + 1}, choice {optionIndex + 1}, subject {subjectIndex + 1}</span><select value={subject} onChange={e => {
            const next = option.length ? [...option] : ['']; next[subjectIndex] = e.target.value;
            update(index, {...group, options: group.options.map((item, i) => i === optionIndex ? next : item)});
          }}><option value="">Select subject</option>{subjects.filter(s => s === subject || !group.options.flat().includes(s)).map(s => <option key={s}>{s}</option>)}</select></label>
          {subjectIndex > 0 && <button type="button" className="button secondary small" aria-label={`Remove alternative ${subjectIndex + 1} from ${title} requirement ${index + 1} choice ${optionIndex + 1}`} onClick={() => update(index, {...group, options: group.options.map((item, i) => i === optionIndex ? item.filter((_, j) => j !== subjectIndex) : item)})}>Remove</button>}
        </div>)}
        <div className="selection-actions"><button type="button" className="text-button" disabled={!option.length || option.length >= 10 || option.includes('')} onClick={() => update(index, {...group, options: group.options.map((item, i) => i === optionIndex ? [...item, ''] : item)})}>Add alternative (or)</button><button type="button" className="text-button" disabled={group.options.length === 1} onClick={() => update(index, {...group, options: group.options.filter((_, i) => i !== optionIndex)})}>Remove choice</button></div>
      </div>)}
      <button type="button" className="button secondary small" disabled={group.options.length >= 80} onClick={() => update(index, {...group, options: [...group.options, []]})}>Add another choice</button>
    </fieldset>)}
    <button type="button" className="button secondary small" disabled={groups.length >= 9} onClick={() => onChange([...groups, newGroup()])}>Add requirement to {title}</button>
  </div>;
}

function Notes({title, items, onChange, explanation}) {
  return <section><h3>{title}</h3><p>{explanation}</p>{items.map((note, i) => <div className="selection-subject" key={i}><label className="field"><span>{title} {i + 1}</span><textarea rows={3} maxLength={2000} value={note} onChange={e => onChange(items.map((s, j) => j === i ? e.target.value : s))}/></label><button type="button" className="button secondary small" onClick={() => onChange(items.filter((_, j) => j !== i))}>Remove note</button></div>)}<button type="button" className="button secondary small" disabled={items.length >= 20} onClick={() => onChange([...items, ''])}>Add {title.toLowerCase()}</button></section>;
}

export default function CriteriaEditor({value, subjects = [], onChange, onValidityChange}) {
  const errors = problems(value);
  const valid = !errors.length;
  useEffect(() => { onValidityChange(valid); }, [valid, onValidityChange]);
  const update = (key, items) => onChange({...value, [key]: items});
  return <section className="criteria-form" aria-label="Subject requirements editor">
    <h3>Edit subject requirements</h3><p>Use the menus below. For example, “any two of Physics, Chemistry or Economics” is one requirement with a count of 2 and three separate choices. Use “Add alternative (or)” for a shared choice such as Biology or Agricultural Science.</p>
    <details open><summary>O’level credit combinations</summary><p>A student must satisfy one complete path. Each path needs five different subjects at C6 or above. A subject cannot count twice. The compulsory subjects and minimum grades above also apply to every path.</p>
      {value.credit_paths.map((groups, index) => <section className="credit-path" key={index}><h4>Accepted path {index + 1} · {total(groups)} of 5 credits</h4>
        <Selection title={`Credit path ${index + 1}`} groups={groups} subjects={subjects} onChange={next => update('credit_paths', value.credit_paths.map((p, i) => i === index ? next : p))}/>
        {value.credit_paths.length > 1 && <button type="button" className="text-button" onClick={() => update('credit_paths', value.credit_paths.filter((_, i) => i !== index))}>Remove path {index + 1}</button>}
      </section>)}
      <button type="button" className="button secondary small" disabled={value.credit_paths.length >= 5} onClick={() => update('credit_paths', [...value.credit_paths, [newGroup()]])}>Add another accepted path</button>
    </details>
    <details><summary>JAMB subjects · {total(value.jamb_groups)} of 4</summary><p>Include English in the four required subjects.</p><Selection title="JAMB" groups={value.jamb_groups} subjects={subjects} onChange={next => update('jamb_groups', next)}/></details>
    <details><summary>Additional O’level passes</summary><p>These require E8 or better. A credit also satisfies a pass; it can be a subject already counted above.</p><Selection title="Additional passes" groups={value.pass_groups} subjects={subjects} onChange={next => update('pass_groups', next)}/></details>
    <details><summary>Review notes and guidance</summary><Notes title="Review notes" items={value.review_notes || []} onChange={next => update('review_notes', next)} explanation="Each note keeps screenings Pending Review until it is resolved and removed."/><Notes title="Guidance notes" items={value.advisories || []} onChange={next => update('advisories', next)} explanation="Information for administrators. These notes do not block eligibility."/></details>
    {!!errors.length && <div className="error" role="alert"><strong>Before saving:</strong><ul>{errors.map(error => <li key={error}>{error}</li>)}</ul></div>}
    <p>Changes take effect when you select Save admission rules. Original source text and saved screening history are preserved.</p>
  </section>;
}
