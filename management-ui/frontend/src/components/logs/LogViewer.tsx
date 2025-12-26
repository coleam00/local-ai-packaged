import { useState, useEffect } from 'react';
import { Download, Trash2, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { useLogStream } from '../../hooks/useWebSocket';
import { LogStream } from './LogStream';
import { LogFilter } from './LogFilter';
import { Button } from '../common/Button';
import { servicesApi } from '../../api/services';
import type { ServiceInfo } from '../../types/service';

export const LogViewer: React.FC = () => {
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [availableServices, setAvailableServices] = useState<ServiceInfo[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [tail, setTail] = useState(100);
  const [isLoadingServices, setIsLoadingServices] = useState(true);

  const { logs, isConnected, error, clearLogs } = useLogStream({
    serviceName: selectedService,
    tail,
    enabled: !!selectedService,
  });

  // Fetch services on mount only - intentionally empty dependency array
  useEffect(() => {
    const fetchServices = async () => {
      setIsLoadingServices(true);
      try {
        const response = await servicesApi.list();
        const running = response.services.filter((s) => s.status === 'running');
        setAvailableServices(running);
        if (running.length > 0) {
          setSelectedService((current) => current ?? running[0].name);
        }
      } catch (e) {
        console.error('Failed to fetch services:', e);
      } finally {
        setIsLoadingServices(false);
      }
    };
    fetchServices();
  }, []);

  const handleDownload = () => {
    const content = logs.join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedService}-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleRefresh = () => {
    // Re-select the same service to trigger reconnection
    const current = selectedService;
    setSelectedService(null);
    setTimeout(() => setSelectedService(current), 100);
  };

  const matchCount = searchTerm
    ? logs.filter((l) => l.toLowerCase().includes(searchTerm.toLowerCase())).length
    : 0;

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap gap-4 items-center">
        {/* Service Selector */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-400">Service:</label>
          <select
            value={selectedService || ''}
            onChange={(e) => setSelectedService(e.target.value || null)}
            disabled={isLoadingServices}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[200px]"
          >
            <option value="" disabled>
              {isLoadingServices ? 'Loading...' : 'Select a service'}
            </option>
            {availableServices.map((svc) => (
              <option key={svc.name} value={svc.name}>
                {svc.name}
              </option>
            ))}
          </select>
        </div>

        {/* Tail Selector */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-400">Lines:</label>
          <select
            value={tail}
            onChange={(e) => setTail(Number(e.target.value))}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value={50}>Last 50</option>
            <option value={100}>Last 100</option>
            <option value={500}>Last 500</option>
            <option value={1000}>Last 1000</option>
          </select>
        </div>

        {/* Connection Status */}
        <div className="flex items-center gap-2 px-3 py-1 bg-gray-800 rounded-lg">
          {isConnected ? (
            <>
              <Wifi className="w-4 h-4 text-green-400" />
              <span className="text-sm text-green-400">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-red-400" />
              <span className="text-sm text-red-400">Disconnected</span>
            </>
          )}
        </div>

        <div className="flex-1" />

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={!selectedService}
            title="Reconnect"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearLogs}
            disabled={logs.length === 0}
            title="Clear logs"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleDownload}
            disabled={logs.length === 0}
          >
            <Download className="w-4 h-4 mr-2" />
            Download
          </Button>
        </div>
      </div>

      {/* Filter */}
      <LogFilter
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        autoScroll={autoScroll}
        onAutoScrollChange={setAutoScroll}
      />

      {/* Error Display */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <span className="text-red-400">{error}</span>
        </div>
      )}

      {/* Log Display */}
      <LogStream logs={logs} searchTerm={searchTerm} autoScroll={autoScroll} />

      {/* Status Bar */}
      <div className="flex justify-between text-sm text-gray-500">
        <span>{logs.length.toLocaleString()} lines</span>
        <span>
          {searchTerm && `${matchCount.toLocaleString()} matches`}
        </span>
      </div>
    </div>
  );
};
