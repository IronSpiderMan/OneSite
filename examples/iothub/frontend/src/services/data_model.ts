import request from '../utils/request';

const API_URL = '/data_models';

export interface DataModel {
    id: number;

    

    
    name: string;
    
    

    
    identifier: string;
    
    

    
    version: string;
    
    

    
    data_source_id: number;
    
    data_source_id_label?: string;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getDataModels = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<DataModel>>(url);
    return response.data;
};

export const getDataModel = async (id: number) => {
    const response = await request.get<DataModel>(`${API_URL}/${id}`);
    return response.data;
};

export const createDataModel = async (data: any) => {
    const response = await request.post<DataModel>(`${API_URL}/`, data);
    return response.data;
};

export const updateDataModel = async (id: number, data: any) => {
    const response = await request.put<DataModel>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteDataModel = async (id: number) => {
    const response = await request.delete<DataModel>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteDataModel = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};











