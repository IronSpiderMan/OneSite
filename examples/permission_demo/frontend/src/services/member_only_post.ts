import request from '../utils/request';

const API_URL = '/member_only_posts';



export interface MemberOnlyPost {
    id: number;

    

    
    title: string;
    
    

    
    content: string;
    
    

    
    member_level: string;
    
    

    
    created_at: any;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getMemberOnlyPosts = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<MemberOnlyPost>>(url);
    return response.data;
};

export const getMemberOnlyPost = async (id: number) => {
    const response = await request.get<MemberOnlyPost>(`${API_URL}/${id}`);
    return response.data;
};

export const createMemberOnlyPost = async (data: any) => {
    const response = await request.post<MemberOnlyPost>(`${API_URL}/`, data);
    return response.data;
};

export const updateMemberOnlyPost = async (id: number, data: any) => {
    const response = await request.put<MemberOnlyPost>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteMemberOnlyPost = async (id: number) => {
    const response = await request.delete<MemberOnlyPost>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteMemberOnlyPost = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};














