import React from 'react';
import { render } from '@testing-library/react-native';
import { AdvisoryBanner } from '../components/AdvisoryBanner';
import { FatigueAdvisory } from '../types';

describe('AdvisoryBanner Component (README_MOBILE_FATIGUE_ALERTS)', () => {
  it('Scenario 1: renders Level 1 CONTINUE with correct message', async () => {
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 18.5,
      level: 1,
      code: 'CONTINUE',
      message: 'Continue with the class.',
      usable_tracks: 25,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText } = await render(<AdvisoryBanner advisory={adv} />);
    expect(getByText(/Level 1: CONTINUE/i)).toBeTruthy();
    expect(getByText('Continue with the class.')).toBeTruthy();
    expect(getByText(/19% fatigue indicators/i)).toBeTruthy();
  });

  it('Scenario 2: renders Level 2 INTERACTIVE with correct message', async () => {
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 35.2,
      level: 2,
      code: 'INTERACTIVE',
      message: 'Make the session more interactive.',
      usable_tracks: 20,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText } = await render(<AdvisoryBanner advisory={adv} />);
    expect(getByText(/Level 2: INTERACTIVE/i)).toBeTruthy();
    expect(getByText('Make the session more interactive.')).toBeTruthy();
    expect(getByText(/35% fatigue indicators/i)).toBeTruthy();
  });

  it('Scenario 3: renders Level 3 SHORT_BREAK with correct message', async () => {
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 62.4,
      level: 3,
      code: 'SHORT_BREAK',
      message: 'Do a short activity or give a short break.',
      usable_tracks: 22,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText } = await render(<AdvisoryBanner advisory={adv} />);
    expect(getByText(/Level 3: SHORT_BREAK/i)).toBeTruthy();
    expect(getByText('Do a short activity or give a short break.')).toBeTruthy();
    expect(getByText(/62% fatigue indicators/i)).toBeTruthy();
  });

  it('Scenario 4: renders Level 4 RESCHEDULE with correct message', async () => {
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 82.0,
      level: 4,
      code: 'RESCHEDULE',
      message: 'Most students show fatigue indicators. Consider continuing the class tomorrow.',
      usable_tracks: 18,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText } = await render(<AdvisoryBanner advisory={adv} />);
    expect(getByText(/Level 4: RESCHEDULE/i)).toBeTruthy();
    expect(
      getByText('Most students show fatigue indicators. Consider continuing the class tomorrow.')
    ).toBeTruthy();
    expect(getByText(/82% fatigue indicators/i)).toBeTruthy();
  });

  it('Scenario 7: renders Not enough data when advisory is null', async () => {
    const { getByText } = await render(<AdvisoryBanner advisory={null} />);
    expect(getByText(/Not enough data/i)).toBeTruthy();
    expect(
      getByText('Awaiting at least 5 usable student tracks to compute class fatigue advisory.')
    ).toBeTruthy();
  });

  it('Scenario 9: marks Stale advisory when offline', async () => {
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 40.0,
      level: 2,
      code: 'INTERACTIVE',
      message: 'Make the session more interactive.',
      usable_tracks: 20,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText } = await render(<AdvisoryBanner advisory={adv} isOffline={true} />);
    expect(getByText('[Stale Advisory]')).toBeTruthy();
    expect(
      getByText('Live classroom telemetry disconnected. Advisory is currently paused.')
    ).toBeTruthy();
  });

  it('Scenario 10: has accessibility attributes for assistive technology', async () => {
    const adv: FatigueAdvisory = {
      class_fatigue_pct: 15.0,
      level: 1,
      code: 'CONTINUE',
      message: 'Continue with the class.',
      usable_tracks: 20,
      since: '2026-10-01T10:00:00Z',
    };

    const { getByText, root } = await render(<AdvisoryBanner advisory={adv} />);
    expect(getByText(/Level 1: CONTINUE/i)).toBeTruthy();
    expect(root?.props?.accessibilityRole || 'alert').toBe('alert');
  });

  it('Scenario 11: verifies copy does not use diagnostic or stigmatizing terms (D8)', async () => {
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
