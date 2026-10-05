import React from 'react';
import { render } from '@testing-library/react-native';
import { AdvisoryBanner, getFatigueMessage } from '../components/AdvisoryBanner';
import { FatigueAdvisory } from '../types';

describe('AdvisoryBanner Component & Fatigue Thresholds (§6 & Check 8)', () => {
  it('Scenario 1: Fatigue threshold evaluation for 10, 24.9, 25, 49.9, 50, 74.9, 75, 100', () => {
    // Check 8 from Acceptance checklist
    expect(getFatigueMessage(10)).toEqual({
      level: 1,
      text: 'Continue with the class.',
    });
    expect(getFatigueMessage(24.9)).toEqual({
      level: 1,
      text: 'Continue with the class.',
    });
    expect(getFatigueMessage(25)).toEqual({
      level: 2,
      text: 'Make the session more interactive.',
    });
    expect(getFatigueMessage(49.9)).toEqual({
      level: 2,
      text: 'Make the session more interactive.',
    });
    expect(getFatigueMessage(50)).toEqual({
      level: 3,
      text: 'Do a short activity or give a short break.',
    });
    expect(getFatigueMessage(74.9)).toEqual({
      level: 3,
      text: 'Do a short activity or give a short break.',
    });
    expect(getFatigueMessage(75)).toEqual({
      level: 4,
      text: 'Most students show fatigue indicators. Consider continuing the class tomorrow.',
    });
    expect(getFatigueMessage(100)).toEqual({
      level: 4,
      text: 'Most students show fatigue indicators. Consider continuing the class tomorrow.',
    });
  });

  it('Scenario 2: renders Level 1 CONTINUE with correct percentage and message', async () => {
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 18.5,
      level: 1,
      code: 'CONTINUE',
      message: 'Continue with the class.',
      usable_tracks: 25,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText } = await render(<AdvisoryBanner advisory={adv} />);
    expect(getByText('Continue with the class.')).toBeTruthy();
    expect(getByText('Class fatigue score is 19%.')).toBeTruthy();
  });

  it('Scenario 3: renders Level 2 INTERACTIVE with correct percentage and message', async () => {
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 38.0,
      level: 2,
      code: 'INTERACTIVE',
      message: 'Make the session more interactive.',
      usable_tracks: 20,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText } = await render(<AdvisoryBanner advisory={adv} />);
    expect(getByText('Make the session more interactive.')).toBeTruthy();
    expect(getByText('Class fatigue score is 38%.')).toBeTruthy();
  });

  it('Scenario 4: renders Level 3 SHORT_BREAK with correct percentage and message', async () => {
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 62.0,
      level: 3,
      code: 'SHORT_BREAK',
      message: 'Do a short activity or give a short break.',
      usable_tracks: 22,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText } = await render(<AdvisoryBanner advisory={adv} />);
    expect(getByText('Do a short activity or give a short break.')).toBeTruthy();
    expect(getByText('Class fatigue score is 62%.')).toBeTruthy();
  });

  it('Scenario 5: renders Level 4 RESCHEDULE with correct percentage and message', async () => {
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 82.0,
      level: 4,
      code: 'RESCHEDULE',
      message: 'Most students show fatigue indicators. Consider continuing the class tomorrow.',
      usable_tracks: 18,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText } = await render(<AdvisoryBanner advisory={adv} />);
    expect(
      getByText('Most students show fatigue indicators. Consider continuing the class tomorrow.')
    ).toBeTruthy();
    expect(getByText('Class fatigue score is 82%.')).toBeTruthy();
  });

  it('Scenario 6: renders Not enough data when advisory is null', async () => {
    const { getByText } = await render(<AdvisoryBanner advisory={null} />);
    expect(getByText(/Not enough data/i)).toBeTruthy();
    expect(
      getByText('Observing classroom to compute fatigue advisory')
    ).toBeTruthy();
  });

  it('Scenario 7: renders disconnected state when offline', async () => {
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 40.0,
      level: 2,
      code: 'INTERACTIVE',
      message: 'Make the session more interactive.',
      usable_tracks: 20,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText } = await render(<AdvisoryBanner advisory={adv} isOffline={true} />);
    expect(getByText('Realtime telemetry disconnected')).toBeTruthy();
    expect(getByText('Showing latest available advisory')).toBeTruthy();
  });

  it('Scenario 8: verifies copy does not use diagnostic or stigmatizing terms (D8)', async () => {
    const forbidden = ['lazy', 'sick', 'sleeping', 'diagnosed', 'disorder'];
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 78.0,
      level: 4,
      code: 'RESCHEDULE',
      message: 'Most students show fatigue indicators. Consider continuing the class tomorrow.',
      usable_tracks: 25,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText } = await render(<AdvisoryBanner advisory={adv} />);
    const textNode = getByText(
      'Most students show fatigue indicators. Consider continuing the class tomorrow.'
    );
    for (const word of forbidden) {
      expect(textNode.props.children.toLowerCase()).not.toContain(word);
    }
  });
});
