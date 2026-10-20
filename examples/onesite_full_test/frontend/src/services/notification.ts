import request from '../utils/request';

const API_URL = '/notifications';



export interface Notification {
    id: number;

    

    
    title: string;
    
    

    
    summary: string;
    
    

    
    content: string;
    
    

    
    created_at: any;
    
    

    
    is_read: boolean;
    
    

    
    user_id: number;
    
    user_id_label?: string;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getNotifications = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<Notification>>(url);
    return response.data;
};

export const getNotification = async (id: number) => {
    const response = await request.get<Notification>(`${API_URL}/${id}`);
    return response.data;
};

export const createNotification = async (data: any) => {
    const response = await request.post<Notification>(`${API_URL}/`, data);
    return response.data;
};

export const updateNotification = async (id: number, data: any) => {
    const response = await request.put<Notification>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteNotification = async (id: number) => {
    const response = await request.delete<Notification>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteNotification = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};














