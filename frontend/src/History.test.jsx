import React from 'react';
import {render, screen, cleanup, waitFor, fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach, beforeEach, it, expect, vi} from 'vitest';
import History from './History';
import {api} from './api';
vi.mock('./api', () => ({api: vi.fn()}));
const record = {id: 1, student: {name: 'Saved Student'}, rules: {programme: 'Computing'}, status: 'Eligible', created_at: '2026-09-20T00:00:00Z'};
beforeEach(() => {
  api.mockReset();
  api.mockImplementation(async (_, options) => ({history: [record], count: 125, page: Number(options.query.page), num_pages: 3}));
  HTMLDialogElement.prototype.showModal = function () {this.setAttribute('open', '');};
  HTMLDialogElement.prototype.close = function () {this.removeAttribute('open');};
});
afterEach(cleanup);
const mount = () => render(<History user={{username:'staff'}} onLogin={vi.fn()} renderResult={() => <p>Detailed requirement checks</p>}/>);

it('requests pages and searches all history starting at page one', async () => {
  const user = userEvent.setup(); mount();
  await screen.findByText('Page 1 of 3');
  expect(screen.getByRole('button', {name:'Previous page'})).toBeDisabled();
  await user.click(screen.getByRole('button', {name:'Next page'}));
  await screen.findByText('Page 2 of 3');
  await user.type(screen.getByLabelText('Search screenings'), 'Older Student');
  await user.click(screen.getByRole('button', {name:'Search', exact:true}));
  await waitFor(() => expect(api).toHaveBeenLastCalledWith('history', {query:{page:1,q:'Older Student'}}));
});

it('opens a modal and restores focus when closed or cancelled', async () => {
  const user = userEvent.setup(); mount();
  const row = await screen.findByRole('button', {name:/Saved Student/});
  await user.click(row);
  expect(screen.getByRole('dialog', {name:'Saved screening #1'})).toHaveTextContent('Detailed requirement checks');
  expect(document.body.style.overflow).toBe('hidden');
  await user.click(screen.getByRole('button', {name:'Close details'}));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(row).toHaveFocus();
  await user.click(row);
  fireEvent(screen.getByRole('dialog'), new Event('cancel', {bubbles:true,cancelable:true}));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(document.body.style.overflow).toBe('');
});
