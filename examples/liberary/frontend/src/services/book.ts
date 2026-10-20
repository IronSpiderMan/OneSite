import request from '../utils/request';

const API_URL = '/books';



export interface Book {
    id: number;

    

    
    title: string;
    
    

    
    published_at: any;
    
    

    
    author_id: number;
    
    author_id_label?: string;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getBooks = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<Book>>(url);
    return response.data;
};

export const getBook = async (id: number) => {
    const response = await request.get<Book>(`${API_URL}/${id}`);
    return response.data;
};

export const createBook = async (data: any) => {
    const response = await request.post<Book>(`${API_URL}/`, data);
    return response.data;
};

export const updateBook = async (id: number, data: any) => {
    const response = await request.put<Book>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteBook = async (id: number) => {
    const response = await request.delete<Book>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteBook = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};









import { Subject } from './subject';
export const getBookSubjects = async (id: number, page = 1, size = 20) => {
    const response = await request.get<PaginatedResponse<Subject>>(`${API_URL}/${id}/subjects?page=${page}&size=${size}`);
    return response.data;
};







// Import/Export functions

export const exportBooks = async () => {
    const response = await request.post<Blob>(`${API_URL}/export`, {}, {
        responseType: 'blob'
    });
    // Create download link for the returned file
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'books_export.csv');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
};



export interface ImportResult {
    success: number;
    failed: number;
    errors: string[];
}

export const importBooks = async (file: File): Promise<ImportResult> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await request.post<ImportResult>(`${API_URL}/import`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
};






