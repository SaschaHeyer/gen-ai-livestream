import { useMemo, useCallback } from 'react';

const PSEUDO_KEY = 'userPseudoId';
const USER_ID_KEY = 'userId';

const getOrCreatePseudoId = () => {
    if (typeof window === 'undefined') return 'anon-server';
    const existing = window.localStorage.getItem(PSEUDO_KEY);
    if (existing) return existing;
    const id = crypto.randomUUID();
    window.localStorage.setItem(PSEUDO_KEY, id);
    return id;
};

const getUserId = () => {
    if (typeof window === 'undefined') return undefined;
    const stored = window.localStorage.getItem(USER_ID_KEY);
    if (stored) return stored;
    // Optional demo override via env for workshops
    const envUserId = process.env.NEXT_PUBLIC_USER_ID;
    if (envUserId) {
        window.localStorage.setItem(USER_ID_KEY, envUserId);
        return envUserId;
    }
    return undefined;
};

export function useUserEvents() {
    const userPseudoId = useMemo(() => getOrCreatePseudoId(), []);
    const userId = useMemo(() => getUserId(), []);

    const sendEvent = useCallback(async (payload: {
        eventType: string;
        searchQuery?: string;
        attributionToken?: string;
        documents?: string[];
        mediaInfo?: Record<string, unknown>;
        userId?: string;
    }) => {
        try {
            const body = {
                ...payload,
                userPseudoId,
                userId: payload.userId || userId,
                userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
                pageViewId: typeof window !== 'undefined' ? window.location.pathname : undefined,
            };
            await fetch('/api/events', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                keepalive: true,
            });
        } catch (err) {
            console.error('Failed to send user event', err);
        }
    }, [userPseudoId]);

    return { userPseudoId, userId, sendEvent };
}
