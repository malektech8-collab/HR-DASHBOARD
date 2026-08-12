import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { CoverageNote } from './CoverageNote';
import { NotProvided } from './NotProvided';
import { KpiCard } from '../cards/KpiCard';
import { aCoverageItem, aSuppression } from '../../test/builders';

/**
 * Suppression rendering.
 *
 * The ruling `a suppressed payload is null, NEVER []` is enforced server-side.
 * These assert the CLIENT honours the distinction rather than collapsing it —
 * a component that renders `data ?? []` turns a suppression into "no events",
 * which is the exact claim the ruling exists to prevent, and it would pass a
 * typecheck and look fine on demo data.
 */

describe('NotProvided', () => {
  it('names the missing domain rather than showing an empty panel', () => {
    render(<NotProvided title="Attendance" items={[aSuppression()]} />);
    expect(screen.getByTestId('not-provided')).toBeInTheDocument();
    expect(screen.getByText(/Attendance needs Attendance/)).toBeInTheDocument();
    expect(screen.getByText(/not yet provided/)).toBeInTheDocument();
  });

  it('says nothing is estimated while the data is missing', () => {
    render(<NotProvided title="Payroll" items={[aSuppression({
      missing_domains: ['payroll'], message_en: 'Not yet provided: Payroll.' })]} />);
    expect(screen.getByText(/Nothing here is estimated or defaulted/)).toBeInTheDocument();
  });

  it('lists the withheld figures by name', () => {
    render(<NotProvided title="Attendance" items={[
      aSuppression({ key: 'absence_days' }),
      aSuppression({ key: 'late_minutes', mart: 'mart_attendance_kpis' }),
    ]} />);
    expect(screen.getByText('2 withheld figures')).toBeInTheDocument();
    expect(screen.getByText('absence_days')).toBeInTheDocument();
  });

  it('an unmapped figure explains itself differently', () => {
    render(<NotProvided title="WPS" items={[aSuppression({
      reason: 'not_mapped', missing_domains: [] })]} />);
    expect(screen.getByText(/no declared data source/)).toBeInTheDocument();
  });
});

describe('CoverageNote', () => {
  it('renders the day counts and the declared window', () => {
    render(<CoverageNote items={[aCoverageItem()]} />);
    expect(screen.getByTestId('coverage-banner')).toBeInTheDocument();
    expect(screen.getByText(/6 of 27 working days/)).toBeInTheDocument();
    expect(screen.getByText(/2026-08-01 to 2026-08-07/)).toBeInTheDocument();
  });

  it('says the figures are measured over those days only', () => {
    render(<CoverageNote items={[aCoverageItem()]} />);
    expect(screen.getByText(/measured over those days only/)).toBeInTheDocument();
  });

  it('renders NOTHING when there is no note — the noise rule', () => {
    // Full coverage sends an empty list. A banner here on every page would
    // train people to stop reading notes, which costs most on the one case
    // that needs an explanation.
    const { container } = render(<CoverageNote items={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('the caption variant is text beside the content, not a banner', () => {
    render(<CoverageNote items={[aCoverageItem()]} variant="caption" />);
    expect(screen.getByTestId('coverage-caption')).toBeInTheDocument();
    expect(screen.queryByTestId('coverage-banner')).not.toBeInTheDocument();
  });
});

describe('KpiCard — null is not zero', () => {
  it('an unmeasurable value renders an em dash, not a number', () => {
    render(<KpiCard label="Attendance Compliance" value={null} unit="%"
                    status="neutral" />);
    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  it('the em dash carries its reason', () => {
    // An em dash without one is indistinguishable from a bug, and a client who
    // thinks a number is broken asks for it to be "fixed".
    render(<KpiCard label="Attendance Compliance" value={null} unit="%"
                    status="neutral"
                    unmeasurableReason="Covers 0 of 27 working days." />);
    expect(screen.getByText('Covers 0 of 27 working days.')).toBeInTheDocument();
  });

  it('a REAL zero renders as zero', () => {
    // The opposite error, and the more dangerous one to get wrong: hiding a
    // measured zero behind the same dash used for "unknown".
    render(<KpiCard label="Absence Days" value={0} unit="days" status="healthy" />);
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.queryByText('—')).not.toBeInTheDocument();
  });

  it('a real value is unaffected', () => {
    render(<KpiCard label="Active Headcount" value={19} unit="employees"
                    status="healthy" />);
    expect(screen.getByText('19')).toBeInTheDocument();
  });
});
