import { create } from 'zustand';


export interface CustomConfig {

    
    language: any;
    

    
    timezone: any;
    

    
    theme: any;
    

}


interface CustomConfigState {
    data: CustomConfig | null;
    localData: Record<string, any>;
    loading: boolean;
    error: any | null;
    fetchData: () => Promise<void>;
    updateData: (item: any) => Promise<void>;
}

export const useCustomConfigStore = create<CustomConfigState>((set, get) => ({
    data: null,
    localData: {},
    loading: false,
    error: null,
    fetchData: async () => {
        set({ loading: true, error: null });
        try {
            // Fetch server data
            
            const result = null;
            
            
            // Fetch local data from localStorage
            const localData: Record<string, any> = {};
            
            
            const languageVal = localStorage.getItem('custom_config_language');
            if (languageVal !== null) {
                try {
                    localData['language'] = JSON.parse(languageVal);
                } catch(e) {
                    localData['language'] = languageVal;
                }
            } else {
                
                
                localData['language'] = "en";
                
                
            }
            
            
            
            const timezoneVal = localStorage.getItem('custom_config_timezone');
            if (timezoneVal !== null) {
                try {
                    localData['timezone'] = JSON.parse(timezoneVal);
                } catch(e) {
                    localData['timezone'] = timezoneVal;
                }
            } else {
                
                
                localData['timezone'] = "UTC";
                
                
            }
            
            
            
            const themeVal = localStorage.getItem('custom_config_theme');
            if (themeVal !== null) {
                try {
                    localData['theme'] = JSON.parse(themeVal);
                } catch(e) {
                    localData['theme'] = themeVal;
                }
            } else {
                
                
                localData['theme'] = "system";
                
                
            }
            
            
            
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
                
                
                'language',
                
                
                
                'timezone',
                
                
                
                'theme',
                
                
            ];
            const localFields: string[] = [
                
                
                'language',
                
                
                
                'timezone',
                
                
                
                'theme',
                
                
            ];
            
            Object.keys(item).forEach(key => {
                if (!allowedFields.includes(key)) return;
                if (localFields.includes(key)) {
                    localData[key] = item[key];
                    // Save to localStorage
                    localStorage.setItem(`custom_config_${key}`, typeof item[key] === 'object' ? JSON.stringify(item[key]) : item[key]);
                } else {
                    serverData[key] = item[key];
                }
            });

            
            set({ localData });
            
        } catch (error) {
            console.error("Failed to update data:", error);
            throw error;
        }
    },
}));