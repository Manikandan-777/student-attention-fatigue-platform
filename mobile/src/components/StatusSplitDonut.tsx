import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Circle, G } from 'react-native-svg';
import { THEME } from '../theme';

interface StatusSplitDonutProps {
  total: number;
  attentive: number;
  distracted: number;
  fatigued: number;
}

export const StatusSplitDonut: React.FC<StatusSplitDonutProps> = ({
  total,
  attentive,
  distracted,
  fatigued,
}) => {
  const sum = total > 0 ? total : attentive + distracted + fatigued;
  const safeTotal = sum > 0 ? sum : 1;

  const pctAttentive = Math.round((attentive / safeTotal) * 100);
  const pctDistracted = Math.round((distracted / safeTotal) * 100);
  const pctFatigued = Math.max(0, 100 - pctAttentive - pctDistracted);

  // Donut geometry
  const size = 110;
  const strokeWidth = 14;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  // Arc lengths
  const lenAttentive = (attentive / safeTotal) * circumference;
  const lenDistracted = (distracted / safeTotal) * circumference;
  const lenFatigued = (fatigued / safeTotal) * circumference;

  const offsetAttentive = 0;
  const offsetDistracted = -lenAttentive;
  const offsetFatigued = -(lenAttentive + lenDistracted);

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Status Split (Current)</Text>

      <View style={styles.contentRow}>
        {/* Donut Chart */}
        <View style={styles.donutWrapper}>
          <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            <G rotation="-90" origin={`${size / 2}, ${size / 2}`}>
              {/* Background ring */}
              <Circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                stroke="#F1F5F9"
                strokeWidth={strokeWidth}
                fill="none"
              />
              {/* Attentive arc (Green) */}
              {attentive > 0 && (
                <Circle
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  stroke="#16A34A"
                  strokeWidth={strokeWidth}
                  strokeDasharray={`${lenAttentive} ${circumference}`}
                  strokeDashoffset={offsetAttentive}
                  fill="none"
                  strokeLinecap="round"
                />
              )}
              {/* Distracted arc (Yellow/Amber) */}
              {distracted > 0 && (
                <Circle
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  stroke="#F59E0B"
                  strokeWidth={strokeWidth}
                  strokeDasharray={`${lenDistracted} ${circumference}`}
                  strokeDashoffset={offsetDistracted}
                  fill="none"
                  strokeLinecap="round"
                />
              )}
              {/* Fatigued arc (Red) */}
              {fatigued > 0 && (
                <Circle
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  stroke="#EF4444"
                  strokeWidth={strokeWidth}
                  strokeDasharray={`${lenFatigued} ${circumference}`}
                  strokeDashoffset={offsetFatigued}
                  fill="none"
                  strokeLinecap="round"
                />
              )}
            </G>
          </Svg>

          {/* Center text inside donut */}
          <View style={styles.centerTextContainer}>
            <Text style={styles.centerNumber}>{sum}</Text>
            <Text style={styles.centerLabel}>Students</Text>
          </View>
        </View>

        {/* Legend */}
        <View style={styles.legendContainer}>
          <View style={styles.legendItem}>
            <View style={[styles.dot, { backgroundColor: '#16A34A' }]} />
            <Text style={styles.legendLabel}>Attentive</Text>
            <Text style={styles.legendValue}>
              {attentive} <Text style={styles.legendPct}>({pctAttentive}%)</Text>
            </Text>
          </View>

          <View style={styles.legendItem}>
            <View style={[styles.dot, { backgroundColor: '#F59E0B' }]} />
            <Text style={styles.legendLabel}>Distracted</Text>
            <Text style={styles.legendValue}>
              {distracted} <Text style={styles.legendPct}>({pctDistracted}%)</Text>
            </Text>
          </View>

          <View style={styles.legendItem}>
            <View style={[styles.dot, { backgroundColor: '#EF4444' }]} />
            <Text style={styles.legendLabel}>Fatigued</Text>
            <Text style={styles.legendValue}>
              {fatigued} <Text style={styles.legendPct}>({pctFatigued}%)</Text>
            </Text>
          </View>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 14,
    marginVertical: 8,
    borderWidth: 1,
    borderColor: '#F1F5F9',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 12,
  },
  contentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
  },
  donutWrapper: {
    position: 'relative',
    width: 110,
    height: 110,
    alignItems: 'center',
    justifyContent: 'center',
  },
  centerTextContainer: {
    position: 'absolute',
    alignItems: 'center',
    justifyContent: 'center',
  },
  centerNumber: {
    fontSize: 18,
    fontWeight: '800',
    color: '#0F172A',
    lineHeight: 22,
  },
  centerLabel: {
    fontSize: 9,
    color: '#64748B',
    fontWeight: '500',
  },
  legendContainer: {
    flex: 1,
    paddingLeft: 20,
    justifyContent: 'center',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 4,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  legendLabel: {
    fontSize: 12,
    color: '#334155',
    fontWeight: '500',
    width: 68,
  },
  legendValue: {
    fontSize: 12,
    fontWeight: '700',
    color: '#0F172A',
  },
  legendPct: {
    fontWeight: '500',
    color: '#64748B',
    fontSize: 11,
  },
});
