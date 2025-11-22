 'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { PlayCircle, FileText, Headphones, Clock, ArrowUpRight } from 'lucide-react';
import { useUserEvents } from '../hooks/useUserEvents';

interface MediaCardProps {
    result: {
        id: string;
        title: string;
        description: string;
        uri: string;
        category?: string;
        publishTime?: string;
        mediaType?: string;
        thumbnail?: string;
        duration?: string;
    };
    attributionToken?: string | null;
}

const formatDuration = (duration?: string) => {
    if (!duration) return null;
    if (duration.endsWith('s')) {
        const seconds = parseInt(duration.replace('s', ''), 10);
        const minutes = Math.floor(seconds / 60);
        const remaining = seconds % 60;
        return `${minutes}m ${remaining}s`;
    }
    return duration;
};

const MediaCard: React.FC<MediaCardProps> = ({ result, attributionToken }) => {
    const isVideo = result.mediaType === 'video';
    const isAudio = result.mediaType === 'audio';
    const { sendEvent } = useUserEvents();
    const router = useRouter();

    const handleClick = () => {
        sendEvent({ eventType: 'view-item', documents: [result.id], attributionToken });
        if (isVideo || isAudio) {
            sendEvent({
                eventType: 'media-play',
                documents: [result.id],
                attributionToken,
                mediaInfo: {
                    mediaProgressDuration: result.duration,
                    mediaSessionType: isVideo ? 'VIDEO' : 'AUDIO',
                },
            });
        }
    };

    const goToDetail = () => {
        handleClick();
        router.push(`/item/${result.id}`);
    };

    return (
        <div
            className="neo-border bg-white flex flex-col group cursor-pointer overflow-hidden h-full transition-all hover:shadow-[6px_6px_0px_var(--chronos-blue)]"
            onClick={goToDetail}
            role="button"
            tabIndex={0}
        >
            <div className="relative overflow-hidden aspect-video">
                <div className="absolute top-2 left-2 z-10">
                    <span className="bg-chronos-black text-white px-2 py-1 text-[10px] font-mono uppercase flex items-center gap-1">
                        {isVideo ? <PlayCircle className="w-3 h-3" /> : isAudio ? <Headphones className="w-3 h-3" /> : <FileText className="w-3 h-3" />} {isVideo ? 'Video' : isAudio ? 'Audio' : 'Article'}
                    </span>
                </div>
                {result.thumbnail ? (
                    <img
                        src={result.thumbnail}
                        alt={result.title}
                        className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500"
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
                        {isVideo ? <PlayCircle className="h-12 w-12 text-blue-400" /> : isAudio ? <Headphones className="h-12 w-12 text-indigo-400" /> : <FileText className="h-12 w-12 text-indigo-400" />}
                    </div>
                )}
                {(result.duration || result.publishTime) && (
                    <div className="absolute bottom-2 left-2 text-[10px] font-mono text-white bg-black/80 px-2 py-1 flex items-center gap-1">
                        {result.duration ? <><Clock className="w-3 h-3" /> {formatDuration(result.duration)}</> : null}
                    </div>
                )}
            </div>
            <div className="p-5 flex flex-col flex-grow">
                <div className="flex justify-between items-center mb-2 text-xs font-mono text-gray-500 uppercase">
                    <span>{result.category || 'General'}</span>
                    {result.publishTime && <span>{new Date(result.publishTime).toLocaleDateString()}</span>}
                </div>
                <h3 className="font-serif text-2xl font-bold leading-tight mb-2 group-hover:text-chronos-accent transition-colors line-clamp-2">
                    <Link href={`/item/${result.id}`} className="focus:outline-none" onClick={(e) => { e.stopPropagation(); goToDetail(); }}>
                        {result.title}
                    </Link>
                </h3>
                <p className="font-sans text-sm text-gray-600 leading-relaxed mb-4 flex-grow line-clamp-3">
                    {result.description}
                </p>

                <div className="pt-4 border-t border-gray-100 flex items-center justify-between font-mono text-xs font-bold text-gray-700">
                    <span>{isVideo ? 'Watch' : isAudio ? 'Listen' : 'Read'}</span>
                    <span className="flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                        Open <ArrowUpRight className="w-3 h-3" />
                    </span>
                </div>
            </div>
        </div>
    );
};

export default MediaCard;
