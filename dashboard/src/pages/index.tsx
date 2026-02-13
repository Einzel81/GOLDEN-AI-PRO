// الصفحة الرئيسية
import React from 'react';
import { Layout } from '../components/Layout';
import { PriceChart } from '../components/PriceChart';
import { SignalCard } from '../components/SignalCard';
import { StatsCard } from '../components/StatsCard';

export default function Dashboard() {
  return (
    <Layout>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <PriceChart />
        </div>
        <div className="space-y-6">
          <SignalCard />
          <StatsCard />
        </div>
      </div>
    </Layout>
  );
}
