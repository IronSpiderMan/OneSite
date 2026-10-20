import request from '../utils/request';

const API_URL = '/users';

export interface User {
    id: number;

    
    email: string;
    
    

    
    full_name: string;
    
    

    
    avatar: string;
    
    

    
    is_active: boolean;
    
    

    
    role: string;
    
    

    

    

    
    created_at: any;
    
    

    
    updated_at: any;
    
    

    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getUsers = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<User>>(url);
    return response.data;
};

export const getUser = async (id: number) => {
    const response = await request.get<User>(`${API_URL}/${id}`);
    return response.data;
};

export const createUser = async (data: any) => {
    const response = await request.post<User>(`${API_URL}/`, data);
    return response.data;
};

export const updateUser = async (id: number, data: any) => {
    const response = await request.put<User>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteUser = async (id: number) => {
    const response = await request.delete<User>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteUser = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};






export const getMe = async () => {
    const response = await request.get<User>(`${API_URL}/me`);
    return response.data;
};

export const updateMe = async (data: any) => {
    const response = await request.put<User>(`${API_URL}/me`, data);
    return response.data;
};






