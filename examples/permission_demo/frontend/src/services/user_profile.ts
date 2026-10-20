import request from '../utils/request';

const API_URL = '/user_profiles';



export interface UserProfile {
    id: number;

    

    
    display_name: string;
    
    

    
    avatar: string;
    
    

    
    bio: string;
    
    

    
    phone: string;
    
    

    
    ssn: string;
    
    

    
    internal_note: string;
    
    

    
    loyalty_points: number;
    
    

    
    id_document: string;
    
    

    
    created_at: any;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getUserProfiles = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<UserProfile>>(url);
    return response.data;
};

export const getUserProfile = async (id: number) => {
    const response = await request.get<UserProfile>(`${API_URL}/${id}`);
    return response.data;
};

export const createUserProfile = async (data: any) => {
    const response = await request.post<UserProfile>(`${API_URL}/`, data);
    return response.data;
};

export const updateUserProfile = async (id: number, data: any) => {
    const response = await request.put<UserProfile>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteUserProfile = async (id: number) => {
    const response = await request.delete<UserProfile>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteUserProfile = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};














