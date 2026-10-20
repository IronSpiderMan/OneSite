import request from '../utils/request';

const API_URL = '/tags';



export interface Tag {
    id: number;

    

    
    name: string;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getTags = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<Tag>>(url);
    return response.data;
};

export const getTag = async (id: number) => {
    const response = await request.get<Tag>(`${API_URL}/${id}`);
    return response.data;
};

export const createTag = async (data: any) => {
    const response = await request.post<Tag>(`${API_URL}/`, data);
    return response.data;
};

export const updateTag = async (id: number, data: any) => {
    const response = await request.put<Tag>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteTag = async (id: number) => {
    const response = await request.delete<Tag>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteTag = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};











import { Product } from './product';
export const getTagProducts = async (id: number, page = 1, size = 20) => {
    const response = await request.get<PaginatedResponse<Product>>(`${API_URL}/${id}/products?page=${page}&size=${size}`);
    return response.data;
};






