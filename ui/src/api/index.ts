import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface PortfolioSummary {
  cash: number;
  stock_value: number;
  total_assets: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_pct: number;
  updated_at: string;
}

export const getPortfolioSummary = async () => {
  const response = await api.get<PortfolioSummary>('/portfolio/summary');
  return response.data;
};

export const getHealth = async () => {
    const response = await api.get('/health');
    return response.data;
}

export default api;
