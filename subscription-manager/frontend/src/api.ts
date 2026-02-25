/** Wrapper around fetch that automatically adds the Bearer token from localStorage. */
export function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
    const token = localStorage.getItem('subtrack_token') ?? '';
    return fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            ...(options.headers ?? {}),
        },
    });
}
