'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search } from 'lucide-react';

interface SearchBarProps {
    initialQuery?: string;
}

const SearchBar: React.FC<SearchBarProps> = ({ initialQuery = '' }) => {
    const [query, setQuery] = useState(initialQuery);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const debounceRef = useRef<NodeJS.Timeout | null>(null);
    const router = useRouter();

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (query.trim()) {
            router.push(`/search?q=${encodeURIComponent(query)}`);
        }
    };

    const fetchSuggestions = async (text: string) => {
        try {
            const res = await fetch('/api/autocomplete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: text }),
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
                    className="block w-full pl-10 pr-3 py-4 border border-gray-300 rounded-full leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-lg shadow-sm transition-shadow hover:shadow-md"
                    placeholder="Search for videos, news, and more..."
                    value={query}
                    onChange={(e) => {
                        setQuery(e.target.value);
                        setShowSuggestions(true);
                    }}
                    onFocus={() => setShowSuggestions(true)}
                    onBlur={() => setTimeout(() => setShowSuggestions(false), 100)}
                />
                <button
                    type="submit"
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                >
                    <div className="bg-blue-600 hover:bg-blue-700 text-white rounded-full p-2 transition-colors">
                        <Search className="h-5 w-5" />
                    </div>
                </button>
            </form>

            {showSuggestions && suggestions.length > 0 && (
                <div className="absolute mt-2 w-full bg-white border border-gray-200 rounded-xl shadow-lg z-50 overflow-hidden">
                    {suggestions.map((s, idx) => (
                        <button
                            key={`${s}-${idx}`}
                            className="w-full text-left px-4 py-3 hover:bg-gray-50 text-gray-700"
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
