import React, { useEffect, useState } from 'react';
import { getPortfolioSummary, PortfolioSummary, getHealth } from '@/api';
import { TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react';

const Dashboard = () => {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [summaryData, healthData] = await Promise.all([
          getPortfolioSummary(),
          getHealth()
        ]);
        setSummary(summaryData);
        setHealth(healthData);
      } catch (error) {
        console.error('Failed to fetch data', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="p-4">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Assets"
          value={`$${summary?.total_assets.toLocaleString()}`}
          icon={<DollarSign className="text-green-500" />}
          trend={summary?.total_pnl_pct}
        />
        <StatCard
          title="Total P&L"
          value={`$${summary?.total_pnl.toLocaleString()}`}
          icon={summary?.total_pnl && summary.total_pnl >= 0 ? <TrendingUp className="text-green-500" /> : <TrendingDown className="text-red-500" />}
          className={summary?.total_pnl && summary.total_pnl >= 0 ? "text-green-600" : "text-red-600"}
        />
        <StatCard
          title="Stock Value"
          value={`$${summary?.stock_value.toLocaleString()}`}
          icon={<Activity className="text-blue-500" />}
        />
        <StatCard
          title="Cash Balance"
          value={`$${summary?.cash.toLocaleString()}`}
          icon={<DollarSign className="text-gray-500" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card p-6 rounded-xl border shadow-sm">
           <h3 className="font-semibold mb-4">System Status</h3>
           <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">API Status:</span>
                <span className="text-green-500 font-medium">{health?.status || 'Unknown'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Watchlist:</span>
                <span>{health?.watchlist_count || 0} items</span>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ title, value, icon, trend, className }: any) => (
  <div className="bg-card p-6 rounded-xl border shadow-sm">
    <div className="flex justify-between items-start mb-2">
      <span className="text-sm font-medium text-muted-foreground">{title}</span>
      <div className="p-2 bg-secondary/50 rounded-lg">{icon}</div>
    </div>
    <div className={`text-2xl font-bold ${className}`}>{value}</div>
    {trend !== undefined && (
      <div className={`text-sm mt-1 ${trend >= 0 ? 'text-green-500' : 'text-red-500'}`}>
        {trend >= 0 ? '+' : ''}{trend}%
      </div>
    )}
  </div>
);

export default Dashboard;
