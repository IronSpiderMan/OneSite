import { create } from 'zustand';

import { AdminSettings, getAdminSettings, updateAdminSettings } from '../services/admin_settings';



interface AdminSettingsState {
    data: AdminSettings | null;
    localData: Record<string, any>;
    loading: boolean;
    error: any | null;
    fetchData: () => Promise<void>;
    updateData: (item: any) => Promise<void>;
}

export const useAdminSettingsStore = create<AdminSettingsState>((set, get) => ({
    data: null,
    localData: {},
    loading: false,
    error: null,
    fetchData: async () => {
        set({ loading: true, error: null });
        try {
            // Fetch server data
            
            const result = await getAdminSettings();
            
            
            // Fetch local data from localStorage
            const localData: Record<string, any> = {};
            
            
            
            
            
            
            
            
            set({ data: result, localData, loading: false });
        } catch (error) {
            console.error("Failed to fetch data:", error);
            set({ loading: false, error });
        }
    },
    updateData: async (item: any) => {
        try {
            // Separate server and local data
            const serverData: Record<string, any> = {};
            const localData: Record<string, any> = {};
            
            const allowedFields: string[] = [
                
                
                
                
                'banner_text',
                
                
                
                'maintenance_mode',
                
                
            ];
            const localFields: string[] = [
                
                
                
                
                
                
                
            ];
            
            Object.keys(item).forEach(key => {
                if (!allowedFields.includes(key)) return;
                if (localFields.includes(key)) {
                    localData[key] = item[key];
                    // Save to localStorage
                    localStorage.setItem(`admin_settings_${key}`, typeof item[key] === 'object' ? JSON.stringify(item[key]) : item[key]);
                } else {
                    serverData[key] = item[key];
                }
            });

            
            const result = await updateAdminSettings(serverData);
            set({ data: result, localData });
            
        } catch (error) {
            console.error("Failed to update data:", error);
            throw error;
        }
    },
}));