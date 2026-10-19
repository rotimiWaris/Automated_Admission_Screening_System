import React from 'react';
import {render, screen, cleanup, waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach, beforeEach, it, expect, vi} from 'vitest';
import BatchScreening from './BatchScreening';
import {api} from './api';
vi.mock('./api', () => ({api: vi.fn()}));
afterEach(cleanup);
const rules = [{id: 1, programme: 'Computer Science', revision: 3, academic_session: '2026/2027'}];
const draft = {student_name: 'Test Student', registration_number: 'TEST-001', course: 'Computer Science', jamb_score: 240, sittings: []};
const pages = [{page: 1, token: 'signed-first', drafts: [draft]}, {page: 2, token: 'signed-second', drafts: [{...draft, registration_number: 'TEST-002'}]}];
beforeEach(() => {api.mockReset(); api.mockResolvedValue({summary: {Eligible: 2}, results: pages.map(p => ({...p.drafts[0], page: p.page, status: 'Eligible', issues: [], result: null}))});});

it('downloads the generated workbook automatically and offers another download', async () => {
  const create = vi.fn(() => 'blob:report');
  const revoke = vi.fn();
  vi.stubGlobal('URL', {...URL, createObjectURL: create, revokeObjectURL: revoke});
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  api.mockResolvedValueOnce({summary: {}, results: [], excel: {filename: 'screening-results.xlsx', base64: btoa('workbook')}});
  try {
    render(<BatchScreening pages={pages} rules={rules} onReview={vi.fn()}/>);
    await screen.findByRole('button', {name: 'Download Excel results'});
    expect(create).toHaveBeenCalledTimes(1);
    await userEvent.click(screen.getByRole('button', {name: 'Download Excel results'}));
    expect(click).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(revoke).toHaveBeenCalledTimes(2), {timeout: 2500});
  } finally { click.mockRestore(); vi.unstubAllGlobals(); }
});

it('automatically screens all pages using exact programme matches without retyping', async () => {
  render(<BatchScreening pages={pages} rules={rules} onReview={vi.fn()}/>);
  await waitFor(() => expect(api).toHaveBeenCalledWith('screen-batch', {method: 'POST', body: {pages: ['signed-first', 'signed-second'], course_rules: {'Computer Science': {id: 1, revision: 3}}, admission_type: 'ND Full-Time', save: false}}));
  expect(await screen.findAllByText('Test Student')).toHaveLength(2);
});

it('submits automatic screening only once under React StrictMode', async () => {
  render(<React.StrictMode><BatchScreening pages={pages} rules={rules} user={{username: 'staff'}} onReview={vi.fn()}/></React.StrictMode>);
  await screen.findAllByText('Test Student');
  expect(api).toHaveBeenCalledTimes(1);
});

it('requires an explicit course mapping when names differ and allows correction of a record', async () => {
  const review = vi.fn(); const user = userEvent.setup();
  render(<BatchScreening pages={pages} rules={[{...rules[0], programme: 'Computing'}]} onReview={review} automatic={false}/>);
  expect(api).not.toHaveBeenCalled();
  await user.selectOptions(screen.getByLabelText('Computer Science'), '1');
  await user.click(screen.getByRole('button', {name: 'Screen all students'}));
  await user.click((await screen.findAllByRole('button', {name: /Open student for corrections/}))[1]);
  expect(review).toHaveBeenCalledWith(expect.objectContaining({registration_number: 'TEST-002', page: 2}), 'complete');
});

it('automatically saves for signed-in users and lets them switch to an unsaved assessment', async () => {
  const user = userEvent.setup();
  render(<BatchScreening pages={pages} rules={rules} user={{username: 'staff'}} onReview={vi.fn()}/>);
  await screen.findAllByText('Test Student');
  expect(api).toHaveBeenLastCalledWith('screen-batch', expect.objectContaining({body: expect.objectContaining({save: true})}));
  await user.click(screen.getByRole('checkbox', {name: /Save evaluated students/}));
  const button = screen.getByRole('button', {name: 'Screen all students'});
  expect(button).toBeEnabled();
  await user.click(button);
  expect(api).toHaveBeenLastCalledWith('screen-batch', expect.objectContaining({body: expect.objectContaining({save: false})}));
});

it('shows a fresh outcome and checks for a student already in history', async () => {
  api.mockResolvedValueOnce({summary: {'Not Eligible': 1}, results: [{...draft, page: 1, status: 'Not Eligible', issues: [], save_skipped: true, storage_notice: 'Already in history; not saved again.', result: {remark: 'Unqualified', checks: [{label: 'JAMB score', status: 'failed', detail: '50; minimum 180.'}]}}]});
  render(<BatchScreening pages={pages} rules={rules} user={{username: 'staff'}} onReview={vi.fn()}/>);
  expect(await screen.findByText(/Already in history; not saved again/)).toBeInTheDocument();
  expect(screen.getByText('Remark: Unqualified')).toBeInTheDocument();
  await userEvent.click(screen.getByText('View requirement checks'));
  expect(screen.getByText('50; minimum 180.')).toBeInTheDocument();
  expect(screen.queryByText('Duplicate')).not.toBeInTheDocument();
});

it('paginates large batches and opens the correct draft on page two', async () => {
  const records=Array.from({length:51},(_,i)=>({...draft,student_name:`Student ${i+1}`,registration_number:`REG${i}`}));
  api.mockResolvedValueOnce({summary:{Eligible:51},results:records.map(item=>({...item,page:1,status:'Eligible',issues:[],result:null}))});
  const onReview=vi.fn();const user=userEvent.setup();
  render(<BatchScreening pages={[{page:1,token:'signed',drafts:records}]} rules={rules} onReview={onReview}/>);
  await screen.findByText('Page 1 of 2');
  expect(screen.queryByRole('heading',{name:'Student 51'})).not.toBeInTheDocument();
  await user.click(screen.getByRole('button',{name:'Next results'}));
  expect(screen.getByRole('heading',{name:'Student 51'})).toBeInTheDocument();
  await user.click(screen.getByRole('button',{name:/Open student for corrections/}));
  expect(onReview).toHaveBeenCalledWith(expect.objectContaining({registration_number:'REG50'}),'complete');
});


it.each(['ND Part-Time', 'HND Full-Time', 'HND Part-Time'])('uses server course matching for %s', async admissionType => {
  render(<BatchScreening pages={pages} rules={rules} admissionType={admissionType} onReview={vi.fn()}/>);
  await waitFor(() => expect(api).toHaveBeenCalledWith('screen-batch', expect.objectContaining({body: expect.objectContaining({course_rules: {}, admission_type: admissionType})})));
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
});
