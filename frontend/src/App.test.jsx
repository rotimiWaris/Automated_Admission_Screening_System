import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import { api } from './api';
vi.mock('./api', () => ({api: vi.fn()}));

const subjects = ['English Language', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Economics'];
const examinations = [
  {board: 'WAEC', exam_type: 'School', label: 'WAEC — WASSCE / SSCE (School)'},
  {board: 'WAEC', exam_type: 'Private/GCE', label: 'WAEC — GCE O’level / WASSCE (Private)'},
  {board: 'WAEC', exam_type: 'WASC', label: 'WAEC — WASC (Legacy certificate)'},
  {board: 'NECO', exam_type: 'School', label: 'NECO — SSCE Internal (School)'},
  {board: 'NECO', exam_type: 'Private/GCE', label: 'NECO — SSCE External / GCE (Private)'},
  {board: 'NABTEB', exam_type: 'School', label: 'NABTEB — NBC / NTC (School)'},
  {board: 'NABTEB', exam_type: 'Private/GCE', label: 'NABTEB — NBC / NTC (Private / GCE)'},
];
const rules = [{id: 1, programme: 'Computing demo', academic_session: 'Demo', minimum_jamb: 180, minimum_credits: 5, max_sittings: 2, allow_combining: true, active: true, revision: 1, required_subjects: subjects.slice(0, 3).map(subject => ({subject, minimum_grade: 'C6'}))}];
let currentUser;
beforeEach(() => {
  currentUser = {username: 'tester', is_staff: false};
  localStorage.clear();
  window.scrollTo = vi.fn();
  api.mockReset();
  api.mockImplementation(async (path, options) => {
    if (path === 'session') return {user: currentUser};
    if (path === 'catalogue') return {subjects, grades: ['A1', 'B2', 'B3', 'C4', 'C5', 'C6', 'D7', 'E8', 'F9', 'Awaiting'], boards: ['WAEC', 'NECO', 'NABTEB'], examinations};
    if (path === 'rules') return {rules};
    if (path === 'screen') return {student: {name: options.body.student_name, registration_number: options.body.registration_number}, rules: rules[0], sittings: options.body.sittings, jamb_score: options.body.jamb_score, status: 'Eligible', checks: [{label: 'JAMB score', status: 'passed', detail: '240; minimum 180.'}]};
    if (path === 'history') return {history: []};
    return {};
  });
});
afterEach(cleanup);

describe('manual screening workspace', () => {
  it('submits reviewed manual results and clears stale outcomes after edits', async () => {
    const user = userEvent.setup(); render(<App/>);
    await user.type(await screen.findByLabelText(/full name/), 'Test Applicant');
    await user.type(screen.getByLabelText('JAMB registration number'), 'TEST-001');
    await user.selectOptions(screen.getByLabelText('Programme & admission session'), '1');
    await user.type(screen.getByLabelText(/JAMB total score/), '240');
    await user.selectOptions(screen.getByLabelText('Sitting 1 subject 1'), 'English Language');
    await user.selectOptions(screen.getByLabelText('Sitting 1 grade 1'), 'B3');
    const examSelect = screen.getByLabelText('O’level examination');
    expect([...examSelect.options].filter(option => !option.disabled)).toHaveLength(7);
    await user.selectOptions(examSelect, 'NECO:Private/GCE');
    await user.click(screen.getByRole('checkbox', {name: /I have reviewed/}));
    await user.click(screen.getByRole('button', {name: 'Screen student →'}));
    expect(await screen.findByText('Eligible')).toBeInTheDocument();
    const call = api.mock.calls.find(([path]) => path === 'screen');
    expect(call[1].body).toMatchObject({jamb_score: 240, confirmed: true, save: false, rule_revision: 1});
    expect(call[1].body.sittings[0].subjects).toHaveLength(1);
    expect(call[1].body.sittings[0]).toMatchObject({board: 'NECO', exam_type: 'Private/GCE'});
    await user.type(screen.getByLabelText('Student’s full name'), ' Changed');
    expect(screen.queryByText('Eligible')).not.toBeInTheDocument();
    expect(screen.getByRole('checkbox', {name: /I have reviewed/})).not.toBeChecked();
  });

  it('lets staff save changed requirements', async () => {
    currentUser = {username: 'admin', is_staff: true};
    const user = userEvent.setup(); render(<App/>);
    await screen.findByLabelText('JAMB registration number');
    await user.click(screen.getByRole('button', {name: /Admission rules/}));
    window.scrollTo = vi.fn();
    await user.click(screen.getByRole('button', {name: /Edit rules/}));
    const threshold = screen.getByLabelText('Minimum JAMB score');
    await user.clear(threshold); await user.type(threshold, '220');
    await user.click(screen.getByRole('button', {name: 'Save admission rules'}));
    await waitFor(() => expect(api).toHaveBeenCalledWith('rules/1', expect.objectContaining({method: 'PUT', body: expect.objectContaining({minimum_jamb: 220, revision: 1})})));
    expect(await screen.findByText(/Admission rules saved/)).toBeInTheDocument();
  });

  it('shows connection errors and allows retry', async () => {
    api.mockRejectedValueOnce(new Error('Cannot reach the server.'));
    const user = userEvent.setup(); render(<App/>);
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the server.');
    await user.click(screen.getByRole('button', {name: 'Retry connection'}));
    expect(await screen.findByLabelText('JAMB registration number')).toBeInTheDocument();
  });
});


it('remembers sidebar collapse and keeps student input across navigation', async () => {
  const user = userEvent.setup(); const view = render(<App/>);
  await user.type(await screen.findByLabelText(/full name/), 'Test Applicant');
  await user.click(screen.getByRole('button', {name: 'Collapse sidebar'}));
  expect(screen.getByRole('button', {name: 'Expand sidebar'})).toHaveAttribute('aria-expanded', 'false');
  expect(localStorage.getItem('mapoly.sidebar.collapsed')).toBe('true');
  await user.click(screen.getByRole('button', {name: 'Admission rules'}));
  expect(screen.getByRole('button', {name: 'Admission rules'})).toHaveAttribute('aria-current', 'page');
  await user.click(screen.getByRole('button', {name: 'Screening'}));
  expect(screen.getByDisplayValue('Test Applicant')).toBeInTheDocument();
  view.unmount(); render(<App/>);
  expect(await screen.findByRole('button', {name: 'Expand sidebar'})).toBeInTheDocument();
  await user.click(screen.getByRole('button', {name: 'Expand sidebar'}));
  expect(localStorage.getItem('mapoly.sidebar.collapsed')).toBe('false');
});

it('requires sign-in before loading protected data or showing tools', async () => {
  currentUser=null; render(<App/>);
  expect(await screen.findByLabelText('Password')).toBeInTheDocument();
  expect(api.mock.calls.map(([path])=>path)).toEqual(['session']);
  expect(screen.queryByRole('button',{name:'Screening'})).not.toBeInTheDocument();
});
it('clears the workspace when the session expires', async () => {
  render(<App/>);
  await screen.findByLabelText('JAMB registration number');
  window.dispatchEvent(new Event('session-expired'));
  expect(await screen.findByLabelText('Password')).toBeInTheDocument();
  expect(screen.queryByLabelText('JAMB registration number')).not.toBeInTheDocument();
});

it('shows and hides the password without submitting or changing it', async () => {
  currentUser=null; const user=userEvent.setup(); render(<App/>);
  const input=await screen.findByLabelText('Password');
  await user.type(input,'example-password');
  expect(input).toHaveAttribute('type','password');
  await user.click(screen.getByRole('button',{name:'Show password'}));
  expect(input).toHaveAttribute('type','text');
  expect(input).toHaveValue('example-password');
  await user.click(screen.getByRole('button',{name:'Hide password'}));
  expect(input).toHaveAttribute('type','password');
  expect(api.mock.calls.some(([path])=>path==='login')).toBe(false);
});
