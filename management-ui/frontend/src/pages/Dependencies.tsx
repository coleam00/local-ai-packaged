import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitBranch, RefreshCw, AlertCircle, Box, Link2, Heart, Layers } from 'lucide-react';
import { DependencyGraph } from '../components/services/DependencyGraph';
import { useServicesStore } from '../store/servicesStore';
import { servicesApi } from '../api/services';
import type { DependencyGraph as DependencyGraphData } from '../api/services';
import { Loading } from '../components/common/Loading';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';

export const Dependencies: React.FC = () => {
  const navigate = useNavigate();
  const { services, fetchServices } = useServicesStore();
  const [graphData, setGraphData] = useState<DependencyGraphData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [graph] = await Promise.all([
          servicesApi.getDependencies(),
          fetchServices(),
        ]);
        setGraphData(graph);
      } catch (e: unknown) {
        const err = e as { message?: string };
        setError(err.message || 'Failed to load dependency graph');
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, [fetchServices]);

  const handleRefresh = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [graph] = await Promise.all([
        servicesApi.getDependencies(),
        fetchServices(),
      ]);
      setGraphData(graph);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err.message || 'Failed to load dependency graph');
    } finally {
      setIsLoading(false);
    }
  };

  const handleServiceClick = (serviceName: string) => {
    navigate(`/services?selected=${serviceName}`);
  };

  if (isLoading) {
    return <Loading message="Loading dependency graph..." />;
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <GitBranch className="w-7 h-7 text-gray-400" />
            Service Dependencies
          </h2>
        </div>
        <Card>
          <div className="flex items-center gap-3 text-red-400">
            <AlertCircle className="w-5 h-5" />
            <p>{error}</p>
          </div>
          <Button variant="secondary" onClick={handleRefresh} className="mt-4">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <GitBranch className="w-7 h-7 text-gray-400" />
            Service Dependencies
          </h2>
        </div>
        <Card>
          <p className="text-gray-400">No dependency data available</p>
        </Card>
      </div>
    );
  }

  const stats = {
    total: graphData.nodes.length,
    running: services.filter((s) => s.status === 'running').length,
    stopped: services.filter((s) => s.status === 'stopped' || s.status === 'not_created').length,
    dependencies: graphData.edges.length,
    healthyDeps: graphData.edges.filter((e) => e.data.condition === 'service_healthy').length,
    groups: new Set(graphData.nodes.map((n) => n.data.group)).size,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <GitBranch className="w-7 h-7 text-gray-400" />
            Service Dependencies
          </h2>
          <p className="text-gray-400 mt-1">
            Interactive visualization of service relationships and dependencies
          </p>
        </div>
        <Button
          variant="ghost"
          onClick={handleRefresh}
          disabled={isLoading}
          className="text-gray-400 hover:text-white"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <Card>
          <div className="flex items-center gap-3">
            <Box className="w-5 h-5 text-blue-400" />
            <div>
              <p className="text-xs text-gray-400">Services</p>
              <p className="text-xl font-bold text-white">{stats.total}</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <div>
              <p className="text-xs text-gray-400">Running</p>
              <p className="text-xl font-bold text-green-400">{stats.running}</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-gray-500" />
            <div>
              <p className="text-xs text-gray-400">Stopped</p>
              <p className="text-xl font-bold text-gray-400">{stats.stopped}</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <Link2 className="w-5 h-5 text-purple-400" />
            <div>
              <p className="text-xs text-gray-400">Dependencies</p>
              <p className="text-xl font-bold text-white">{stats.dependencies}</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <Heart className="w-5 h-5 text-pink-400" />
            <div>
              <p className="text-xs text-gray-400">Health Checks</p>
              <p className="text-xl font-bold text-white">{stats.healthyDeps}</p>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex items-center gap-3">
            <Layers className="w-5 h-5 text-yellow-400" />
            <div>
              <p className="text-xs text-gray-400">Groups</p>
              <p className="text-xl font-bold text-white">{stats.groups}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Graph */}
      <DependencyGraph
        graphData={graphData}
        services={services}
        onServiceClick={handleServiceClick}
      />

      {/* Help Text */}
      <div className="text-sm text-gray-500 space-y-1">
        <p>
          <strong className="text-gray-400">Tip:</strong> Click on a service node to manage it.
          Use the filter buttons to highlight specific groups. Scroll to zoom, drag to pan.
        </p>
        <p>
          Arrows point from a service to its dependencies. Green animated arrows indicate
          health-check dependencies.
        </p>
      </div>
    </div>
  );
};
