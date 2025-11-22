'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Layout from '../../components/Layout';
import SearchBar from '../../components/SearchBar';
import VideoCard from '../../components/VideoCard';
import FacetFilter from '../../components/FacetFilter';
import { Loader2, AlertCircle } from 'lucide-react';

function SearchContent() {
    const searchParams = useSearchParams();
    const query = searchParams.get('q') || '';

    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedCategory, setSelectedCategory] = useState<string[]>([]);
    const [selectedMediaType, setSelectedMediaType] = useState<string[]>([]);
    const [sortBy, setSortBy] = useState<string>('relevance');
    const [facets, setFacets] = useState<any[]>([]);

    useEffect(() => {
        const fetchResults = async () => {
            setLoading(true);
            setError(null);
            try {
                // Construct filter string
                const filters = [];
                if (selectedCategory.length > 0) {
                    filters.push(`categories: ANY("${selectedCategory.join('","')}")`);
                }
                if (selectedMediaType.length > 0) {
                    filters.push(`content_type: ANY("${selectedMediaType.join('","')}")`);
                }
                const filterString = filters.join(' AND ');

                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query,
                        filter: filterString,
                        orderBy: sortBy === 'newest' ? 'available_time desc' : undefined
                    }),
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch results');
                }

                const data = await response.json();
                setResults(data.results);
                setFacets(data.facets || []);
            } catch (err) {
                setError('An error occurred while searching. Please try again.');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchResults();
    }, [query, selectedCategory, selectedMediaType, sortBy]);

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

    // Human-friendly labels for categories/content types
    const prettify = (text: string) =>
        text
            .split(/[-_]/)
            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
            .join(' ');

    const formatCategoryLabel = (value: string) => {
        const parts = value.split('>').map((p) => p.trim());
        const leaf = parts[parts.length - 1] || value;
        const parent = parts.length > 1 ? parts[parts.length - 2] : '';
        const leafPretty = prettify(leaf);
        const parentPretty = parent ? prettify(parent) : '';
        return parentPretty ? `${leafPretty} (${parentPretty})` : leafPretty;
    };

    // Helper to transform API facets to UI options with formatted labels
    const getFacetOptions = (key: string) => {
        const facet = facets.find((f: any) => f.key === key);
        if (!facet || !facet.values) return [];
        return facet.values.map((v: any) => {
            const raw = v.value as string;
            const label =
                key === 'categories'
                    ? formatCategoryLabel(raw)
                    : key === 'content_type'
                        ? prettify(raw)
                        : raw;
            return { label, value: raw, count: v.count };
        });
    };

    const categoryOptions = getFacetOptions('categories');
    const mediaTypeOptions = getFacetOptions('content_type');

    return (
        <>
            <div className="bg-white border-b border-gray-200">
                <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-6">Search Results</h1>
                    <SearchBar initialQuery={query} />
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="flex flex-col lg:flex-row gap-8">
                    {/* Sidebar / Facets */}
                    <div className="w-full lg:w-64 flex-shrink-0">
                        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 sticky top-24">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-lg font-medium text-gray-900">Filters</h2>
                                <button
                                    onClick={() => { setSelectedCategory([]); setSelectedMediaType([]); }}
                                    className="text-sm text-blue-600 hover:text-blue-800"
                                >
                                    Clear all
                                </button>
                            </div>
                            <FacetFilter
                                title="Category"
                                options={categoryOptions}
                                selectedValues={selectedCategory}
                                onChange={handleCategoryChange}
                            />
                            <div className="border-t border-gray-100 my-4"></div>
                            <FacetFilter
                                title="Media Type"
                                options={mediaTypeOptions}
                                selectedValues={selectedMediaType}
                                onChange={handleMediaTypeChange}
                            />
                        </div>
                    </div>

                    {/* Main Content */}
                    <div className="flex-1">
                        {/* Toolbar */}
                        <div className="flex items-center justify-between mb-6">
                            <p className="text-sm text-gray-500">
                                Showing <span className="font-medium text-gray-900">{results.length}</span> results for "<span className="font-medium text-gray-900">{query}</span>"
                            </p>
                            <div className="flex items-center">
                                <label htmlFor="sort" className="mr-2 text-sm text-gray-700">Sort by:</label>
                                <select
                                    id="sort"
                                    value={sortBy}
                                    onChange={(e) => setSortBy(e.target.value)}
                                    className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                                >
                                    <option value="relevance">Relevance</option>
                                    <option value="newest">Newest</option>
                                </select>
                            </div>
                        </div>

                        {/* Results Grid */}
                        {loading ? (
                            <div className="flex justify-center items-center h-64">
                                <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
                            </div>
                        ) : error ? (
                            <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded-md">
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
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                                {results.map((result) => (
                                    <VideoCard key={result.id} result={result} />
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
                                <p className="text-gray-500 text-lg">No results found for "{query}"</p>
                                <p className="text-gray-400 mt-2">Try adjusting your search or filters.</p>
                            </div>
                        )}
                    </div>
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
