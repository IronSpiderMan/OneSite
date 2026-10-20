import request from '../utils/request';

const API_URL = '/system_config/';

export interface SystemConfig {

    
    id: number;
    

    
    site_name: string;
    

    
    allow_registration: boolean;
    

}

export const getSystemConfig = async () => {
    const response = await request.get<SystemConfig>(API_URL);
    return response.data;
};

export const updateSystemConfig = async (data: Partial<SystemConfig>) => {
    const response = await request.put<SystemConfig>(API_URL, data);
    return response.data;
};