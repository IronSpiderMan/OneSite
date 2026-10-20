import { create } from 'zustand';

import { SystemConfig, getSystemConfig, updateSystemConfig } from '../services/system_config';



interface SystemConfigState {
    data: SystemConfig | null;
    localData: Record<string, any>;
    loading: boolean;
    error: any | null;
    fetchData: () => Promise<void>;
    updateData: (item: any) => Promise<void>;
}

export const useSystemConfigStore = create<SystemConfigState>((set, get) => ({
    data: null,
    localData: {},
    loading: false,
    error: null,
    fetchData: async () => {
        set({ loading: true, error: null });
        try {
            // Fetch server data
            
            const result = await getSystemConfig();
            
            
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
                
                
                
                'day_shift_start_at',
                
                
                
                'day_shift_end_at',
                
                
                
                'night_shift_start_at',
                
                
                
                'night_shift_end_at',
                
                
                
                'allow_registration',
                
                
            ];
            const localFields: string[] = [
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
            ];
            
            Object.keys(item).forEach(key => {
                if (!allowedFields.includes(key)) return;
                if (localFields.includes(key)) {
                    localData[key] = item[key];
                    // Save to localStorage
                    localStorage.setItem(`system_config_${key}`, typeof item[key] === 'object' ? JSON.stringify(item[key]) : item[key]);
                } else {
                    serverData[key] = item[key];
                }
            });

            
            const result = await updateSystemConfig(serverData);
            set({ data: result, localData });
            
        } catch (error) {
            console.error("Failed to update data:", error);
            throw error;
        }
    },
}));