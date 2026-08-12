/**
 * The panel that renders what cycle A returned and nobody displayed.
 *
 * These are render assertions rather than truth tables because the failure is
 * a rendering one: the data was present, correct, and invisible. What matters
 * is that the outstanding work is on screen without being asked for, and that
 * the 22 correct renames are not.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { aMapping } from '../../test/builders';
import { MappingPanel } from './MappingPanel';

describe('MappingPanel', () => {
  it('renders nothing when no profile was applied', () => {
    const { container } = render(<MappingPanel mapping={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows unmapped columns without being asked', () => {
    render(<MappingPanel mapping={aMapping({ unmapped: ['ملاحظات', 'Column14'] })} />);

    expect(screen.getByTestId('unmapped-columns')).toBeInTheDocument();
    expect(screen.getByText('ملاحظات')).toBeInTheDocument();
    expect(screen.getByText(/2 columns have no decision/)).toBeInTheDocument();
  });

  it('shows the client their own words and the options to choose from', () => {
    render(<MappingPanel mapping={aMapping({
      unmapped_values: { status: ['معلق', 'منتهي'] },
    })} />);

    const task = screen.getByTestId('unmapped-values-status');
    expect(task).toHaveTextContent('معلق, منتهي');
    expect(task).toHaveTextContent('Active, Inactive, Terminated, On Leave');
  });

  it('states what the value mapping decides, beside the choice', () => {
    // The affirmation is worth nothing if it does not say what is affirmed.
    render(<MappingPanel mapping={aMapping({
      unmapped_values: { status: ['معلق'] },
      reject_enum_consequences: { status: 'Status decides who is counted as employed.' },
    })} />);

    expect(screen.getByTestId('unmapped-values-status'))
      .toHaveTextContent('Status decides who is counted as employed.');
  });

  it('keeps the 22 correct renames collapsed', async () => {
    render(<MappingPanel mapping={aMapping({
      renamed: { 'الرقم الوظيفي': 'employee_id', 'الجنسيه': 'nationality' },
    })} />);

    expect(screen.queryByText('employee_id')).not.toBeInTheDocument();
    await userEvent.click(screen.getByText(/2 renamed/));
    expect(screen.getByText('employee_id')).toBeInTheDocument();
  });

  it('warns about a changed export rather than re-mapping it', async () => {
    render(<MappingPanel mapping={aMapping({ header_changed: true })} />);

    expect(screen.getByTestId('header-changed'))
      .toHaveTextContent(/Nothing was re-mapped automatically/);
  });

  it('says so plainly when nothing is outstanding', () => {
    render(<MappingPanel mapping={aMapping()} />);

    expect(screen.getByText(/Every column has a decision/)).toBeInTheDocument();
    expect(screen.queryByTestId('open-mapping')).not.toBeInTheDocument();
  });

  it('offers the way out, with the column that was clicked', async () => {
    const onFix = vi.fn();
    render(<MappingPanel mapping={aMapping({ unmapped: ['ملاحظات'] })} onFix={onFix} />);

    await userEvent.click(screen.getByText('ملاحظات'));
    expect(onFix).toHaveBeenCalledWith('ملاحظات');
  });
});
