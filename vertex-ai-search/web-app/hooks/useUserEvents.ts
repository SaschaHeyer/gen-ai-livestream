import { useMemo } from 'react';

const PSEUDO_KEY = 'userPseudoId';

const getOrCreatePseudoId = () => {
    if (typeof window === 'undefined') return 'anon-server';
    const existing = window.localStorage.getItem(PSEUDO_KEY);
    if (existing) return existing;
    const id = crypto.randomUUID();
    window.localStorage.setItem(PSEUDO_KEY, id);
    return id;
};

export function useUserEvents() {
    const userPseudoId = useMemo(() => getOrCreatePseudoId(), []);

    const sendEvent = async (payload: {
        eventType: string;
        searchQuery?: string;
        attributionToken?: string;
        documents?: string[];
        mediaInfo?: Record<string, unknown>;
    }) => {
        try {
            await fetch('/api/events', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...payload,
                    userPseudoId,
                    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
                    pageViewId: typeof window !== 'undefined' ? window.location.pathname : undefined,
                }),
            });
        } catch (err) {
            console.error('Failed to send user event', err);
        }
    };

    return { userPseudoId, sendEvent };
}
