import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Workforce } from './Workforce';
import * as api from '../lib/api';
import { aSuppression } from '../test/builders';

/**
 * `null` is not `[]`, on the client.
 *
 * The ruling is enforced server-side: a suppressed payload is `null`, never an
 * empty array. This is the one test that checks a PAGE honours the distinction
 * end to end — the last place it can collapse.
 *
 * The failure it guards against is quiet: a page written with `data ?? []`
 * typechecks, looks correct on demo data (where nothing is ever suppressed),
 * and renders an empty chart in production. An empty chart is a claim that the
 * period had no events.
 *
 * Workforce is used because it is the smallest page with both shapes.
 */

vi.mock('../lib/api');

const KPIS = [
  { key: 'active_headcount', label: 'Active Headcount', value: 19,
    unit: 'employees', status: 'healthy' as const },
];

const TRENDS = { months: ['2026-06'], headcount_trend: [19], suppressed: [] };
const DISTRIBUTION = {
  department: { labels: ['Ops'], values: [19] },
  project: { labels: [], values: [] },
  nationality_group: { labels: [], values: [] },
  employment_type: { labels: [], values: [] },
  status: { labels: [], values: [] },
  suppressed: [],
};
const EXPIRY = {
  expired: 0, '0_30': 0, '31_60': 0, '61_90': 0, '90_plus': 0, missing_date: 0,
  suppressed: [],
};

function mockAll(over: Record<string, unknown> = {}) {
  const defaults: Record<string, unknown> = {
    fetchWorkforceSummary: { report_month: '2026-06', kpis: KPIS, suppressed: [] },
    fetchWorkforceTrends: TRENDS,
    fetchWorkforceDistribution: DISTRIBUTION,
    fetchWorkforceContractExpiry: EXPIRY,
    fetchWorkforceIqamaExpiry: EXPIRY,
    fetchWorkforceExceptions: { exceptions: [], suppressed: [] },
  };
  const mocked = api as unknown as Record<string, ReturnType<typeof vi.fn>>;
  for (const [name, value] of Object.entries({ ...defaults, ...over })) {
    mocked[name].mockResolvedValue(value);
  }
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('a page given null renders NotProvided', () => {
  it('a suppressed KPI strip is not an empty page', async () => {
    mockAll({
      fetchWorkforceSummary: {
        report_month: '2026-06',
        kpis: null,
        suppressed: [aSuppression({ key: 'active_headcount',
                                    mart: 'mart_workforce_kpis',
                                    missing_domains: ['employees'],
                                    message_en: 'Not yet provided: Employees.' })],
      },
    });
    render(<Workforce />);
    expect(await screen.findByTestId('not-provided')).toBeInTheDocument();
    expect(screen.getByText(/needs Employees/)).toBeInTheDocument();
  });

  it('a suppressed trend series suppresses the page it belongs to', async () => {
    mockAll({
      fetchWorkforceTrends: { months: null, headcount_trend: null,
                              suppressed: [aSuppression()] },
    });
    render(<Workforce />);
    expect(await screen.findByTestId('not-provided')).toBeInTheDocument();
  });
});

describe('a page given [] does NOT render NotProvided', () => {
  it('an empty-but-present series is real data and renders as the page', async () => {
    // This is the assertion that makes the null test meaningful. If a page
    // treated [] and null alike, both tests would pass and the distinction
    // would be gone.
    mockAll({
      fetchWorkforceTrends: { months: [], headcount_trend: [], suppressed: [] },
    });
    render(<Workforce />);
    await waitFor(() => {
      expect(screen.getByText('Primary Workforce Indicators')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('not-provided')).not.toBeInTheDocument();
  });

  it('a fully populated page renders its KPIs', async () => {
    mockAll();
    render(<Workforce />);
    await waitFor(() => {
      expect(screen.getByText('Active Headcount')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('not-provided')).not.toBeInTheDocument();
  });
});

describe('the coverage note is a sibling, not a suppression', () => {
  it('a partially covered page still renders its data, with the note', async () => {
    mockAll({
      fetchWorkforceSummary: {
        report_month: '2026-06',
        kpis: KPIS,
        suppressed: [],
        coverage_notes: [{
          domain: 'attendance', domain_label_en: 'Attendance',
          domain_label_ar: 'الحضور',
          declared_start: '2026-08-01', declared_end: '2026-08-07',
          covered_days: 6, expected_days: 27, coverage_pct: 22.2,
          message_en: 'Covers 6 of 27 working days (2026-08-01 to 2026-08-07).',
          message_ar: 'يغطي 6 من 27 يوم عمل.',
        }],
      },
    });
    render(<Workforce />);
    // present AND qualified - the whole reason coverage is not a suppression
    expect(await screen.findByTestId('coverage-banner')).toBeInTheDocument();
    expect(screen.getByText('Active Headcount')).toBeInTheDocument();
    expect(screen.queryByTestId('not-provided')).not.toBeInTheDocument();
  });
});
