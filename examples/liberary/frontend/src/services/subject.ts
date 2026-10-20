import request from '../utils/request';

const API_URL = '/subjects';



export interface Subject {
    id: number;

    

    
    title: string;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getSubjects = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<Subject>>(url);
    return response.data;
};

export const getSubject = async (id: number) => {
    const response = await request.get<Subject>(`${API_URL}/${id}`);
    return response.data;
};

export const createSubject = async (data: any) => {
    const response = await request.post<Subject>(`${API_URL}/`, data);
    return response.data;
};

export const updateSubject = async (id: number, data: any) => {
    const response = await request.put<Subject>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteSubject = async (id: number) => {
    const response = await request.delete<Subject>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteSubject = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};











import { Book } from './book';
export const getSubjectBooks = async (id: number, page = 1, size = 20) => {
    const response = await request.get<PaginatedResponse<Book>>(`${API_URL}/${id}/books?page=${page}&size=${size}`);
    return response.data;
};






