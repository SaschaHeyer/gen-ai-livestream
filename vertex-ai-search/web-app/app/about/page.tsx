'use client';

import Link from 'next/link';

export default function About() {
    return (
        <div className="max-w-5xl mx-auto px-4 py-10 space-y-10 text-[var(--chronos-black)]">
            <header className="space-y-2">
                <p className="font-mono text-sm text-gray-600">Vertex AI Media Search Demo</p>
                <h1 className="font-serif text-4xl font-bold">About the Chronos Daily Experience</h1>
                <p className="font-sans text-lg text-gray-700">
                    This site is powered by Vertex AI Media Search and shows how to blend multimodal search, autocomplete, facets, detail pages, and user-event tracking in a stylized news experience.
                </p>
            </header>

            <section className="neo-border bg-white p-6 space-y-3">
                <h2 className="font-mono text-sm text-gray-600">Key Capabilities</h2>
                <ul className="list-disc pl-5 space-y-2 font-sans text-sm">
                    <li><strong>Media Search API</strong>: Live queries to a media data store with category and media-type facets, sorting, and recentness.</li>
                    <li><strong>Autocomplete</strong>: Gemini Completion-backed suggestions with search-title fallback.</li>
                    <li><strong>Spell correction / Did-you-mean</strong>: Uses Vertex AI spellCorrectionSpec (SUGGESTION_ONLY) to surface corrected queries; click to rerun.</li>
                    <li><strong>Images</strong>: Schema-aligned <code>images[].uri</code> populated from our thumbnail generator and served via GCS.</li>
                    <li><strong>Detail Pages</strong>: Article, video, and audio layouts per item ID fetched via <code>getDocument</code>.</li>
                    <li><strong>User Events</strong>: search, view-item, media-play, media-complete (optimistic) with attributionToken and pseudo user IDs.</li>
                    <li><strong>Browse Feed</strong>: Home “Latest Feed” pulls live results (empty query, sorted by available_time desc).</li>
                    <li><strong>Facets</strong>: Parent-level category rollups (e.g., Politics) with expand/collapse; media type filters.</li>
                </ul>
            </section>

            <section className="neo-border bg-white p-6 space-y-3">
                <h2 className="font-mono text-sm text-gray-600">Spell Correction / Fuzzy UX</h2>
                <p className="font-sans text-sm text-gray-700">
                    Search requests include <code>spellCorrectionSpec: SUGGESTION_ONLY</code>. When the API returns <code>correctedQuery</code>, the UI shows “Did you mean …” and lets users rerun with one click. Autocomplete still handles typos via Completion by default. This improves misspelling tolerance without changing the user’s original query.
                </p>
            </section>

            <section className="neo-border bg-white p-6 space-y-3">
                <h2 className="font-mono text-sm text-gray-600">Data & Schema</h2>
                <p className="font-sans text-sm text-gray-700">
                    Documents use the media predefined schema: <code>content_type</code>, <code>categories</code>, <code>available_time</code>, <code>duration</code>, and <code>images</code>. Thumbnails are generated via Gemini image preview and uploaded to <code>gs://doit-vertex-ai-search</code>.
                </p>
            </section>

            <section className="neo-border bg-white p-6 space-y-3">
                <h2 className="font-mono text-sm text-gray-600">How to Try</h2>
                <ol className="list-decimal pl-5 space-y-2 font-sans text-sm">
                    <li>Use the search bar (header or hero) to query topics like “politics”, “mars”, or “quantum”.</li>
                    <li>Apply facets (category/media type) and switch grid/list views in Latest Feed.</li>
                    <li>Click any card to open the detail page; plays/logs user events.</li>
                    <li>Clear the query to browse all media (empty search).</li>
                </ol>
            </section>

            <section className="neo-border bg-white p-6 space-y-3">
                <h2 className="font-mono text-sm text-gray-600">Links</h2>
                <div className="flex gap-4 font-mono text-sm">
                    <Link href="/search" className="underline">Search</Link>
                    <Link href="/" className="underline">Home</Link>
                </div>
            </section>
        </div>
    );
}
