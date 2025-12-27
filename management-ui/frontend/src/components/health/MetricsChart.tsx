import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { ContainerMetrics, MetricsSnapshot } from '../../types/metrics';

interface MetricsChartProps {
  data: ContainerMetrics[] | MetricsSnapshot[];
  title?: string;
  showCpu?: boolean;
  showMemory?: boolean;
  showNetwork?: boolean;
  height?: number;
}

export function MetricsChart({
  data,
  title,
  showCpu = true,
  showMemory = true,
  showNetwork = false,
  height = 200,
}: MetricsChartProps) {
  const chartData = useMemo(() => {
    return data.map((d) => {
      const timestamp = new Date(d.timestamp);
      const isSnapshot = 'cpu_avg' in d;

      return {
        time: timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        timestamp: timestamp.getTime(),
        cpu: isSnapshot ? (d as MetricsSnapshot).cpu_avg : (d as ContainerMetrics).cpu_percent,
        memory: isSnapshot ? (d as MetricsSnapshot).memory_avg : (d as ContainerMetrics).memory_percent,
        networkRx: isSnapshot
          ? (d as MetricsSnapshot).network_rx_rate_avg
          : (d as ContainerMetrics).network_rx_rate,
        networkTx: isSnapshot
          ? (d as MetricsSnapshot).network_tx_rate_avg
          : (d as ContainerMetrics).network_tx_rate,
      };
    });
  }, [data]);

  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-[#1e293b] rounded-lg border border-[#374151]"
        style={{ height }}
      >
        <span className="text-slate-500">No data available</span>
      </div>
    );
  }

  return (
    <div className="bg-[#1e293b] rounded-lg border border-[#374151] p-4">
      {title && <h4 className="text-sm font-medium text-white mb-3">{title}</h4>}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="time"
            stroke="#64748b"
            tick={{ fill: '#64748b', fontSize: 11 }}
          />
          <YAxis
            stroke="#64748b"
            tick={{ fill: '#64748b', fontSize: 11 }}
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #374151',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#fff' }}
          />
          <Legend />
          {showCpu && (
            <Line
              type="monotone"
              dataKey="cpu"
              name="CPU %"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          )}
          {showMemory && (
            <Line
              type="monotone"
              dataKey="memory"
              name="Memory %"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          )}
          {showNetwork && (
            <>
              <Line
                type="monotone"
                dataKey="networkRx"
                name="Network RX"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="networkTx"
                name="Network TX"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
