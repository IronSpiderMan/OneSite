import { create } from 'zustand';

import { getOpsDashboardData, type CustomFeatureData } from '../services/ops_dashboard';

type OpsDashboardState = {
  data: CustomFeatureData | null;
  loading: boolean;
  error: string | null;
  load: () => Promise<void>;
};

export const useOpsDashboardStore = create<OpsDashboardState>((set, get) => ({
  data: null,
  loading: false,
  error: null,
  load: async () => {
    if (get().loading) return;
    set({ loading: true, error: null });
    try {
      set({ data: await getOpsDashboardData(), loading: false });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'Unable to load custom feature',
      });
    }
  },
}));