import { create } from 'zustand';
import { PremiumContent, getPremiumContents, getPremiumContent, createPremiumContent, updatePremiumContent, deletePremiumContent, bulkDeletePremiumContent } from '../services/premium_content';

interface PremiumContentState {
    data: PremiumContent[];
    total: number;
    page: number;
    size: number;
    loading: boolean;
    currentItem: PremiumContent | null;
    filters: Record<string, any>;
    fetchData: (page?: number, size?: number, filters?: Record<string, any>) => Promise<void>;
    refreshData: (page?: number, size?: number, filters?: Record<string, any>) => Promise<void>;
    fetchItem: (id: number) => Promise<PremiumContent | null>;
    createItem: (item: any) => Promise<void>;
    updateItem: (id: number, item: any) => Promise<void>;
    deleteItem: (id: number) => Promise<void>;
    bulkDeleteItem: (ids: number[]) => Promise<void>;
}

export const usePremiumContentStore = create<PremiumContentState>((set, get) => ({
    data: [],
    total: 0,
    page: 1,
    size: 20,
    loading: false,
    currentItem: null,
    filters: {},
    fetchData: async (page = 1, size = 20, filters?: Record<string, any>) => {
        set({ loading: true });
        try {
            const f = filters !== undefined ? filters : get().filters;
            const result = await getPremiumContents(page, size, f);
            if (result && Array.isArray(result.items)) {
                set({ 
                    data: result.items,
                    total: result.total,
                    page: result.page,
                    size: result.size,
                    filters: f
                });
            } else {
                console.error("Expected paginated response but got:", result);
                set({ data: [], total: 0 });
            }
        } catch (error) {
            console.error(error);
            set({ data: [], total: 0 });
        } finally {
            set({ loading: false });
        }
    },
    refreshData: async (page?: number, size?: number, filters?: Record<string, any>) => {
        try {
            const currentPage = page ?? get().page;
            const currentSize = size ?? get().size;
            const f = filters !== undefined ? filters : get().filters;
            const result = await getPremiumContents(currentPage, currentSize, f);
            if (result && Array.isArray(result.items)) {
                set({
                    data: result.items,
                    total: result.total,
                    page: result.page,
                    size: result.size,
                    filters: f
                });
            } else {
                console.error("Expected paginated response but got:", result);
            }
        } catch (error) {
            console.error(error);
        }
    },
    fetchItem: async (id: number) => {
        set({ loading: true });
        try {
            const result = await getPremiumContent(id);
            set({ currentItem: result });
            return result;
        } catch (error) {
            console.error(error);
            set({ currentItem: null });
            return null;
        } finally {
            set({ loading: false });
        }
    },
    createItem: async (item: any) => {
        try {
            await createPremiumContent(item);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
    updateItem: async (id: number, item: any) => {
        try {
            await updatePremiumContent(id, item);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
    deleteItem: async (id: number) => {
        try {
            await deletePremiumContent(id);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
    bulkDeleteItem: async (ids: number[]) => {
        try {
            await bulkDeletePremiumContent(ids);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
}));