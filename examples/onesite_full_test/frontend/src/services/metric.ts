import request from '../utils/request';

const API_URL = '/metrics';



export interface Metric {
    id: number;

    

    
    name: string;
    
    

    
    value: number;
    
    

    
    recorded_at: any;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getMetrics = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<Metric>>(url);
    return response.data;
};

export const getMetric = async (id: number) => {
    const response = await request.get<Metric>(`${API_URL}/${id}`);
    return response.data;
};

export const createMetric = async (data: any) => {
    const response = await request.post<Metric>(`${API_URL}/`, data);
    return response.data;
};

export const updateMetric = async (id: number, data: any) => {
    const response = await request.put<Metric>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteMetric = async (id: number) => {
    const response = await request.delete<Metric>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteMetric = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};














