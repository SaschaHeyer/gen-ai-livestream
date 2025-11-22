import React from 'react';
import Link from 'next/link';
import { PlayCircle, FileText, Headphones, Calendar } from 'lucide-react';

interface VideoCardProps {
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

const VideoCard: React.FC<VideoCardProps> = ({ result }) => {
    const isVideo = result.mediaType === 'video';
    const isAudio = result.mediaType === 'audio';

    return (
        <div className="group flex flex-col bg-white rounded-lg shadow-sm hover:shadow-lg transition-shadow overflow-hidden border border-gray-100">
            <div className="relative aspect-video bg-gray-200 overflow-hidden">
                {result.thumbnail ? (
                    <img
                        src={result.thumbnail}
                        alt={result.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
                        {isVideo ? <PlayCircle className="h-12 w-12 text-blue-400" /> : isAudio ? <Headphones className="h-12 w-12 text-indigo-400" /> : <FileText className="h-12 w-12 text-indigo-400" />}
                    </div>
                )}
                {result.duration && (
                    <div className="absolute bottom-2 right-2 bg-black bg-opacity-70 text-white text-xs px-2 py-1 rounded">
                        {formatDuration(result.duration)}
                    </div>
                )}
            </div>
            <div className="p-4 flex flex-col flex-grow">
                <div className="flex items-center justify-between mb-2">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${isVideo ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'}`}>
                        {result.category || 'General'}
                    </span>
                    {result.publishTime && (
                        <div className="flex items-center text-xs text-gray-500">
                            <Calendar className="h-3 w-3 mr-1" />
                            {new Date(result.publishTime).toLocaleDateString()}
                        </div>
                    )}
                </div>
                <h3 className="text-lg font-medium text-gray-900 group-hover:text-blue-600 line-clamp-2 mb-1">
                    <Link href={result.uri} className="focus:outline-none">
                        {result.title}
                    </Link>
                </h3>
                <p className="text-sm text-gray-500 line-clamp-3 mb-4 flex-grow">
                    {result.description}
                </p>

                <div className="mt-auto pt-4 border-t border-gray-50 flex items-center justify-between">
                    <div className="flex items-center text-xs text-gray-400">
                        {isVideo ? 'Video' : isAudio ? 'Audio' : 'Article'}
                    </div>
                    <button className="text-blue-600 text-sm font-medium hover:text-blue-800">
                        {isVideo ? 'Watch Now' : isAudio ? 'Listen' : 'Read More'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default VideoCard;
