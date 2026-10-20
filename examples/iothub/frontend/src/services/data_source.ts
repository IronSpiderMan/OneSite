import request from '../utils/request';

const API_URL = '/data_sources';

export interface DataSource {
    id: number;

    

    
    name: string;
    
    

    
    type: string;
    
    

    
    host: string;
    
    

    
    port: number;
    
    

    
    description: string;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getDataSources = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<DataSource>>(url);
    return response.data;
};

export const getDataSource = async (id: number) => {
    const response = await request.get<DataSource>(`${API_URL}/${id}`);
    return response.data;
};

export const createDataSource = async (data: any) => {
    const response = await request.post<DataSource>(`${API_URL}/`, data);
    return response.data;
};

export const updateDataSource = async (id: number, data: any) => {
    const response = await request.put<DataSource>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteDataSource = async (id: number) => {
    const response = await request.delete<DataSource>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteDataSource = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};











