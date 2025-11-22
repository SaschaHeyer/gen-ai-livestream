import React from 'react';
import Layout from '../components/Layout';
import SearchBar from '../components/SearchBar';
import { Play, Zap, TrendingUp } from 'lucide-react';

export default function Home() {
    return (
        <>
            {/* Hero Section */}
            <div className="relative bg-white overflow-hidden">
                <div className="max-w-7xl mx-auto">
                    <div className="relative z-10 pb-8 bg-white sm:pb-16 md:pb-20 lg:max-w-2xl lg:w-full lg:pb-28 xl:pb-32">
                        <main className="mt-10 mx-auto max-w-7xl px-4 sm:mt-12 sm:px-6 md:mt-16 lg:mt-20 lg:px-8 xl:mt-28">
                            <div className="sm:text-center lg:text-left">
                                <h1 className="text-4xl tracking-tight font-extrabold text-gray-900 sm:text-5xl md:text-6xl">
                                    <span className="block xl:inline">Discover the future of</span>{' '}
                                    <span className="block text-blue-600 xl:inline">cloud technology</span>
                                </h1>
                                <p className="mt-3 text-base text-gray-500 sm:mt-5 sm:text-lg sm:max-w-xl sm:mx-auto md:mt-5 md:text-xl lg:mx-0">
                                    Explore our vast library of videos, articles, and insights powered by Vertex AI Media Search. Find exactly what you need, faster than ever.
                                </p>
                                <div className="mt-8 sm:mt-10">
                                    <SearchBar />
                                </div>
                                <div className="mt-5 sm:mt-8 sm:flex sm:justify-center lg:justify-start">
                                    <div className="rounded-md shadow">
                                        <a href="/search" className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 md:py-4 md:text-lg md:px-10">
                                            Browse All
                                        </a>
                                    </div>
                                    <div className="mt-3 sm:mt-0 sm:ml-3">
                                        <a href="#" className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 md:py-4 md:text-lg md:px-10">
                                            Live Demo
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </main>
                    </div>
                </div>
                <div className="lg:absolute lg:inset-y-0 lg:right-0 lg:w-1/2 bg-gray-50">
                    <div className="h-56 w-full sm:h-72 md:h-96 lg:w-full lg:h-full flex items-center justify-center">
                        {/* Abstract Visual Representation */}
                        <div className="grid grid-cols-2 gap-4 p-8 opacity-80">
                            <div className="bg-blue-100 p-6 rounded-2xl transform rotate-3 hover:rotate-0 transition-transform duration-500">
                                <Play className="h-12 w-12 text-blue-500 mb-2" />
                                <div className="h-2 w-24 bg-blue-200 rounded mb-1"></div>
                                <div className="h-2 w-16 bg-blue-200 rounded"></div>
                            </div>
                            <div className="bg-indigo-100 p-6 rounded-2xl transform -rotate-2 hover:rotate-0 transition-transform duration-500 mt-8">
                                <Zap className="h-12 w-12 text-indigo-500 mb-2" />
                                <div className="h-2 w-24 bg-indigo-200 rounded mb-1"></div>
                                <div className="h-2 w-16 bg-indigo-200 rounded"></div>
                            </div>
                            <div className="bg-purple-100 p-6 rounded-2xl transform -rotate-3 hover:rotate-0 transition-transform duration-500">
                                <TrendingUp className="h-12 w-12 text-purple-500 mb-2" />
                                <div className="h-2 w-24 bg-purple-200 rounded mb-1"></div>
                                <div className="h-2 w-16 bg-purple-200 rounded"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Features Section */}
            <div className="py-12 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="lg:text-center">
                        <h2 className="text-base text-blue-600 font-semibold tracking-wide uppercase">Features</h2>
                        <p className="mt-2 text-3xl leading-8 font-extrabold tracking-tight text-gray-900 sm:text-4xl">
                            Powered by Vertex AI
                        </p>
                        <p className="mt-4 max-w-2xl text-xl text-gray-500 lg:mx-auto">
                            Experience the next generation of media search with semantic understanding and multimodal capabilities.
                        </p>
                    </div>
                </div>
            </div>
        </>
    );
}
