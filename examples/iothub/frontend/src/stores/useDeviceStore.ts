import { create } from 'zustand';
import { Device, getDevices, getDevice, createDevice, updateDevice, deleteDevice, bulkDeleteDevice } from '../services/device';

interface DeviceState {
    data: Device[];
    total: number;
    page: number;
    size: number;
    loading: boolean;
    currentItem: Device | null;
    filters: Record<string, any>;
    fetchData: (page?: number, size?: number, filters?: Record<string, any>) => Promise<void>;
    fetchItem: (id: number) => Promise<Device | null>;
    createItem: (item: any) => Promise<void>;
    updateItem: (id: number, item: any) => Promise<void>;
    deleteItem: (id: number) => Promise<void>;
    bulkDeleteItem: (ids: number[]) => Promise<void>;
}

export const useDeviceStore = create<DeviceState>((set, get) => ({
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
            const result = await getDevices(page, size, f);
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
    fetchItem: async (id: number) => {
        set({ loading: true });
        try {
            const result = await getDevice(id);
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
            await createDevice(item);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
    updateItem: async (id: number, item: any) => {
        try {
            await updateDevice(id, item);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
    deleteItem: async (id: number) => {
        try {
            await deleteDevice(id);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
    bulkDeleteItem: async (ids: number[]) => {
        try {
            await bulkDeleteDevice(ids);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
}));