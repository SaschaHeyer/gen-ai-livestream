'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search } from 'lucide-react';
import { useUserEvents } from '../hooks/useUserEvents';
import { useUserPreferences } from '../hooks/useUserPreferences';

interface SearchBarProps {
    initialQuery?: string;
}

const SearchBar: React.FC<SearchBarProps> = ({ initialQuery = '' }) => {
    const [query, setQuery] = useState(initialQuery);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const debounceRef = useRef<NodeJS.Timeout | null>(null);
    const router = useRouter();
    const { userPseudoId } = useUserEvents();
    const { languageCodes, countryCode } = useUserPreferences();

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        const q = query.trim();
        router.push(q ? `/search?q=${encodeURIComponent(q)}` : `/search`);
    };

    const fetchSuggestions = async (text: string) => {
        try {
            const res = await fetch('/api/autocomplete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: text, userPseudoId, languageCodes, userCountryCode: countryCode }),
            });
            if (!res.ok) return;
            const data = await res.json();
            setSuggestions(data.suggestions || []);
        } catch (err) {
            console.error('autocomplete error', err);
        }
    };

    useEffect(() => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        if (!query.trim()) {
            debounceRef.current = setTimeout(() => setSuggestions([]), 0);
            return;
        }
        debounceRef.current = setTimeout(() => fetchSuggestions(query), 150);
    }, [query]);

    return (
        <div className="w-full max-w-3xl mx-auto relative">
            <form onSubmit={handleSearch} className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-5 w-5 text-gray-400" />
                </div>
                <input
                    type="text"
                    className="block w-full pl-10 pr-20 py-4 border-2 border-[var(--chronos-black)] rounded-full leading-5 bg-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[var(--chronos-accent)] shadow-[4px_4px_0px_var(--chronos-black)] transition-all font-mono text-sm sm:text-base"
                    placeholder="Ask the Archives..."
                    value={query}
                    onChange={(e) => {
                        setQuery(e.target.value);
                        setShowSuggestions(true);
                    }}
                    onFocus={() => setShowSuggestions(true)}
                    onBlur={() => setTimeout(() => setShowSuggestions(false), 100)}
                />
                <div className="absolute right-3 top-2">
                    <span className="text-[10px] font-mono bg-gray-200 px-1 rounded text-gray-500 border border-gray-300">VERTEX AI</span>
                </div>
                <button type="submit" className="absolute inset-y-0 right-0 pr-10 flex items-center">
                    <div className="bg-[var(--chronos-black)] hover:bg-[var(--chronos-accent)] text-white rounded-full p-2 transition-colors">
                        <Search className="h-5 w-5" />
                    </div>
                </button>
            </form>

            {showSuggestions && suggestions.length > 0 && (
                <div className="absolute mt-2 w-full bg-white border-2 border-[var(--chronos-black)] shadow-[8px_8px_0px_var(--chronos-black)] z-50 overflow-hidden">
                    {suggestions.map((s, idx) => (
                        <button
                            key={`${s}-${idx}`}
                            className="w-full text-left px-4 py-3 hover:bg-gray-100 text-gray-800 font-sans text-sm"
                            onMouseDown={(e) => e.preventDefault()}
                            onClick={() => {
                                setQuery(s);
                                setShowSuggestions(false);
                                router.push(`/search?q=${encodeURIComponent(s)}`);
                            }}
                        >
                            {s}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

export default SearchBar;
