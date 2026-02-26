/** Fetch a fresh token from the server and store it. */
async function refreshToken(): Promise<string> {
    const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: 'subtrack' }),
    });
    const data = await res.json();
    if (data.token) {
        localStorage.setItem('subtrack_token', data.token);
        return data.token;
    }
    return '';
}

/** Wrapper around fetch that automatically adds the Bearer token.
 *  If the server returns 401 (e.g. after a restart), it refreshes
 *  the token once and retries automatically. */
export async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
    let token = localStorage.getItem('subtrack_token') ?? '';

    // If no token yet, get one before the first request
    if (!token) token = await refreshToken();

    const makeRequest = (t: string) => fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${t}`,
            'ngrok-skip-browser-warning': '1',
            ...(options.headers ?? {}),
        },
    });

    const response = await makeRequest(token);

    // Token stale (server restarted) — refresh and retry once
    if (response.status === 401) {
        const newToken = await refreshToken();
        if (newToken) return makeRequest(newToken);
    }

    return response;
}
