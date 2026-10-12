import React, { useState } from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CriteriaEditor from './CriteriaEditor';

afterEach(cleanup);
const subjects = ['English Language', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Agricultural Science', 'Economics'];
const original = {
  credit_paths: [[{count: 5, options: subjects.slice(0, 5).map(s => [s])}]],
  jamb_groups: [{count: 4, options: subjects.slice(0, 4).map(s => [s])}], pass_groups: [],
  review_notes: ['Confirm this requirement.'], advisories: [], source_text: 'Original wording', source_row: 1,
};
function Harness({changed, valid}) {
  const [value, setValue] = useState(structuredClone(original));
  return <CriteriaEditor value={value} subjects={subjects} onValidityChange={valid} onChange={next => {setValue(next); changed(next);}}/>;
}

it('edits an alternative with dropdowns, validates blanks and preserves provenance', async () => {
  const user=userEvent.setup(), changed=vi.fn(), valid=vi.fn();
  render(<Harness changed={changed} valid={valid}/>);
  expect(valid).toHaveBeenLastCalledWith(true);
  const requirement=screen.getByRole('group', {name:'Credit path 1 · requirement 1'});
  await user.click(within(requirement).getAllByRole('button', {name:'Add alternative (or)'})[4]);
  expect(valid).toHaveBeenLastCalledWith(false);
  await user.selectOptions(screen.getByLabelText('Credit path 1, requirement 1, choice 5, subject 2'), 'Agricultural Science');
  expect(valid).toHaveBeenLastCalledWith(true);
  const value=changed.mock.lastCall[0];
  expect(value.credit_paths[0][0].options[4]).toEqual(['Biology','Agricultural Science']);
  expect(value.credit_paths[0][0].count).toBe(5);
  expect(value.source_text).toBe('Original wording');
  expect(value.jamb_groups).toEqual(original.jamb_groups);
});

it('blocks incorrect totals and allows removing an unfinished alternative path', async () => {
  const user=userEvent.setup(), changed=vi.fn(), valid=vi.fn();
  render(<Harness changed={changed} valid={valid}/>);
  await user.selectOptions(screen.getAllByLabelText('Number of subjects required')[0], '4');
  expect(screen.getByRole('alert')).toHaveTextContent('Credit path 1: choose a total of 5');
  expect(valid).toHaveBeenLastCalledWith(false);
  await user.selectOptions(screen.getAllByLabelText('Number of subjects required')[0], '5');
  await user.click(screen.getByRole('button',{name:'Add another accepted path'}));
  expect(valid).toHaveBeenLastCalledWith(false);
  await user.click(screen.getByRole('button',{name:'Remove path 2'}));
  expect(valid).toHaveBeenLastCalledWith(true);
});

it('edits pass requirements and removes review notes without altering credit paths', async () => {
  const user=userEvent.setup(), changed=vi.fn(), valid=vi.fn();
  render(<Harness changed={changed} valid={valid}/>);
  await user.click(screen.getByText('Additional O’level passes'));
  await user.click(screen.getByRole('button',{name:'Add requirement to Additional passes'}));
  await user.selectOptions(screen.getByLabelText('Additional passes, requirement 1, choice 1, subject 1'),'Physics');
  await user.click(screen.getByText('Review notes and guidance'));
  await user.click(screen.getByRole('button',{name:'Remove note'}));
  expect(changed.mock.lastCall[0]).toMatchObject({review_notes:[],credit_paths:original.credit_paths,pass_groups:[{count:1,options:[['Physics']]}]});
  expect(valid).toHaveBeenLastCalledWith(true);
});
