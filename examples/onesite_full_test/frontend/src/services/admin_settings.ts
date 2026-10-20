import request from '../utils/request';

const API_URL = '/admin_settings/';

export interface AdminSettings {

    
    id: number;
    

    

    

}

export const getAdminSettings = async () => {
    const response = await request.get<AdminSettings>(API_URL);
    return response.data;
};

export const updateAdminSettings = async (data: Partial<AdminSettings>) => {
    const response = await request.put<AdminSettings>(API_URL, data);
    return response.data;
};