'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { ArrowLeft, Clock, Headphones, PlayCircle, Sparkles, Share2 } from 'lucide-react';
import Link from 'next/link';
import { useUserEvents } from '../../hooks/useUserEvents';

type DocData = {
    id: string;
    data: any;
};

export default function ItemPage() {
    const params = useParams();
    const id = params?.id as string;
    const [doc, setDoc] = useState<DocData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { sendEvent } = useUserEvents();

    useEffect(() => {
        const fetchDoc = async () => {
            try {
                const res = await fetch(`/api/document/${id}`);
                if (!res.ok) throw new Error('Not found');
                const data = await res.json();
                setDoc(data);
                // view-item on load
                sendEvent({ eventType: 'view-item', documents: [id] });
            } catch (e: any) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        };
        if (id) fetchDoc();
    }, [id, sendEvent]);

    if (loading) return <div className="max-w-5xl mx-auto px-4 py-10">Loading...</div>;
    if (error || !doc) return <div className="max-w-5xl mx-auto px-4 py-10 text-red-600">Not found.</div>;

    const data = doc.data || {};
    const mediaType = data.content_type || data.media_type || 'news';
    const image = data.images?.[0]?.uri || data.image_uri;
    const published = data.available_time ? new Date(data.available_time).toLocaleDateString() : '';

    const onPlay = () => {
        sendEvent({
            eventType: 'media-play',
            documents: [id],
            mediaInfo: { mediaProgressDuration: data.duration, mediaSessionType: mediaType === 'audio' ? 'AUDIO' : 'VIDEO' },
        });
        sendEvent({
            eventType: 'media-complete',
            documents: [id],
            mediaInfo: { mediaProgressDuration: data.duration, mediaProgressPercentage: 1.0, mediaSessionType: mediaType === 'audio' ? 'AUDIO' : 'VIDEO' },
        });
    };

    const ArticleView = () => (
        <article className="grid grid-cols-1 lg:grid-cols-12 gap-12">
            <div className="lg:col-span-8">
                <header className="mb-8">
                    <div className="flex items-center gap-3 mb-4 font-mono text-xs text-gray-500 uppercase">
                        <span className="bg-chronos-black text-white px-2 py-1">ARTICLE</span>
                        <span>{data.categories?.[0] || 'General'}</span>
                        <span>//</span>
                        <span>{published}</span>
                    </div>
                    <h1 className="font-serif text-4xl md:text-5xl font-bold leading-tight mb-6">{data.title}</h1>
                    <div className="flex items-center justify-between border-y border-gray-200 py-4">
                        <div className="text-sm">
                            <p className="font-bold font-sans">{data.author || 'Chronos Staff'}</p>
                            <p className="text-gray-500 font-mono text-xs">Senior Correspondent</p>
                        </div>
                        <div className="font-mono text-xs text-gray-500 flex gap-4">
                            {data.duration && (
                                <span className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" /> {data.duration}
                                </span>
                            )}
                            <button className="hover:text-chronos-accent">
                                <Share2 className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </header>
                {image && (
                    <img src={image} className="w-full aspect-video object-cover mb-8 neo-border grayscale hover:grayscale-0 transition-all duration-700" />
                )}
                <div className="prose font-serif text-gray-800 max-w-none">
                    <p className="font-sans text-xl leading-relaxed mb-8 text-black font-medium">
                        {data.description}
                    </p>
                    <p>
                        This story continues in the Chronos archives. Follow the source link below for the full report.
                    </p>
                </div>
                {data.uri && (
                    <div className="mt-6">
                        <a
                            href={data.uri}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-4 py-2 border border-[var(--chronos-black)] font-mono text-sm hover:bg-[var(--chronos-black)] hover:text-white inline-flex items-center gap-2"
                        >
                            Open Source
                        </a>
                    </div>
                )}
            </div>
            <aside className="lg:col-span-4 space-y-6">
                <div className="bg-blue-50 border border-chronos-blue p-6">
                    <h4 className="font-mono text-xs font-bold text-chronos-blue mb-2 flex items-center gap-2">
                        <Sparkles className="w-4 h-4" /> VERTEX CONTEXT
                    </h4>
                    <p className="font-sans text-sm leading-relaxed text-gray-700">
                        Category <strong>{data.categories?.[0] || 'General'}</strong> is trending in the Chronos index. Freshness: {published || 'n/a'}.
                    </p>
                </div>
            </aside>
        </article>
    );

    const VideoView = () => (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-9">
                <div className="w-full aspect-video bg-black neo-border relative group mb-6 flex items-center justify-center">
                    {image && <img src={image} className="absolute inset-0 w-full h-full object-cover opacity-60" />}
                    <a
                        href={data.uri}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={onPlay}
                        className="relative z-10 w-20 h-20 bg-white rounded-full flex items-center justify-center hover:scale-110 transition-transform group-hover:bg-chronos-accent group-hover:text-white"
                    >
                        <PlayCircle className="w-8 h-8 ml-1" />
                    </a>
                    <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent text-white flex justify-between items-end">
                        <div className="font-mono text-xs">{mediaType.toUpperCase()}</div>
                        {data.duration && <div className="font-mono text-xs">{data.duration}</div>}
                    </div>
                </div>
                <h1 className="font-serif text-3xl font-bold mb-2">{data.title}</h1>
                <p className="font-sans text-gray-700 mb-4">{data.description}</p>
            </div>
            <div className="lg:col-span-3 space-y-4">
                <h4 className="font-mono font-bold text-lg">UP NEXT</h4>
                <p className="text-sm text-gray-600">Explore more results from the search page.</p>
            </div>
        </div>
    );

    const AudioView = () => (
        <div className="max-w-4xl">
            <div className="bg-black text-white p-8 neo-border relative overflow-hidden">
                {image && <img src={image} className="absolute inset-0 w-full h-full object-cover opacity-20 blur-sm" />}
                <div className="relative z-10 flex flex-col items-center text-center">
                    {image && (
                        <div className="w-48 h-48 mb-8 neo-border bg-gray-800 overflow-hidden relative shadow-2xl">
                            <img src={image} className="w-full h-full object-cover" />
                        </div>
                    )}
                    <h1 className="font-serif text-3xl md:text-4xl font-bold mb-4">{data.title}</h1>
                    <p className="font-mono text-chronos-accent mb-6">{data.host || 'AI Narrator'}</p>
                    <a
                        href={data.uri}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={onPlay}
                        className="px-4 py-2 bg-white text-black rounded-full font-mono text-sm hover:bg-[var(--chronos-accent)] hover:text-white flex items-center gap-2"
                    >
                        <Headphones className="w-4 h-4" /> Listen
                    </a>
                </div>
            </div>
        </div>
    );

    return (
        <div className="max-w-6xl mx-auto px-4 py-10 space-y-6">
            <div className="mb-4">
                <Link href="/search" className="flex items-center gap-2 text-sm font-mono hover:text-[var(--chronos-accent)]">
                    <ArrowLeft className="w-4 h-4" /> BACK
                </Link>
            </div>
            {mediaType === 'video' ? (
                <VideoView />
            ) : mediaType === 'audio' ? (
                <AudioView />
            ) : (
                <ArticleView />
            )}
        </div>
    );
}
