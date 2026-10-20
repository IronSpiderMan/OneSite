import { create } from 'zustand';

import { getOperationsSnapshot, OperationsSnapshot } from '../services/operations';

type OperationsDashboardState = {
  data: OperationsSnapshot | null;
  loading: boolean;
  error: string | null;
  load: () => Promise<void>;
};

export const useOperationsDashboardStore = create<OperationsDashboardState>((set, get) => ({
  data: null,
  loading: false,
  error: null,
  load: async () => {
    if (get().loading || get().data) return;
    set({ loading: true, error: null });
    try {
      set({ data: await getOperationsSnapshot(), loading: false });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'Unable to load operations snapshot',
      });
    }
  },
}));
