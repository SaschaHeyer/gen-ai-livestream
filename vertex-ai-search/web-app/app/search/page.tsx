'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Layout from '../../components/Layout';
import SearchBar from '../../components/SearchBar';
import MediaCard from '../../components/MediaCard';
import FacetFilter from '../../components/FacetFilter';
import { Loader2, AlertCircle, Sparkles } from 'lucide-react';
import { useUserEvents } from '../../hooks/useUserEvents';
import { useUserPreferences } from '../../hooks/useUserPreferences';

function SearchContent() {
    const searchParams = useSearchParams();
    const query = searchParams.get('q') || '';
    const initialCat = searchParams.get('cat');

    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedCategory, setSelectedCategory] = useState<string[]>([]);
    const [selectedMediaType, setSelectedMediaType] = useState<string[]>([]);
    const [sortBy, setSortBy] = useState<string>('relevance');
    const [facets, setFacets] = useState<any[]>([]);
    const [attributionToken, setAttributionToken] = useState<string | null>(null);
    const [corrected, setCorrected] = useState<string | null>(null);
    const [selectedAuthor, setSelectedAuthor] = useState<string[]>([]);
    const [selectedLanguage, setSelectedLanguage] = useState<string[]>([]);
    const [selectedMarket, setSelectedMarket] = useState<string[]>([]);
    const [catHydrated, setCatHydrated] = useState(false);

    const { sendEvent, userPseudoId, userId } = useUserEvents();
    const { languageCodes, countryCode } = useUserPreferences();

    useEffect(() => {
        if (initialCat) {
            setSelectedCategory([initialCat]);
            setCatHydrated(false);
        } else {
            setSelectedCategory([]);
            setCatHydrated(false);
        }
    }, [initialCat]);

    useEffect(() => {
        const fetchResults = async () => {
            setLoading(true);
            setError(null);
            try {
                // Construct filter string
                const filters = [];
                if (selectedCategory.length > 0) {
                    const selectedChildren: string[] = [];
                    selectedCategory.forEach((parentVal) => {
                        const opt = categoryOptions.find((o: any) => o.value === parentVal);
                        if (opt?.children?.length) selectedChildren.push(...opt.children);
                        else selectedChildren.push(parentVal);
                    });
                    const uniq = Array.from(new Set(selectedChildren));
                    if (uniq.length > 0) {
                        filters.push(`categories: ANY("${uniq.join('","')}")`);
                    } else {
                        // Fallback: apply parent values directly if facet children not yet available
                        filters.push(`categories: ANY("${selectedCategory.join('","')}")`);
                    }
                }
                if (selectedMediaType.length > 0) {
                    filters.push(`content_type: ANY("${selectedMediaType.join('","')}")`);
                }
                if (selectedAuthor.length > 0) {
                    filters.push(`author: ANY("${selectedAuthor.join('","')}")`);
                }
                if (selectedLanguage.length > 0) {
                    filters.push(`language: ANY("${selectedLanguage.join('","')}")`);
                }
                if (selectedMarket.length > 0) {
                    filters.push(`market: ANY("${selectedMarket.join('","')}")`);
                }
                const filterString = filters.join(' AND ');

                let resolvedOrderBy: string | undefined = undefined;
                if (sortBy === 'newest') resolvedOrderBy = 'available_time desc';
                else if (sortBy === 'popularity') resolvedOrderBy = 'popularity desc';
                else if (sortBy === 'rating') resolvedOrderBy = 'rating desc';

                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query,
                        filter: filterString,
                        orderBy: resolvedOrderBy,
                        userPseudoId,
                        userId,
                        userCountryCode: countryCode,
                        languageCodes,
                    }),
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch results');
                }

                const data = await response.json();
                console.log('Facets (client):', data.facets);
                setResults(data.results);
                setFacets(data.facets || []);
                setAttributionToken(data.attributionToken || null);
                setCorrected(data.correctedQuery || null);

                // Fire search event
                sendEvent({
                    eventType: 'search',
                    searchQuery: query,
                    attributionToken: data.attributionToken,
                    documents: data.results?.map((r: any) => r.id).filter(Boolean) || [],
                });
            } catch (err) {
                setError('An error occurred while searching. Please try again.');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchResults();
    }, [query, selectedCategory, selectedMediaType, selectedAuthor, selectedLanguage, selectedMarket, sortBy, languageCodes, countryCode, userId, userPseudoId]);

    const handleCategoryChange = (value: string) => {
        setSelectedCategory(prev =>
            prev.includes(value) ? prev.filter(item => item !== value) : [...prev, value]
        );
    };

    const handleMediaTypeChange = (value: string) => {
        setSelectedMediaType(prev =>
            prev.includes(value) ? prev.filter(item => item !== value) : [...prev, value]
        );
    };
    const handleAuthorChange = (value: string) => {
        setSelectedAuthor(prev => prev.includes(value) ? prev.filter(item => item !== value) : [...prev, value]);
    };
    const handleLanguageChange = (value: string) => {
        setSelectedLanguage(prev => prev.includes(value) ? prev.filter(item => item !== value) : [...prev, value]);
    };
    const handleMarketChange = (value: string) => {
        setSelectedMarket(prev => prev.includes(value) ? prev.filter(item => item !== value) : [...prev, value]);
    };

    // Human-friendly labels and grouping for categories/content types
    const prettify = (text: string) =>
        text
            .split(/[-_]/)
            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
            .join(' ');

    const groupLabel = (value: string) => {
        const parts = value.split('>').map((p) => p.trim());
        const leaf = parts.pop() || value;
        const parent = parts.pop();
        const leafPretty = prettify(leaf);
        const parentPretty = parent ? prettify(parent) : '';
        return parentPretty ? `${leafPretty} (${parentPretty})` : leafPretty;
    };

    const rollupCategories = (facetValues: any[]) => {
        const grouped: Record<string, { parent: string; count: number; children: string[] }> = {};
        facetValues.forEach((v) => {
            const raw = v.value as string;
            const parts = raw.split('>').map((p) => p.trim());
            const leaf = parts.pop() || raw;
            const parent = parts.pop() || leaf;
            const key = parent;
            if (!grouped[key]) grouped[key] = { parent: key, count: 0, children: [] };
            grouped[key].count += v.count || 0;
            grouped[key].children.push(raw);
        });
        return Object.values(grouped).sort((a, b) => b.count - a.count || a.parent.localeCompare(b.parent));
    };

    // Helper to transform API facets to UI options with formatted labels
    const getFacetOptions = (key: string) => {
        const facet = facets.find((f: any) => f.key === key);
        if (!facet || !facet.values) return [];

        if (key === 'categories') {
            return rollupCategories(facet.values).map((v) => ({
                label: prettify(v.parent),
                value: v.parent, // UI value
                count: v.count,
                children: v.children, // full paths to filter on
            }));
        }

        return facet.values.map((v: any) => {
            const raw = v.value as string;
            const label = key === 'content_type' ? prettify(raw) : raw;
            return { label, value: raw, count: v.count };
        });
    };

    const categoryOptions = getFacetOptions('categories');
    const mediaTypeOptions = getFacetOptions('content_type');
    const authorOptions = getFacetOptions('author_facet');
    const languageOptions = getFacetOptions('language_code');
    const marketOptions = getFacetOptions('market_facet');

    // Once facets are available, hydrate the initial category selection so filters use the correct child values
    useEffect(() => {
        if (initialCat && !catHydrated && categoryOptions.length > 0) {
            const opt = categoryOptions.find((o: any) => o.value === initialCat);
            if (opt) {
                setSelectedCategory([opt.value]);
                setCatHydrated(true);
            }
        }
    }, [initialCat, catHydrated, categoryOptions]);

    return (
        <>
            <div className="bg-[var(--chronos-white)] border-b-2 border-[var(--chronos-black)]">
                <div className="max-w-6xl mx-auto py-8 px-4">
                    <h1 className="font-serif text-4xl font-bold mb-6 tracking-tight">Search the Chronos Archives</h1>
                    <SearchBar initialQuery={query} />
                </div>
            </div>

            <div className="max-w-6xl mx-auto px-4 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Sidebar / Facets */}
                    <aside className="lg:col-span-3 space-y-8">
                        <div className="sticky top-24 neo-border bg-white p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="font-mono font-bold text-lg">FILTERS</h2>
                                <button
                                    onClick={() => { setSelectedCategory([]); setSelectedMediaType([]); setSelectedAuthor([]); setSelectedLanguage([]); setSelectedMarket([]); }}
                                    className="text-xs underline hover:text-[var(--chronos-accent)]"
                                >
                                    Clear all
                                </button>
                            </div>
                            <FacetFilter
                                title="Category"
                                options={categoryOptions}
                                selectedValues={selectedCategory}
                                onChange={handleCategoryChange}
                                collapsible
                                defaultOpenCount={8}
                            />
                            <div className="border-t border-gray-300 my-4"></div>
                            <FacetFilter
                                title="Media Type"
                                options={mediaTypeOptions}
                                selectedValues={selectedMediaType}
                                onChange={handleMediaTypeChange}
                            />
                            <div className="border-t border-gray-300 my-4"></div>
                            <FacetFilter
                                title="Author"
                                options={authorOptions}
                                selectedValues={selectedAuthor}
                                onChange={handleAuthorChange}
                                collapsible
                                defaultOpenCount={6}
                                collapsedByDefault
                            />
                            <div className="border-t border-gray-300 my-4"></div>
                            <FacetFilter
                                title="Language"
                                options={languageOptions}
                                selectedValues={selectedLanguage}
                                onChange={handleLanguageChange}
                                collapsible
                                defaultOpenCount={6}
                                collapsedByDefault
                            />
                            <div className="border-t border-gray-300 my-4"></div>
                            <FacetFilter
                                title="Market"
                                options={marketOptions}
                                selectedValues={selectedMarket}
                                onChange={handleMarketChange}
                                collapsible
                                defaultOpenCount={6}
                                collapsedByDefault
                            />
                        </div>
                    </aside>

                    {/* Main Content */}
                    <section className="lg:col-span-9 space-y-6">
                        {/* Generative summary placeholder */}
                        <div className="bg-gray-50 border-2 border-[var(--chronos-blue)] p-6 relative overflow-hidden neo-border">
                            <div className="absolute top-0 left-0 w-1 h-full bg-[var(--chronos-blue)]" />
                            <div className="flex items-start gap-3">
                                <div className="w-10 h-10 bg-[var(--chronos-blue)] text-white flex items-center justify-center rounded">
                                    <Sparkles className="w-5 h-5" />
                                </div>
                                <div>
                                    <h3 className="font-mono font-bold text-[var(--chronos-blue)] mb-2 flex items-center gap-2">
                                        Generative Answer <span className="text-[10px] bg-blue-100 px-1 rounded text-blue-800">BETA</span>
                                    </h3>
                                    <p className="font-sans text-base text-gray-800 leading-relaxed">
                                        {query
                                            ? `Highlights related to "${query}" from the Chronos archive. Select a result to dive deeper.`
                                            : 'Ask the archives anything—tech, off-world, policy—and see media, audio, and articles together.'}
                                    </p>
                                    {corrected && corrected !== query && (
                                        <p className="font-mono text-xs text-gray-600 mt-2">
                                            Did you mean: <button className="underline" onClick={() => window.location.href = `/search?q=${encodeURIComponent(corrected)}`}>{corrected}</button>
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Toolbar */}
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between font-mono text-xs text-gray-600 gap-2">
                            <span id="result-count">
                                {query.trim()
                                    ? `Showing ${results.length} results for "${query}"`
                                    : `Showing ${results.length} results (browse all)`}
                            </span>
                            <div className="flex items-center gap-2">
                                <span>SORT BY:</span>
                                <select
                                    id="sort"
                                    value={sortBy}
                                    onChange={(e) => setSortBy(e.target.value)}
                                    className="bg-transparent border-b border-gray-300 focus:outline-none text-[var(--chronos-black)]"
                                >
                                    <option value="relevance">RELEVANCE</option>
                                    <option value="newest">DATE</option>
                                    <option value="popularity">POPULARITY</option>
                                    <option value="rating">RATING</option>
                                </select>
                            </div>
                        </div>

                        {/* Results */}
                        {loading ? (
                            <div className="flex justify-center items-center h-64">
                                <Loader2 className="h-8 w-8 text-[var(--chronos-blue)] animate-spin" />
                            </div>
                        ) : error ? (
                            <div className="bg-red-50 border-2 border-red-400 p-4 neo-border">
                                <div className="flex">
                                    <div className="flex-shrink-0">
                                        <AlertCircle className="h-5 w-5 text-red-400" />
                                    </div>
                                    <div className="ml-3">
                                        <p className="text-sm text-red-700">{error}</p>
                                    </div>
                                </div>
                            </div>
                        ) : results.length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {results.map((result) => (
                                    <MediaCard key={result.id} result={result} attributionToken={attributionToken} />
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-16 border-2 border-dashed border-gray-300 neo-border bg-white">
                                <p className="text-gray-700 font-serif text-xl mb-2">No records found in the archives.</p>
                                <p className="text-gray-500 font-mono text-sm">Try a different query or adjust filters.</p>
                            </div>
                        )}
                    </section>
                </div>
            </div>
        </>
    );
}

export default function SearchPage() {
    return (
        <Suspense fallback={<div className="flex justify-center items-center h-screen"><Loader2 className="h-8 w-8 text-blue-500 animate-spin" /></div>}>
            <SearchContent />
        </Suspense>
    );
}
