import { SearchTaskRequest, SearchStatusResponse } from '@/interface/search/searchInterface';
import { ApiResponse } from '@/interface/global';
import { Cookies } from '@/utils/cookies';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;


export const createSearchTask = async (data: SearchTaskRequest): Promise<ApiResponse> => {
    try {
        const sessionId = Cookies.getSessionId();
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
        };

        if (sessionId) {
            headers['Authorization'] = `Bearer ${sessionId}`;
        }

        const response = await fetch(`${API_BASE_URL}/api/search/task`, {
            method: 'POST',
            headers,
            body: JSON.stringify(data),
        });

        return await response.json();
    } catch (error) {
        console.error('Create search task failed:', error);
        return {
            success: false,
            message: {
                en: 'Failed to create search task',
                zh: '创建检索任务失败'
            }
        };
    }
};

export const getSearchStatus = async (taskId: string): Promise<ApiResponse<SearchStatusResponse>> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/search/search_status/${taskId}`);
        return await response.json();
    } catch (error) {
        console.error('Get search status failed:', error);
        return {
            success: false,
            message: {
                en: 'Failed to get search status',
                zh: '获取检索状态失败'
            }
        };
    }
};

export const downloadSearchResult = (downloadLink: string): void => {
    const link = downloadLink.startsWith('/') ? `${API_BASE_URL}${downloadLink}` : `${API_BASE_URL}/${downloadLink}`;

    // Use anchor tag for better download behavior (avoids popup blockers)
    const a = document.createElement('a');
    a.href = link;
    // target="_blank" is still useful if the browser insists on opening it
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
};

export const stopSearchTask = async (taskId: string): Promise<ApiResponse> => {
    try {
        const sessionId = Cookies.getSessionId();
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
        };
        if (sessionId) {
            headers['Authorization'] = `Bearer ${sessionId}`;
        }

        const response = await fetch(`${API_BASE_URL}/api/search/task/stop`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ task_id: taskId }),
        });
        return await response.json();
    } catch (error) {
        console.error('Stop search task failed:', error);
        return {
            success: false,
            message: {
                en: 'Failed to stop search task',
                zh: '停止检索任务失败'
            }
        };
    }
};

export const getUserDocuments = async (): Promise<ApiResponse<import('@/interface/search/searchInterface').SearchDocument[]>> => {
    try {
        const sessionId = Cookies.getSessionId();
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
        };
        if (sessionId) {
            headers['Authorization'] = `Bearer ${sessionId}`;
        }

        const response = await fetch(`${API_BASE_URL}/api/search/documents`, {
            method: 'GET',
            headers,
        });

        return await response.json();
    } catch (error) {
        console.error('Get user documents failed:', error);
        return {
            success: false,
            message: {
                en: 'Failed to get documents',
                zh: '获取文档列表失败'
            }
        };
    }
};

export const deleteDocument = async (docId: string): Promise<ApiResponse> => {
    try {
        const sessionId = Cookies.getSessionId();
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
        };
        if (sessionId) {
            headers['Authorization'] = `Bearer ${sessionId}`;
        }

        const response = await fetch(`${API_BASE_URL}/api/search/documents/${docId}`, {
            method: 'DELETE',
            headers,
        });

        if (!response.ok) {
            const text = await response.text();
            console.error(`Delete failed: ${response.status} ${response.statusText}`, text);
            try {
                return JSON.parse(text);
            } catch (e) {
                throw new Error(`Server returned ${response.status}: ${text}`);
            }
        }

        return await response.json();
    } catch (error) {
        console.error('Delete document failed:', error);
        return {
            success: false,
            message: {
                en: 'Failed to delete document',
                zh: '删除文档失败。'
            }
        };
    }
};
