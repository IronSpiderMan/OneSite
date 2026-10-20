import request from '../utils/request';

const API_URL = '/premium_contents';



export interface PremiumContent {
    id: number;

    

    
    title: string;
    
    

    
    body: string;
    
    

    
    price: number;
    
    

    
    created_at: any;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getPremiumContents = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<PremiumContent>>(url);
    return response.data;
};

export const getPremiumContent = async (id: number) => {
    const response = await request.get<PremiumContent>(`${API_URL}/${id}`);
    return response.data;
};

export const createPremiumContent = async (data: any) => {
    const response = await request.post<PremiumContent>(`${API_URL}/`, data);
    return response.data;
};

export const updatePremiumContent = async (id: number, data: any) => {
    const response = await request.put<PremiumContent>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deletePremiumContent = async (id: number) => {
    const response = await request.delete<PremiumContent>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeletePremiumContent = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};














