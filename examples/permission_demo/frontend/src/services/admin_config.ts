import request from '../utils/request';

const API_URL = '/admin_config/';

export interface AdminConfig {

    
    id: number;
    

    
    site_name: string;
    

    
    max_upload_size: number;
    

    
    enable_registration: boolean;
    

}

export const getAdminConfig = async () => {
    const response = await request.get<AdminConfig>(API_URL);
    return response.data;
};

export const updateAdminConfig = async (data: Partial<AdminConfig>) => {
    const response = await request.put<AdminConfig>(API_URL, data);
    return response.data;
};