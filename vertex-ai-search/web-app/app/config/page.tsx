'use client';

import { useEffect, useState } from 'react';
import { useUserPreferences } from '../../hooks/useUserPreferences';
import Link from 'next/link';

const LANGUAGE_OPTIONS = ['en', 'sv', 'de', 'fr', 'es', 'it', 'pt', 'nl', 'no', 'da', 'fi'];
const COUNTRY_OPTIONS = ['US', 'SE', 'DE', 'FR', 'ES', 'IT', 'PT', 'NL', 'NO', 'DK', 'FI', 'GB', 'CA', 'AU'];

export default function ConfigPage() {
    const { languageCodes, countryCode, savePreferences } = useUserPreferences();
    const [langs, setLangs] = useState<string[]>(languageCodes);
    const [country, setCountry] = useState<string>(countryCode);
    const [saved, setSaved] = useState(false);

    useEffect(() => {
        setLangs(languageCodes);
        setCountry(countryCode);
    }, [languageCodes, countryCode]);

    const toggleLang = (code: string) => {
        setSaved(false);
        setLangs((prev) => (prev.includes(code) ? prev.filter((l) => l !== code) : [...prev, code]));
    };

    const onSave = () => {
        const list = langs.length ? langs : [country.toLowerCase()];
        savePreferences(list, country);
        setSaved(true);
    };

    return (
        <div className="max-w-3xl mx-auto px-4 py-10 space-y-8 text-[var(--chronos-black)]">
            <div className="flex items-center gap-3 text-sm font-mono">
                <Link href="/" className="underline">Home</Link>
                <span>/</span>
                <span className="font-bold">Config</span>
            </div>
            <h1 className="font-serif text-4xl font-bold">Audience / Language Config</h1>
            <p className="text-gray-700 font-sans">
                Set the preferred languages and market for this browser. These values are sent with search and autocomplete requests to showcase localization and personalization with Vertex AI Search.
            </p>

            <div className="neo-border bg-white p-6 space-y-6">
                <div>
                    <h2 className="font-mono text-xs text-gray-600 mb-2">LANGUAGES</h2>
                    <div className="flex flex-wrap gap-2">
                        {LANGUAGE_OPTIONS.map((code) => (
                            <button
                                key={code}
                                onClick={() => toggleLang(code)}
                                className={`px-3 py-2 border-2 border-[var(--chronos-black)] text-sm font-mono ${langs.includes(code) ? 'bg-[var(--chronos-black)] text-white' : 'bg-white'}`}
                            >
                                {code.toUpperCase()}
                            </button>
                        ))}
                    </div>
                    <p className="text-xs text-gray-500 mt-2">Pick one or more. Default is inferred from browser.</p>
                </div>

                <div>
                    <h2 className="font-mono text-xs text-gray-600 mb-2">MARKET / COUNTRY</h2>
                    <select
                        value={country}
                        onChange={(e) => { setSaved(false); setCountry(e.target.value); }}
                        className="border-2 border-[var(--chronos-black)] px-3 py-2 font-mono text-sm bg-white"
                    >
                        {COUNTRY_OPTIONS.map((c) => (
                            <option key={c} value={c}>{c}</option>
                        ))}
                    </select>
                </div>

                <button
                    onClick={onSave}
                    className="px-4 py-3 bg-[var(--chronos-black)] text-white font-mono text-sm border-2 border-[var(--chronos-black)] hover:bg-[var(--chronos-accent)]"
                >
                    Save preferences
                </button>
                {saved && <div className="text-xs text-green-700 font-mono">Saved to browser storage & cookies. Reload search to apply.</div>}
            </div>
        </div>
    );
}

