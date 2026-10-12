import React from 'react';
import {render, screen, cleanup, waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach, beforeEach, it, expect, vi} from 'vitest';
import OCRUpload from './OCRUpload';
import {api} from './api';
vi.mock('./api', () => ({api: vi.fn()}));
afterEach(cleanup);
const draft = {student_name: 'Synthetic Student', registration_number: 'DEMO-001', course: 'Computer Science', jamb_score: 245, sittings: []};
beforeEach(() => { api.mockReset(); api.mockImplementation(async (_, options) => options ? {page: Number(options.body.get('page')), page_count: 5, token: 'signed-page', text: 'Recognised text', preview: 'data:image/png;base64,cG5n', warnings: ['Review all fields.'], low_confidence_words: [], drafts: [draft, {...draft, student_name: 'Second Student'}]} : {available: true}); });

it('uploads multipart data and requires explicit review before applying a selected student', async () => {
  const onApply = vi.fn(); const user = userEvent.setup(); render(<OCRUpload onApply={onApply}/>);
  await user.upload(screen.getByLabelText('Result document'), new File(['sample'], 'result.pdf', {type: 'application/pdf'}));
  await user.click(screen.getByRole('button', {name: 'Extract text'}));
  expect(await screen.findByText('Review the extraction')).toBeInTheDocument();
  const call = api.mock.calls.find(([, options]) => options?.method === 'POST');
  expect(call[1].body).toBeInstanceOf(FormData);
  expect(screen.getByRole('button', {name: /Load draft for review/})).toBeDisabled();
  await user.selectOptions(screen.getByLabelText('Student draft'), '1');
  await user.click(screen.getByRole('checkbox', {name: /Replace the corresponding/}));
  await user.click(screen.getByRole('button', {name: /Load draft for review/}));
  expect(onApply).toHaveBeenCalledWith(expect.objectContaining({student_name: 'Second Student'}), 'complete');
});

it('shows OCR errors without applying or screening a record', async () => {
  const onApply = vi.fn(); const user = userEvent.setup(); render(<OCRUpload onApply={onApply}/>);
  await user.upload(screen.getByLabelText('Result document'), new File(['sample'], 'result.png', {type: 'image/png'}));
  api.mockRejectedValueOnce(new Error('OCR timed out'));
  await user.click(screen.getByRole('button', {name: 'Extract text'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('OCR timed out');
  expect(onApply).not.toHaveBeenCalled();
});


it('processes every PDF page from one selection and reports completion', async () => {
  const user = userEvent.setup(); render(<OCRUpload onApply={vi.fn()}/>);
  await user.upload(screen.getByLabelText('Result document'), new File(['sample'], 'register.pdf', {type: 'application/pdf'}));
  await user.click(screen.getByRole('button', {name: 'Extract text'}));
  expect(await screen.findByText('Finished 5 page(s).')).toBeInTheDocument();
  const calls = api.mock.calls.filter(([path, options]) => path === 'ocr' && options?.method === 'POST');
  expect(calls.map(([, options]) => options.body.get('page'))).toEqual(['1', '2', '3', '4', '5']);
  expect(screen.getByLabelText('Student draft').options).toHaveLength(10);
});

it('keeps completed pages and does not batch screen after a later page fails', async () => {
  const user = userEvent.setup(); render(<OCRUpload onApply={vi.fn()}/>);
  await user.upload(screen.getByLabelText('Result document'), new File(['sample'], 'register.pdf', {type: 'application/pdf'}));
  api.mockResolvedValueOnce({page: 1, page_count: 2, drafts: [draft], text: 'first page', warnings: [], low_confidence_words: [], preview: 'data:image/png;base64,cG5n'}).mockRejectedValueOnce(new Error('Second page timed out'));
  await user.click(screen.getByRole('button', {name: 'Extract text'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Second page timed out');
  expect(screen.getByLabelText('Student draft').options).toHaveLength(1);
  expect(api.mock.calls.some(([path]) => path === 'screen-batch')).toBe(false);
});


it('imports a CSV once and displays cells without an OCR confidence score', async () => {
  const user = userEvent.setup(); render(<OCRUpload onApply={vi.fn()}/>);
  await user.upload(screen.getByLabelText('Result document'), new File(['student_name\nSynthetic Student'], 'students.csv', {type:'text/csv'}));
  api.mockResolvedValueOnce({page:1,page_count:1,token:'signed-table',source_format:'csv',confidence:null,text:'student_name\nSynthetic Student',preview:null,warnings:[],low_confidence_words:[],drafts:[draft],table:{headers:['student_name'],rows:[['Synthetic Student']],count:1}});
  await user.click(screen.getByRole('button', {name:'Import records'}));
  expect(await screen.findByRole('table')).toHaveTextContent('Synthetic Student');
  expect(screen.getByText('Values imported directly from the spreadsheet.')).toBeInTheDocument();
  expect(screen.queryByText(/Recognition score:/)).not.toBeInTheDocument();
  expect(api.mock.calls.filter(([path,options])=>path === 'ocr' && options?.method==='POST')).toHaveLength(1);
});

it('includes the selected admission type in the import request', async () => {
  const user = userEvent.setup(); render(<OCRUpload onApply={vi.fn()}/>);
  await user.selectOptions(screen.getByLabelText('Admission type'), 'HND Part-Time');
  expect(screen.getByText(/No admission rules are configured for HND Part-Time/)).toBeInTheDocument();
  await user.upload(screen.getByLabelText('Result document'), new File(['sample'], 'result.png', {type: 'image/png'}));
  await user.click(screen.getByRole('button', {name: 'Extract text'}));
  await screen.findByText('Review the extraction');
  const call = api.mock.calls.find(([path, options]) => path === 'ocr' && options?.method === 'POST');
  expect(call[1].body.get('admission_type')).toBe('HND Part-Time');
});

it('defaults to strict names and sends the optional smart processing setting', async () => {
  const user=userEvent.setup();render(<OCRUpload onApply={vi.fn()}/>);
  const checkbox=screen.getByRole('checkbox',{name:/Smart processing/});
  expect(checkbox).not.toBeChecked();
  await user.click(checkbox);
  await user.upload(screen.getByLabelText('Result document'),new File(['sample'],'result.png',{type:'image/png'}));
  await user.click(screen.getByRole('button',{name:'Extract text'}));
  await screen.findByText('Review the extraction');
  const calls=api.mock.calls.filter(([path,options])=>path==='ocr' && options?.method==='POST');
  expect(calls.length).toBeGreaterThan(0);
  expect(calls.every(([,options])=>options.body.get('smart_processing')==='true')).toBe(true);
  await user.click(checkbox);
  expect(screen.queryByText('Review the extraction')).not.toBeInTheDocument();
});
