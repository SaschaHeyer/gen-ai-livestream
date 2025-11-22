import React from 'react';
import SearchBar from '../components/SearchBar';
import MediaCard from '../components/MediaCard';

const featured = {
    title: 'Terraforming Project Phase 4: The Oceans Return',
    description: 'Scientists confirm the first stable bodies of water on the Red Planet since the Pre-Collapse era. What this means for real estate prices in the Valles Marineris.',
    uri: '/search?q=terraforming',
    thumbnail: 'https://images.unsplash.com/photo-1614726365723-49cfae947584?auto=format&fit=crop&w=1600&q=80',
    category: 'Off-World',
    mediaType: 'video',
    duration: '840s',
    publishTime: '2045-03-01T10:00:00Z',
    id: 'featured-video',
};

const briefing = {
    title: '"The distinction between virtual and physical reality has officially been dissolved by the UN."',
    duration: '260s',
};

const opinion = {
    title: "Why your AI assistant shouldn't have voting rights (yet).",
};

// Quick curated cards for the home feed (reuse API results shape)
const latestFeed = [
    {
        id: 'news_orbital_elevator',
        title: 'Orbital Elevator Construction Halted',
        description: 'Solar flares force a safety pause on the equatorial tether build.',
        uri: 'https://example.com/news/orbital-elevator',
        category: 'Earth Orbit',
        mediaType: 'news',
        publishTime: '2045-02-20T14:00:00Z',
        thumbnail: 'https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=1600&q=80',
    },
    {
        id: 'news_synthetic_meat',
        title: 'Synthetic Meat Prices Drop 15%',
        description: 'Breakthrough feedstocks slash costs across mega-farms feeding the stacks.',
        uri: 'https://example.com/news/synthetic-meat-prices',
        category: 'Biotech',
        mediaType: 'news',
        publishTime: '2045-02-12T12:30:00Z',
        thumbnail: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1600&q=80',
    },
    {
        id: 'news_mars_colony',
        title: 'Mars Colony Celebrates 10th Anniversary',
        description: 'Valles Marineris population tops 2 million; commerce booms.',
        uri: 'https://example.com/news/mars-colony-10',
        category: 'Off-World',
        mediaType: 'news',
        publishTime: '2045-01-25T06:45:00Z',
        thumbnail: 'https://images.unsplash.com/photo-1586773496207-2994b2893f4b?auto=format&fit=crop&w=1600&q=80',
    },
    {
        id: 'news_ai_senate',
        title: "AI Senate Passes 'Right to Compute' Bill",
        description: 'Global policy momentum builds for equitable compute access.',
        uri: 'https://example.com/news/right-to-compute',
        category: 'AI Policy',
        mediaType: 'news',
        publishTime: '2045-02-05T08:15:00Z',
        thumbnail: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=1600&q=80',
    },
    {
        id: 'news_quantum_coverage',
        title: 'Quantum Internet Reaches 99% Coverage',
        description: 'Entangled backbones make interplanetary latency nearly disappear.',
        uri: 'https://example.com/news/quantum-coverage',
        category: 'Quantum',
        mediaType: 'news',
        publishTime: '2045-02-22T09:00:00Z',
        thumbnail: 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?auto=format&fit=crop&w=1600&q=80',
    },
    {
        id: 'audio_synthetic_politics',
        title: 'The Rise of Synthetic Politics',
        description: 'An AI runs for mayor in Neo-Tokyo. What could go right?',
        uri: 'https://storage.googleapis.com/cloud-samples-data/audio/synthetic_politics.mp3',
        category: 'Governance',
        mediaType: 'audio',
        duration: '2700s',
        thumbnail: 'https://images.unsplash.com/photo-1591453089816-0fbb971b454c?auto=format&fit=crop&w=1600&q=80',
    },
];

export default function Home() {
    return (
        <div className="bg-[var(--chronos-white)] text-[var(--chronos-black)]">
            <div className="max-w-6xl mx-auto px-4 py-10 space-y-10">
                {/* Hero Section */}
                <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-fade-in">
                    <div className="lg:col-span-8 neo-border bg-white p-0 relative group cursor-pointer overflow-hidden">
                        <div className="absolute top-4 left-4 z-10 bg-[var(--chronos-accent)] text-white font-mono text-xs px-2 py-1 font-bold">
                            TOP STORY
                        </div>
                        <img
                            src={featured.thumbnail}
                            alt={featured.title}
                            className="w-full h-[380px] object-cover grayscale group-hover:grayscale-0 transition-all duration-500"
                        />
                        <div className="p-6 border-t-2 border-[var(--chronos-black)] bg-white relative z-10">
                            <div className="flex items-center gap-2 mb-2 text-xs font-mono text-gray-500">
                                <span>14 MIN AGO</span>
                                <span>•</span>
                                <span>VIDEO REPORT</span>
                            </div>
                            <h2 className="font-serif text-4xl md:text-5xl font-bold mb-4 leading-tight group-hover:text-[var(--chronos-accent)] transition-colors">
                                {featured.title}
                            </h2>
                            <p className="font-sans text-lg leading-relaxed border-l-4 border-gray-200 pl-4">
                                {featured.description}
                            </p>
                        </div>
                    </div>

                    <div className="lg:col-span-4 flex flex-col gap-6">
                        <div className="bg-black text-white p-6 neo-border h-full flex flex-col justify-center">
                            <h3 className="font-mono text-[var(--chronos-accent)] mb-2">DAILY BRIEFING</h3>
                            <p className="font-serif text-2xl leading-tight mb-4">{briefing.title}</p>
                            <div className="mt-auto pt-4 border-t border-gray-800 flex justify-between items-center font-mono text-xs">
                                <span>AUDIO • {Math.round(parseInt(briefing.duration.replace('s', '')) / 60)} MIN</span>
                                <button className="bg-white text-black rounded-full p-2 hover:bg-[var(--chronos-accent)] hover:text-white transition-colors">
                                    ▶
                                </button>
                            </div>
                        </div>
                        <div className="bg-white p-6 neo-border h-full relative overflow-hidden">
                            <div className="absolute -right-4 -top-4 text-9xl font-serif text-gray-100 z-0">?</div>
                            <h3 className="relative z-10 font-mono text-xs font-bold mb-2 text-gray-500">OPINION</h3>
                            <a href="/search" className="relative z-10 font-serif text-2xl font-bold hover:underline decoration-4 decoration-[var(--chronos-accent)] underline-offset-4">
                                {opinion.title}
                            </a>
                        </div>
                    </div>
                </section>

                {/* Search CTA */}
                <section className="neo-border bg-white p-6">
                    <h3 className="font-mono text-sm text-gray-600 mb-2">ARCHIVE SEARCH</h3>
                    <SearchBar />
                </section>

                {/* Latest Feed */}
                <section>
                    <div className="flex items-end justify-between mb-6 border-b-2 border-[var(--chronos-black)] pb-2">
                        <h3 className="font-mono text-2xl font-bold uppercase">Latest Feed</h3>
                        <div className="flex gap-2">
                            <button className="w-8 h-8 border border-[var(--chronos-black)] flex items-center justify-center hover:bg-[var(--chronos-black)] hover:text-white transition-colors">▢</button>
                            <button className="w-8 h-8 border border-[var(--chronos-black)] flex items-center justify-center hover:bg-[var(--chronos-black)] hover:text-white transition-colors">≡</button>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {latestFeed.map((item) => (
                            <MediaCard key={item.id} result={item} />
                        ))}
                    </div>
                </section>
            </div>
        </div>
    );
}
