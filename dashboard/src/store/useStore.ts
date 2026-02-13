// Zustand store
import { create } from 'zustand';

interface Store {
  balance: number;
  equity: number;
  positions: any[];
  setBalance: (balance: number) => void;
  setPositions: (positions: any[]) => void;
}

export const useStore = create<Store>((set) => ({
  balance: 0,
  equity: 0,
  positions: [],
  setBalance: (balance) => set({ balance }),
  setPositions: (positions) => set({ positions }),
}));
