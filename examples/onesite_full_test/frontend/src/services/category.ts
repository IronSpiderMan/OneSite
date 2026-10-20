import request from '../utils/request';

const API_URL = '/categorys';



export interface Category {
    id: number;

    

    
    name: string;
    
    

    
    description: string;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getCategorys = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<Category>>(url);
    return response.data;
};

export const getCategory = async (id: number) => {
    const response = await request.get<Category>(`${API_URL}/${id}`);
    return response.data;
};

export const createCategory = async (data: any) => {
    const response = await request.post<Category>(`${API_URL}/`, data);
    return response.data;
};

export const updateCategory = async (id: number, data: any) => {
    const response = await request.put<Category>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteCategory = async (id: number) => {
    const response = await request.delete<Category>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteCategory = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};














