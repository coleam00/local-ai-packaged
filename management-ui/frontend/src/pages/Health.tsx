import { useEffect, useState, useMemo } from 'react';
import { Activity, RefreshCw, Bell } from 'lucide-react';
import { Card } from '../components/common/Card';
import { MetricsCard, MetricsChart, HealthAlerts, DiagnosticsPanel } from '../components/health';
import { useMetricsStream } from '../hooks/useMetricsStream';
import { useMetricsStore } from '../store/metricsStore';
import { useServicesStore } from '../store/servicesStore';

export const Health: React.FC = () => {
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const { restartService, actionInProgress } = useServicesStore();

  const {
    currentMetrics: streamMetrics,
    metricsHistory,
    isConnected,
    error: streamError,
  } = useMetricsStream({ enabled: true, interval: 2, historySize: 60 });

  const {
    alerts,
    diagnostics,
    history,
    fetchAlerts,
    fetchDiagnostics,
    fetchHistory,
    acknowledgeAlert,
  } = useMetricsStore();

  // Fetch alerts on mount and periodically
  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  // Fetch diagnostics and history when service is selected
  useEffect(() => {
    if (selectedService) {
      fetchDiagnostics(selectedService);
      fetchHistory(selectedService, 24);
    }
  }, [selectedService, fetchDiagnostics, fetchHistory]);

  const servicesList = useMemo(() => {
    return Object.keys(streamMetrics).sort();
  }, [streamMetrics]);

  const selectedHistory = selectedService ? metricsHistory[selectedService] || [] : [];
  const selectedDiagnostics = selectedService ? diagnostics[selectedService] : null;
  const selectedFullHistory = selectedService ? history[selectedService] : null;

  const handleRefreshDiagnostics = () => {
    if (selectedService) {
      fetchDiagnostics(selectedService);
    }
  };

  const handleRestart = async () => {
    if (selectedService) {
      await restartService(selectedService);
      // Refresh diagnostics after restart
      setTimeout(() => fetchDiagnostics(selectedService), 2000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Activity className="w-7 h-7 text-emerald-400" />
            Health Dashboard
          </h2>
          <p className="text-slate-400 mt-1">
            Real-time monitoring and diagnostics
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Connection Status */}
          <div className="flex items-center gap-2 px-3 py-1 bg-[#1e293b] rounded-lg border border-[#374151]">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-sm text-slate-400">
              {isConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
          {/* Alerts Badge */}
          {alerts.length > 0 && (
            <div className="flex items-center gap-2 px-3 py-1 bg-red-900/20 rounded-lg border border-red-700/30">
              <Bell className="w-4 h-4 text-red-400" />
              <span className="text-sm text-red-400">{alerts.length} alerts</span>
            </div>
          )}
        </div>
      </div>

      {streamError && (
        <div className="flex items-center gap-3 p-4 bg-red-900/20 border border-red-700/30 rounded-lg">
          <span className="text-red-400">{streamError}</span>
        </div>
      )}

      {/* Alerts Section */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-3">Active Alerts</h3>
        <HealthAlerts
          alerts={alerts}
          onAcknowledge={acknowledgeAlert}
        />
      </div>

      {/* Metrics Grid */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-3">Service Metrics</h3>
        {servicesList.length === 0 ? (
          <Card>
            <div className="flex items-center justify-center py-8 text-slate-400">
              <RefreshCw className="w-5 h-5 animate-spin mr-2" />
              Waiting for metrics...
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {servicesList.map((name) => (
              <MetricsCard
                key={name}
                metrics={streamMetrics[name]}
                onClick={() => setSelectedService(name === selectedService ? null : name)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Selected Service Details */}
      {selectedService && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Real-time Chart */}
          <div>
            <h3 className="text-lg font-semibold text-white mb-3">
              {selectedService} - Real-time (Last 2 min)
            </h3>
            <MetricsChart
              data={selectedHistory}
              showCpu
              showMemory
              height={250}
            />
          </div>

          {/* Diagnostics */}
          <DiagnosticsPanel
            diagnostics={selectedDiagnostics || null}
            isLoading={false}
            onRefresh={handleRefreshDiagnostics}
            onRestart={handleRestart}
            isRestartInProgress={actionInProgress === selectedService}
          />
        </div>
      )}

      {/* Historical Chart */}
      {selectedService && selectedFullHistory && selectedFullHistory.data_points.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-white mb-3">
            {selectedService} - 24 Hour History
          </h3>
          <MetricsChart
            data={selectedFullHistory.data_points}
            title="CPU & Memory Usage"
            showCpu
            showMemory
            height={300}
          />
        </div>
      )}
    </div>
  );
};
