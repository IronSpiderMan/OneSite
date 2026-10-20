import request from '../utils/request';

const API_URL = '/secret_config/';

export interface SecretConfig {

    
    id: number;
    

    
    api_key: string;
    

    
    internal_url: string;
    

    
    debug_mode: boolean;
    

}

export const getSecretConfig = async () => {
    const response = await request.get<SecretConfig>(API_URL);
    return response.data;
};

export const updateSecretConfig = async (data: Partial<SecretConfig>) => {
    const response = await request.put<SecretConfig>(API_URL, data);
    return response.data;
};