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
                    <li><strong>Language- & Market-aware search</strong>: Preferences set in <code>/config</code> are sent to Vertex AI Search and Completion; German typo “eegriewende” still suggests “Energiewende 2.0 beschleunigt” (see screenshot below). Market (SE/DE/ES) is softly boosted in ranking.</li>
                </ul>
            </section>

            <section className="neo-border bg-white p-6 space-y-3">
                <h2 className="font-mono text-sm text-gray-600">Facets & Filtering</h2>
                <p className="font-sans text-sm text-gray-700">
                    Vertex AI Search returns global facet counts (media search doesn’t re-scope counts after filtering). We facet on categories, media type, author, language, and market. To avoid key-property restrictions, we facet on dedicated fields (<code>categories_facet</code>, <code>content_type_facet</code>, <code>author_facet</code>, <code>language_facet</code>, <code>market_facet</code>) marked indexable + filterable + dynamic facetable in the schema.
                </p>
                <pre className="bg-gray-50 border border-gray-200 p-4 font-mono text-xs overflow-auto whitespace-pre-wrap">
{`// app/api/search/route.ts (facet specs)
facetSpecs: [
  { facetKey: { key: 'categories' }, limit: 20 },
  { facetKey: { key: 'content_type' }, limit: 10 },
  { facetKey: { key: 'language_code' }, limit: 10 },
  { facetKey: { key: 'author_facet' }, limit: 20 },
  { facetKey: { key: 'market_facet' }, limit: 10 },
],`}
                </pre>
                <pre className="bg-gray-50 border border-gray-200 p-4 font-mono text-xs overflow-auto whitespace-pre-wrap">
{`// app/api/search/route.ts (REST call)
const auth = new GoogleAuth({ scopes: ['https://www.googleapis.com/auth/cloud-platform'] });
const client = await auth.getClient();
const searchUrl = 'https://discoveryengine.googleapis.com/v1beta/' + servingConfig + ':search';
const resp = await client.request({ url: searchUrl, method: 'POST', data: request_body });
const facets = resp.data.facets;`}
                </pre>
                <p className="font-sans text-xs text-gray-600">Facet counts shown are global (not re-scoped by current filters). For demo simplicity we fetch all docs and could recompute counts client-side if needed.</p>
            </section>

            <section className="neo-border bg-white p-6 space-y-3">
                <h2 className="font-mono text-sm text-gray-600">Language Hinting Demo</h2>
                <p className="font-sans text-sm text-gray-700">
                    Autocomplete and search receive <code>languageCodes</code> from <code>/config</code>. Even with a misspelled German query (below), Completion suggests the correct German headline based on the language hint.
                </p>
                <div className="border border-gray-200">
                    <img src="about/language.png" alt="German autocomplete suggestion example" className="w-full" />
                </div>
                <pre className="bg-gray-50 border border-gray-200 p-4 font-mono text-xs overflow-auto whitespace-pre-wrap">
{`// components/SearchBar.tsx (excerpt)
const { userPseudoId } = useUserEvents();
const { languageCodes, countryCode } = useUserPreferences();

const fetchSuggestions = async (text: string) => {
  const res = await fetch('/api/autocomplete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: text, userPseudoId, languageCodes, userCountryCode: countryCode }),
  });
};`}
                </pre>
            </section>

            <section className="neo-border bg-white p-6 space-y-3">
                <h2 className="font-mono text-sm text-gray-600">Market Boost in Ranking</h2>
                <p className="font-sans text-sm text-gray-700">
                    Searches softly boost results whose <code>market</code> matches the userselected country from <code>/config</code>. This keeps localized stories near the top while still showing global content.
                </p>
                <pre className="bg-gray-50 border border-gray-200 p-4 font-mono text-xs overflow-auto whitespace-pre-wrap">
{`// app/api/search/route.ts (excerpt)
if (userCountryCode) {
  request_body.boostSpec = {
    conditionBoostSpecs: [
      {
        condition: 'market: ANY("' + userCountryCode + '")',
        boost: 0.5, // boost must be in [-1, 1]
      },
    ],
  };
}`}
                </pre>
                <p className="font-sans text-xs text-gray-600">Tune the boost (max 1.0) or swap to a default filter for stricter localization.</p>
            </section>

            <section className="neo-border bg-white p-6 space-y-3">
                <h2 className="font-mono text-sm text-gray-600">Query Expansion (AUTO)</h2>
                <p className="font-sans text-sm text-gray-700">
                    Vertex AI Search expands misspelled or related terms to keep recall high. With <code>queryExpansionSpec.condition = 'AUTO'</code> and <code>pinUnexpandedResults = true</code>, exact matches stay on top while expanded matches (e.g., “colonny” → “colony”) still return results.
                </p>
                <pre className="bg-gray-50 border border-gray-200 p-4 font-mono text-xs overflow-auto whitespace-pre-wrap">
{`// app/api/search/route.ts (excerpt)
queryExpansionSpec: {
  condition: 'AUTO',
  pinUnexpandedResults: true,
},
spellCorrectionSpec: {
  mode: 'AUTO',
},`}
                </pre>
                <p className="font-sans text-xs text-gray-600">AUTO may return results without a visible correctedQuery; it silently broadens the query while keeping exact hits pinned.</p>
            </section>

            <section className="neo-border bg-white p-6 space-y-3">
                <h2 className="font-mono text-sm text-gray-600">Spell Correction (AUTO)</h2>
                <p className="font-sans text-sm text-gray-700">
                    Spell correction is set to <code>mode: 'AUTO'</code>, so misspellings are corrected server-side without requiring user clicks. This pairs with query expansion to catch typos and near-matches.
                </p>
                <pre className="bg-gray-50 border border-gray-200 p-4 font-mono text-xs overflow-auto whitespace-pre-wrap">
{`// app/api/search/route.ts (excerpt)
spellCorrectionSpec: {
  mode: 'AUTO',
},`}
                </pre>
                <p className="font-sans text-xs text-gray-600">Use this when you prefer automatic fixes; switch to SUGGESTION_ONLY if you want to show “Did you mean…” and let users opt in.</p>
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
