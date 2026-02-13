// خدمة API
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
});

export const getAccountInfo = () => api.get('/api/v1/account');
export const getPositions = () => api.get('/api/v1/positions');
export const executeTrade = (data: any) => api.post('/api/v1/trade', data);
export const analyzeMarket = (timeframe: string) => 
  api.post('/api/v1/analyze', null, { params: { timeframe } });
