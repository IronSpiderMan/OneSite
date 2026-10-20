import request from '../utils/request';

const API_URL = '/devices';

export interface Device {
    id: number;

    

    
    name: string;
    
    

    
    device_key: string;
    
    

    
    status: string;
    
    

    
    data_model_id: number;
    
    data_model_id_label?: string;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getDevices = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<Device>>(url);
    return response.data;
};

export const getDevice = async (id: number) => {
    const response = await request.get<Device>(`${API_URL}/${id}`);
    return response.data;
};

export const createDevice = async (data: any) => {
    const response = await request.post<Device>(`${API_URL}/`, data);
    return response.data;
};

export const updateDevice = async (id: number, data: any) => {
    const response = await request.put<Device>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteDevice = async (id: number) => {
    const response = await request.delete<Device>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteDevice = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};











