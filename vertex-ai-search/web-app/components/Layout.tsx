import React from 'react';
import Link from 'next/link';
import SearchBar from './SearchBar';

interface LayoutProps {
    children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
    return (
        <div className="min-h-screen bg-[var(--chronos-white)] text-[var(--chronos-black)] font-sans">
            {/* Breaking news ticker */}
            <div className="bg-[var(--chronos-black)] text-[var(--chronos-white)] py-2 border-b border-[var(--chronos-black)] font-mono text-xs uppercase overflow-hidden whitespace-nowrap relative z-50">
                <div className="animate-marquee inline-block">
                    +++ ORBITAL ELEVATOR CONSTRUCTION HALTED DUE TO SOLAR FLARES +++ SYNTHETIC MEAT PRICES DROP 15% +++ MARS COLONY CELEBRATES 10TH ANNIVERSARY +++ AI SENATE PASSES "RIGHT TO COMPUTE" BILL +++ QUANTUM INTERNET REACHES 99% COVERAGE +++
                </div>
                <div className="animate-marquee inline-block absolute top-2">
                    +++ ORBITAL ELEVATOR CONSTRUCTION HALTED DUE TO SOLAR FLARES +++ SYNTHETIC MEAT PRICES DROP 15% +++ MARS COLONY CELEBRATES 10TH ANNIVERSARY +++ AI SENATE PASSES "RIGHT TO COMPUTE" BILL +++ QUANTUM INTERNET REACHES 99% COVERAGE +++
                </div>
            </div>

            {/* Header */}
            <header className="sticky top-0 z-40 bg-[var(--chronos-white)] border-b-2 border-[var(--chronos-black)]">
                <div className="max-w-6xl mx-auto px-4 py-4">
                    <div className="flex flex-col lg:flex-row items-center justify-between gap-4">
                        <Link href="/" className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-[var(--chronos-black)] flex items-center justify-center text-white font-serif font-bold text-xl">C</div>
                            <h1 className="font-serif text-3xl font-bold tracking-tighter">CHRONOS DAILY</h1>
                            <span className="text-xs font-mono bg-[var(--chronos-accent)] text-white px-1 ml-2">2045 ED.</span>
                        </Link>

                        <div className="w-full lg:w-1/2 relative">
                            <SearchBar />
                        </div>

                        <nav className="hidden lg:flex gap-6 font-mono text-sm font-bold">
                            <Link href="/search" className="hover:text-[var(--chronos-accent)] hover:underline decoration-2 underline-offset-4">POLITICS</Link>
                            <Link href="/search" className="hover:text-[var(--chronos-accent)] hover:underline decoration-2 underline-offset-4">TECH</Link>
                            <Link href="/search" className="hover:text-[var(--chronos-accent)] hover:underline decoration-2 underline-offset-4">OFF-WORLD</Link>
                            <span className="flex items-center gap-2 hover:text-[var(--chronos-accent)] cursor-pointer">LOGIN</span>
                        </nav>
                    </div>
                </div>
            </header>

            <main>{children}</main>

            <footer className="bg-[var(--chronos-black)] text-white py-12 border-t-4 border-[var(--chronos-accent)] mt-12">
                <div className="max-w-6xl mx-auto px-4 text-center">
                    <div className="font-serif text-3xl font-bold mb-6">THE CHRONOS DAILY</div>
                    <div className="flex justify-center gap-8 font-mono text-sm mb-8">
                        <a className="hover:text-[var(--chronos-accent)]" href="#">ARCHIVES</a>
                        <a className="hover:text-[var(--chronos-accent)]" href="#">ADVERTISE</a>
                        <a className="hover:text-[var(--chronos-accent)]" href="#">API DOCS</a>
                        <a className="hover:text-[var(--chronos-accent)]" href="#">LEGAL</a>
                    </div>
                    <div className="text-gray-400 text-xs font-mono">
                        &copy; 2045 CHRONOS MEDIA GROUP. POWERED BY VERTEX AI SEARCH.
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default Layout;
