import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Path, Defs, LinearGradient, Stop, Line } from 'react-native-svg';
import { THEME } from '../theme';

interface DataPoint {
  ts: string;
  value: number;
}

interface TrendLineChartProps {
  title: string;
  subtitle?: string;
  data: DataPoint[];
  color?: string; // 'blue' | 'red'
  isLive?: boolean;
}

export const TrendLineChart: React.FC<TrendLineChartProps> = ({
  title,
  subtitle = '(Last 5 minutes)',
  data,
  color = 'blue',
  isLive = true,
}) => {
  const chartHeight = 110;
  const chartWidth = 270;
  const paddingLeft = 30;
  const paddingBottom = 22;
  const paddingTop = 8;
  const innerHeight = chartHeight - paddingTop - paddingBottom;
  const innerWidth = chartWidth - paddingLeft - 8;

  const isBlue = color === 'blue';
  const strokeColor = isBlue ? '#3B82F6' : '#EF4444';
  const gradId = isBlue ? 'blueGrad' : 'redGrad';

  // Ensure at least 6 points for a rich curve
  const points = data && data.length > 0 ? data : [
    { ts: '10:10', value: isBlue ? 45 : 30 },
    { ts: '10:11', value: isBlue ? 65 : 48 },
    { ts: '10:12', value: isBlue ? 55 : 42 },
    { ts: '10:13', value: isBlue ? 75 : 62 },
    { ts: '10:14', value: isBlue ? 68 : 55 },
    { ts: '10:15', value: isBlue ? 78 : 68 },
  ];

  // Map points to SVG coordinates
  const minVal = 0;
  const maxVal = 100;

  const coords = points.map((p, idx) => {
    const x = paddingLeft + (idx / Math.max(1, points.length - 1)) * innerWidth;
    const clamped = Math.max(minVal, Math.min(maxVal, p.value));
    const y = paddingTop + innerHeight - (clamped / 100) * innerHeight;
    return { x, y, ts: p.ts };
  });

  // Construct SVG Path
  let pathD = '';
  if (coords.length > 0) {
    pathD = `M ${coords[0].x} ${coords[0].y}`;
    for (let i = 1; i < coords.length; i++) {
      pathD += ` L ${coords[i].x} ${coords[i].y}`;
    }
  }

  const fillD = coords.length > 0
    ? `${pathD} L ${coords[coords.length - 1].x} ${paddingTop + innerHeight} L ${coords[0].x} ${paddingTop + innerHeight} Z`
    : '';

  // Y-axis labels: 100, 75, 50, 25, 0
  const yTicks = [100, 75, 50, 25, 0];

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.subtitle}>{subtitle}</Text>
        </View>
        {isLive && (
          <View style={styles.liveBadge}>
            <Text style={styles.liveDot}>●</Text>
            <Text style={styles.liveText}>Live</Text>
          </View>
        )}
      </View>

      <View style={styles.chartContainer}>
        <Svg width="100%" height={chartHeight} viewBox={`0 0 ${chartWidth} ${chartHeight}`}>
          <Defs>
            <LinearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0%" stopColor={strokeColor} stopOpacity="0.28" />
              <Stop offset="100%" stopColor={strokeColor} stopOpacity="0.01" />
            </LinearGradient>
          </Defs>

          {/* Grid lines */}
          {yTicks.map((tick) => {
            const y = paddingTop + innerHeight - (tick / 100) * innerHeight;
            return (
              <Line
                key={tick}
                x1={paddingLeft}
                y1={y}
                x2={paddingLeft + innerWidth}
                y2={y}
                stroke="#F1F5F9"
                strokeWidth={1}
              />
            );
          })}

          {/* Fill under line */}
          {fillD ? <Path d={fillD} fill={`url(#${gradId})`} /> : null}

          {/* Trend line */}
          {pathD ? (
            <Path
              d={pathD}
              fill="none"
              stroke={strokeColor}
              strokeWidth={2.4}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ) : null}
        </Svg>

        {/* Y Axis Labels */}
        <View style={styles.yAxisLabels}>
          {yTicks.map((tick) => (
            <Text key={tick} style={styles.axisLabel}>
              {tick}
            </Text>
          ))}
        </View>

        {/* X Axis Labels */}
        <View style={styles.xAxisLabels}>
          {coords.map((c, i) => (
            <Text key={i} style={styles.xLabel}>
              {c.ts}
            </Text>
          ))}
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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F172A',
  },
  subtitle: {
    fontSize: 11,
    color: '#64748B',
    marginTop: 1,
  },
  liveBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#DCFCE7',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
  },
  liveDot: {
    color: '#15803D',
    fontSize: 9,
    marginRight: 3,
  },
  liveText: {
    color: '#15803D',
    fontSize: 10,
    fontWeight: '700',
  },
  chartContainer: {
    position: 'relative',
    marginTop: 2,
  },
  yAxisLabels: {
    position: 'absolute',
    left: 0,
    top: 6,
    height: 82,
    justifyContent: 'space-between',
  },
  axisLabel: {
    fontSize: 9,
    color: '#94A3B8',
    lineHeight: 10,
  },
  xAxisLabels: {
    position: 'absolute',
    bottom: 2,
    left: 30,
    right: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  xLabel: {
    fontSize: 8.5,
    color: '#94A3B8',
  },
});
