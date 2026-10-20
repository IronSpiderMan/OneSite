import { create } from 'zustand';

import { AdminConfig, getAdminConfig, updateAdminConfig } from '../services/admin_config';



interface AdminConfigState {
    data: AdminConfig | null;
    localData: Record<string, any>;
    loading: boolean;
    error: any | null;
    fetchData: () => Promise<void>;
    updateData: (item: any) => Promise<void>;
}

export const useAdminConfigStore = create<AdminConfigState>((set, get) => ({
    data: null,
    localData: {},
    loading: false,
    error: null,
    fetchData: async () => {
        set({ loading: true, error: null });
        try {
            // Fetch server data
            
            const result = await getAdminConfig();
            
            
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
                
                
                
                
                'site_name',
                
                
                
                'max_upload_size',
                
                
                
                'enable_registration',
                
                
            ];
            const localFields: string[] = [
                
                
                
                
                
                
                
                
                
            ];
            
            Object.keys(item).forEach(key => {
                if (!allowedFields.includes(key)) return;
                if (localFields.includes(key)) {
                    localData[key] = item[key];
                    // Save to localStorage
                    localStorage.setItem(`admin_config_${key}`, typeof item[key] === 'object' ? JSON.stringify(item[key]) : item[key]);
                } else {
                    serverData[key] = item[key];
                }
            });

            
            const result = await updateAdminConfig(serverData);
            set({ data: result, localData });
            
        } catch (error) {
            console.error("Failed to update data:", error);
            throw error;
        }
    },
}));