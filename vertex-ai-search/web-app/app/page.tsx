'use client';

import React, { useEffect, useState } from 'react';
import SearchBar from '../components/SearchBar';
import MediaCard from '../components/MediaCard';
import Link from 'next/link';
import { Loader2, Grid, List } from 'lucide-react';
import { useUserEvents } from '../hooks/useUserEvents';
import { useUserPreferences } from '../hooks/useUserPreferences';

export default function Home() {
    const [latest, setLatest] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [layout, setLayout] = useState<'grid' | 'list'>('grid');
    const { userPseudoId, userId } = useUserEvents();
    const { languageCodes, countryCode } = useUserPreferences();

    useEffect(() => {
        const fetchLatest = async () => {
            try {
                setLoading(true);
                const res = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: '',
                        orderBy: 'available_time desc',
                        pageSize: 9,
                        userPseudoId,
                        userId,
                        userCountryCode: countryCode,
                        languageCodes,
                    }),
                });
                if (!res.ok) throw new Error('Failed to fetch latest feed');
                const data = await res.json();
                setLatest(data.results || []);
            } catch (e: any) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        };
        fetchLatest();
    }, [userPseudoId, userId, languageCodes, countryCode]);

    const featured = latest[0];
    const briefing = latest.find((i) => i.mediaType === 'audio');
    const opinion = latest.find((i) => i.mediaType === 'news' && i.id !== featured?.id);
    const rest = latest.filter((i) => i !== featured).slice(0, 9);

    return (
        <div className="bg-[var(--chronos-white)] text-[var(--chronos-black)]">
            <div className="max-w-6xl mx-auto px-4 py-10 space-y-10">
                {/* Hero Section */}
                <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-fade-in">
                    <Link
                        href={featured ? `/item/${featured.id}` : '#'}
                        className="lg:col-span-8 neo-border bg-white p-0 relative group cursor-pointer overflow-hidden block"
                    >
                        <div className="absolute top-4 left-4 z-10 bg-[var(--chronos-accent)] text-white font-mono text-xs px-2 py-1 font-bold">
                            TOP STORY
                        </div>
                        {featured?.thumbnail && (
                            <img
                                src={featured.thumbnail}
                                alt={featured.title}
                                className="w-full h-[380px] object-cover grayscale group-hover:grayscale-0 transition-all duration-500"
                            />
                        )}
                        <div className="p-6 border-t-2 border-[var(--chronos-black)] bg-white relative z-10">
                            <div className="flex items-center gap-2 mb-2 text-xs font-mono text-gray-500">
                                <span>FRESH</span>
                                <span>•</span>
                                <span>{featured?.mediaType?.toUpperCase() || 'MEDIA'}</span>
                            </div>
                            <h2 className="font-serif text-4xl md:text-5xl font-bold mb-4 leading-tight group-hover:text-[var(--chronos-accent)] transition-colors">
                                {featured?.title || 'Loading top story...'}
                            </h2>
                            <p className="font-sans text-lg leading-relaxed border-l-4 border-gray-200 pl-4">
                                {featured?.description || 'Awaiting fresh content from the archives.'}
                            </p>
                        </div>
                    </Link>

                    <div className="lg:col-span-4 flex flex-col gap-6">
                        <div className="bg-black text-white p-6 neo-border h-full flex flex-col justify-center">
                            <h3 className="font-mono text-[var(--chronos-accent)] mb-2">DAILY BRIEFING</h3>
                            <p className="font-serif text-2xl leading-tight mb-4">{briefing?.title || 'Briefing loading...'}</p>
                            <div className="mt-auto pt-4 border-t border-gray-800 flex justify-between items-center font-mono text-xs">
                                <span>AUDIO • {briefing?.duration || '...'} </span>
                                <button className="bg-white text-black rounded-full p-2 hover:bg-[var(--chronos-accent)] hover:text-white transition-colors">
                                    ▶
                                </button>
                            </div>
                        </div>
                        <div className="bg-white p-6 neo-border h-full relative overflow-hidden">
                            <div className="absolute -right-4 -top-4 text-9xl font-serif text-gray-100 z-0">?</div>
                            <h3 className="relative z-10 font-mono text-xs font-bold mb-2 text-gray-500">OPINION</h3>
                            <Link
                                href={opinion ? `/item/${opinion.id}` : '#'}
                                className="relative z-10 font-serif text-2xl font-bold hover:underline decoration-4 decoration-[var(--chronos-accent)] underline-offset-4"
                            >
                                {opinion?.title || 'Explore the archives.'}
                            </Link>
                        </div>
                    </div>
                </section>

                {/* Latest Feed */}
                <section>
                    <div className="flex items-end justify-between mb-6 border-b-2 border-[var(--chronos-black)] pb-2">
                        <h3 className="font-mono text-2xl font-bold uppercase">Latest Feed</h3>
                        <div className="flex gap-2">
                            <button
                                aria-label="Grid view"
                                onClick={() => setLayout('grid')}
                                className={`w-8 h-8 border border-[var(--chronos-black)] flex items-center justify-center hover:bg-[var(--chronos-black)] hover:text-white transition-colors ${
                                    layout === 'grid' ? 'bg-[var(--chronos-black)] text-white' : ''
                                }`}
                            >
                                <Grid className="w-4 h-4" strokeWidth={2} />
                            </button>
                            <button
                                aria-label="List view"
                                onClick={() => setLayout('list')}
                                className={`w-8 h-8 border border-[var(--chronos-black)] flex items-center justify-center hover:bg-[var(--chronos-black)] hover:text-white transition-colors ${
                                    layout === 'list' ? 'bg-[var(--chronos-black)] text-white' : ''
                                }`}
                            >
                                <List className="w-4 h-4" strokeWidth={2} />
                            </button>
                        </div>
                    </div>

                    {loading ? (
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                            <Loader2 className="w-4 h-4 animate-spin" /> Loading latest from Vertex AI Search...
                        </div>
                    ) : error ? (
                        <div className="text-sm text-red-600">{error}</div>
                    ) : (
                        <>
                            {layout === 'grid' ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {rest.map((item) => (
                                        <MediaCard key={item.id} result={item} />
                                    ))}
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {rest.map((item) => (
                                        <MediaCard key={item.id} result={item} />
                                    ))}
                                </div>
                            )}
                        </>
                    )}
                </section>
            </div>
        </div>
    );
}
