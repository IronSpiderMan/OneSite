import request from '../utils/request';

const API_URL = '/authors';



export interface Author {
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

export const getAuthors = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<Author>>(url);
    return response.data;
};

export const getAuthor = async (id: number) => {
    const response = await request.get<Author>(`${API_URL}/${id}`);
    return response.data;
};

export const createAuthor = async (data: any) => {
    const response = await request.post<Author>(`${API_URL}/`, data);
    return response.data;
};

export const updateAuthor = async (id: number, data: any) => {
    const response = await request.put<Author>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteAuthor = async (id: number) => {
    const response = await request.delete<Author>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteAuthor = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};














