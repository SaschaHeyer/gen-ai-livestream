import { useEffect, useState, useCallback } from 'react';

const LANG_KEY = 'chronos_language_codes';
const COUNTRY_KEY = 'chronos_country_code';

const normalizeLangs = (langs: (string | null | undefined)[]) => {
    return Array.from(
        new Set(
            langs
                .filter(Boolean)
                .map((l) => (l as string).toLowerCase())
                .map((l) => l.split('-')[0])
        )
    );
};

export function useUserPreferences() {
    const [languageCodes, setLanguageCodes] = useState<string[]>([]);
    const [countryCode, setCountryCode] = useState<string>('US');

    // Load from storage or navigator
    useEffect(() => {
        if (typeof window === 'undefined') return;
        const storedLangs = window.localStorage.getItem(LANG_KEY);
        const storedCountry = window.localStorage.getItem(COUNTRY_KEY);

        if (storedLangs) {
            try {
                const parsed = JSON.parse(storedLangs);
                if (Array.isArray(parsed)) setLanguageCodes(parsed as string[]);
            } catch { /* ignore */ }
        } else {
            const langs = typeof navigator !== 'undefined' && navigator.languages?.length ? navigator.languages : [navigator.language];
            setLanguageCodes(normalizeLangs(langs));
        }

        if (storedCountry) {
            setCountryCode(storedCountry);
        } else if (typeof navigator !== 'undefined') {
            const locale = navigator.language || 'en-US';
            const country = locale.split('-')[1] || 'US';
            setCountryCode(country.toUpperCase());
        }
    }, []);

    const savePreferences = useCallback((langs: string[], country: string) => {
        if (typeof window === 'undefined') return;
        const safeLangs = langs.filter(Boolean);
        setLanguageCodes(safeLangs);
        setCountryCode(country);
        window.localStorage.setItem(LANG_KEY, JSON.stringify(safeLangs));
        window.localStorage.setItem(COUNTRY_KEY, country);
        document.cookie = `chronos_lang=${safeLangs.join(',')}; path=/; max-age=31536000`;
        document.cookie = `chronos_country=${country}; path=/; max-age=31536000`;
    }, []);

    return { languageCodes, countryCode, savePreferences, setLanguageCodes, setCountryCode };
}

