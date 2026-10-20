import request from '../utils/request';

const API_URL = '/products';



export interface Product {
    id: number;

    

    
    name: string;
    
    

    
    status: string;
    
    

    
    is_featured: boolean;
    
    

    
    category_id: number;
    
    category_id_label?: string;
    
    

    
    variants: any[];
    
    

    
    meta_data: Record<string, any>;
    
    

    
    created_at: any;
    
    

    
    cover_image: string;
    
    

    
    manual_file: string;
    
    

    

    
    internal_note: string;
    
    

}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    total_pages: number;
}

export const getProducts = async (page = 1, size = 20, filters?: Record<string, any>) => {
    let url = `${API_URL}/?page=${page}&size=${size}`;
    if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url += `&${key}=${encodeURIComponent(String(value))}`;
            }
        });
    }
    const response = await request.get<PaginatedResponse<Product>>(url);
    return response.data;
};

export const getProduct = async (id: number) => {
    const response = await request.get<Product>(`${API_URL}/${id}`);
    return response.data;
};

export const createProduct = async (data: any) => {
    const response = await request.post<Product>(`${API_URL}/`, data);
    return response.data;
};

export const updateProduct = async (id: number, data: any) => {
    const response = await request.put<Product>(`${API_URL}/${id}`, data);
    return response.data;
};

export const deleteProduct = async (id: number) => {
    const response = await request.delete<Product>(`${API_URL}/${id}`);
    return response.data;
};

export const bulkDeleteProduct = async (ids: number[]) => {
    const response = await request.post<{ deleted: number }>(`${API_URL}/bulk_delete`, { ids });
    return response.data;
};









import { Tag } from './tag';
export const getProductTags = async (id: number, page = 1, size = 20) => {
    const response = await request.get<PaginatedResponse<Tag>>(`${API_URL}/${id}/tags?page=${page}&size=${size}`);
    return response.data;
};

export type ProductTagWithMeta = { id: number; label: string; order: number };
export const getProductTagsWithMeta = async (id: number, page = 1, size = 50) => {
    const response = await request.get<PaginatedResponse<ProductTagWithMeta>>(`${API_URL}/${id}/tags_with_meta?page=${page}&size=${size}`);
    return response.data;
};







// Import/Export functions

export const exportProducts = async () => {
    const response = await request.post<Blob>(`${API_URL}/export`, {}, {
        responseType: 'blob'
    });
    // Create download link for the returned file
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'products_export.csv');
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

export const importProducts = async (file: File): Promise<ImportResult> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await request.post<ImportResult>(`${API_URL}/import`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
};






