import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CriteriaDetails, { CriteriaEditor } from './CriteriaDetails';

afterEach(cleanup);
const group = {count: 1, options: [['Physics', 'Chemistry']]};
const criteria = {credit_paths: [[group]], pass_groups: [group], jamb_groups: [group],
  review_notes: ['Confirm the source wording.'], advisories: ['Drawing is an advantage.'],
  source_text: 'Original source text', source_row: 1, school: 'Engineering'};

it('shows source wording, alternatives and unresolved requirements', async () => {
  const user = userEvent.setup();
  render(<CriteriaDetails rule={{criteria, admission_type: 'ND Full-Time', academic_session: 'All sessions'}}/>);
  expect(screen.getByText('ND Full-Time')).toBeInTheDocument();
  expect(screen.getByText('Confirm the source wording.')).toBeInTheDocument();
  await user.click(screen.getByText('Full subject requirements'));
  expect(screen.getByText('Additional passes (E8 or above)')).toBeVisible();
  expect(screen.getByText('Drawing is an advantage.')).toBeVisible();
  await user.click(screen.getByText(/Compendium source/));
  expect(screen.getByText('Original source text')).toBeVisible();
});

