import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { GovernanceWidget } from './GovernanceWidget';
import { useGovernanceStatus, useLoginMutation } from '../../hooks/useGovernance';

// Mock hook module
vi.mock('../../hooks/useGovernance', () => ({
  useGovernanceStatus: vi.fn(),
  useLoginMutation: vi.fn(),
}));

describe('GovernanceWidget Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders skeleton loader when in loading state', () => {
    // Arrange
    vi.mocked(useGovernanceStatus).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as any);

    vi.mocked(useLoginMutation).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any);

    // Act
    const { container } = render(<GovernanceWidget />);

    // Assert
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders Access Denied view when a 403 Forbidden error is returned', () => {
    // Arrange
    vi.mocked(useGovernanceStatus).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed with status 403'),
      refetch: vi.fn(),
    } as any);

    vi.mocked(useLoginMutation).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any);

    // Act
    render(<GovernanceWidget />);

    // Assert
    expect(screen.getByText('Access Denied (Fail Closed)')).toBeInTheDocument();
    expect(screen.getByText(/Your authenticated HR_ANALYST role does not possess permissions/)).toBeInTheDocument();
  });

  it('renders Gate 5 grid view when authorized data is loaded successfully', () => {
    // Arrange
    const mockData = {
      current_gate: 'Gate 5 - Final Review',
      current_status: 'Authorization Evidence Pending',
      evidence_status: 'Not Provided',
      synthetic_validation_status: 'Synthetic Validation Only',
      decision_recommendation: 'Hold',
      real_data_execution_approved: false,
      real_authorization_evidence_approved: false,
      load_scheduling_approved: false,
      go_no_go_meeting_held: false,
      stop_criteria_count: 22,
      last_completed_milestone: '3K',
      milestone_3i_status: 'Authorization Evidence Pending',
      milestone_3j_status: 'Planning Only',
      milestone_3k_status: 'Synthetic Validation Only',
    };

    vi.mocked(useGovernanceStatus).mockReturnValue({
      data: mockData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    vi.mocked(useLoginMutation).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as any);

    // Act
    render(<GovernanceWidget />);

    // Assert
    expect(screen.getByText('Hold')).toBeInTheDocument();
    expect(screen.getByText('Authorization Evidence Pending')).toBeInTheDocument();
    expect(screen.getByText('22 Registered')).toBeInTheDocument();
    expect(screen.getByText('3K')).toBeInTheDocument();
  });
});
