import { create } from 'zustand';
import { UserProfile, getUserProfiles, getUserProfile, createUserProfile, updateUserProfile, deleteUserProfile, bulkDeleteUserProfile } from '../services/user_profile';

interface UserProfileState {
    data: UserProfile[];
    total: number;
    page: number;
    size: number;
    loading: boolean;
    currentItem: UserProfile | null;
    filters: Record<string, any>;
    fetchData: (page?: number, size?: number, filters?: Record<string, any>) => Promise<void>;
    refreshData: (page?: number, size?: number, filters?: Record<string, any>) => Promise<void>;
    fetchItem: (id: number) => Promise<UserProfile | null>;
    createItem: (item: any) => Promise<void>;
    updateItem: (id: number, item: any) => Promise<void>;
    deleteItem: (id: number) => Promise<void>;
    bulkDeleteItem: (ids: number[]) => Promise<void>;
}

export const useUserProfileStore = create<UserProfileState>((set, get) => ({
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
            const result = await getUserProfiles(page, size, f);
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
            const result = await getUserProfiles(currentPage, currentSize, f);
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
            const result = await getUserProfile(id);
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
            await createUserProfile(item);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
    updateItem: async (id: number, item: any) => {
        try {
            await updateUserProfile(id, item);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
    deleteItem: async (id: number) => {
        try {
            await deleteUserProfile(id);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
    bulkDeleteItem: async (ids: number[]) => {
        try {
            await bulkDeleteUserProfile(ids);
            const { page, size, filters } = get();
            await get().fetchData(page, size, filters);
        } catch (error) {
            console.error(error);
            throw error;
        }
    },
}));