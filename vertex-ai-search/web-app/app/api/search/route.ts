import { GoogleAuth } from 'google-auth-library';
import { v1beta } from '@google-cloud/discoveryengine';
import { NextResponse } from 'next/server';

// Completion still via SDK; search via REST to mirror curl that returns facets
const completionClient = new v1beta.CompletionServiceClient();

export async function POST(request: Request) {
    try {
        let body: any = {};
        try {
            body = await request.json();
        } catch (e) {
            body = {};
        }
        const { query, pageToken, filter, orderBy, userPseudoId, userId, userCountryCode, languageCodes, pageSize } = body;

        const projectId = process.env.GOOGLE_CLOUD_PROJECT_ID;
        const location = process.env.GOOGLE_CLOUD_LOCATION || 'global';
        const dataStoreId = process.env.VERTEX_AI_DATA_STORE_ID;

        if (!projectId || !dataStoreId) {
            return NextResponse.json(
                { error: 'Missing environment variables' },
                { status: 500 }
            );
        }

        // Construct serving config path manually to be safe
        // projects/{project}/locations/{location}/collections/{collection}/dataStores/{data_store}/servingConfigs/{serving_config}
        const servingConfig = `projects/${projectId}/locations/${location}/collections/default_collection/dataStores/${dataStoreId}/servingConfigs/default_search`;

        const effectiveQuery = query ?? '';

        const request_body: any = {
            servingConfig: servingConfig,
            query: effectiveQuery,
            pageSize: pageSize || 35,
            offset: 0,
            // Backend filters are omitted because custom fields may not be marked filterable;
            // we apply filters locally below.
            orderBy: orderBy || undefined,
            contentSearchSpec: {
                snippetSpec: { returnSnippet: true },
                summarySpec: { summaryResultCount: 5, includeCitations: true },
            },
            queryExpansionSpec: {
                condition: 'AUTO',
                pinUnexpandedResults: true,
            },
            facetSpecs: [
                { facetKey: { key: 'categories' }, limit: 20 },
                { facetKey: { key: 'content_type' }, limit: 10 },
                { facetKey: { key: 'language_code' }, limit: 10 },
                { facetKey: { key: 'author_facet' }, limit: 20 },
                { facetKey: { key: 'market_facet' }, limit: 10 },
            ],
            spellCorrectionSpec: {
                mode: 'AUTO',
            },
        };

        // Soft geo/market boost based on user-selected country (config page)
        if (userCountryCode) {
            request_body.boostSpec = {
                conditionBoostSpecs: [
                    {
                        condition: `market: ANY("${userCountryCode}")`,
                        boost: 1.0, // max boost (must be in [-1, 1])
                    },
                ],
            };
        }

        if (userPseudoId) request_body.userPseudoId = userPseudoId;
        if (userId) {
            request_body.userInfo = {
                userId,
                userAgent: request.headers.get('user-agent') || undefined,
            };
        }
        if (userCountryCode) {
            request_body.userLabels = { country: userCountryCode };
        }
        if (languageCodes && Array.isArray(languageCodes) && languageCodes.length > 0) {
            request_body.languageCode = languageCodes[0];
        }

        if (pageToken) {
            // request_body.pageToken = pageToken;
        }

        // Call REST search to ensure facet parity with curl
        const auth = new GoogleAuth({ scopes: ['https://www.googleapis.com/auth/cloud-platform'] });
        const client = await auth.getClient();
        const searchUrl = `https://discoveryengine.googleapis.com/v1beta/${servingConfig}:search`;
        const resp = await client.request<any>({
            url: searchUrl,
            method: 'POST',
            data: request_body,
        });
        const searchResponse = resp.data;

        const results = (searchResponse as any)?.results || [];
        console.log('Facets from Vertex:', JSON.stringify((searchResponse as any)?.facets || [], null, 2));
        let correctedQuery = (searchResponse as any)?.correctedQuery || null;
        if (correctedQuery) {
            console.log('Spell correction suggestion:', correctedQuery, 'for query:', query);
        }

        // Helper to unwrap Protobuf Struct
        const unwrapValue = (value: any): any => {
            if (!value) return null;
            if (value.stringValue !== undefined) return value.stringValue;
            if (value.numberValue !== undefined) return value.numberValue;
            if (value.boolValue !== undefined) return value.boolValue;
            if (value.listValue !== undefined) return value.listValue.values?.map(unwrapValue) || [];
            if (value.structValue !== undefined) return unwrapStruct(value.structValue);
            return null;
        };

        const unwrapStruct = (struct: any): any => {
            if (!struct || !struct.fields) return {};
            const result: any = {};
            for (const key in struct.fields) {
                result[key] = unwrapValue(struct.fields[key]);
            }
            return result;
        };

        if (results && results.length > 0) {
            console.log('First result document:', JSON.stringify(results[0].document, null, 2));
        }

        // Transform results to be more frontend-friendly
        const mappedResults = results?.map((result) => {
            let data: any = result.document?.structData;

            // Check if it's a Protobuf Struct with fields
            if (data && data.fields) {
                data = unwrapStruct(data);
            }

            return {
                id: result.document?.id,
                title: data?.title || result.document?.id,
                description: data?.description || result.document?.content,
                uri: data?.uri,
                category: data?.categories?.[0] || 'General',
                publishTime: data?.available_time,
                mediaType: data?.content_type || data?.media_type || (data?.uri?.endsWith('.mp4') ? 'video' : data?.uri?.endsWith('.mp3') ? 'audio' : 'news'),
                thumbnail: data?.images?.[0]?.uri || data?.image_uri || data?.thumbnail, // prefer schema images
                duration: data?.duration,
                author: data?.author,
                language: data?.language || data?.language_code,
                market: data?.market,
                popularity: data?.popularity,
                rating: data?.rating,
            };
        }) || [];

        // ---------- Local fallback for filters/facets ----------
        // If the backend doesn't return facets or the fields aren't filterable yet,
        // we still allow the UI to filter using the returned page.
        let filteredResults = mappedResults;

        if (filter) {
            // Very small parser for filters like `categories: ANY("a","b") AND content_type: ANY("clip")`
            const categoriesMatch = /categories:\s*ANY\("([^\)]*)"\)/i.exec(filter);
            const mediaTypeMatch = /content_type:\s*ANY\("([^\)]*)"\)/i.exec(filter);
            const authorMatch = /author:\s*ANY\("([^\)]*)"\)/i.exec(filter);
            const languageMatch = /language:\s*ANY\("([^\)]*)"\)/i.exec(filter);
            const marketMatch = /market:\s*ANY\("([^\)]*)"\)/i.exec(filter);

            const selectedCategories = categoriesMatch?.[1]?.split('","').map((s) => s.replace(/\"/g, '')) || [];
            const selectedMediaTypes = mediaTypeMatch?.[1]?.split('","').map((s) => s.replace(/\"/g, '')) || [];
            const selectedAuthors = authorMatch?.[1]?.split('","').map((s) => s.replace(/\"/g, '')) || [];
            const selectedLanguages = languageMatch?.[1]?.split('","').map((s) => s.replace(/\"/g, '')) || [];
            const selectedMarkets = marketMatch?.[1]?.split('","').map((s) => s.replace(/\"/g, '')) || [];

            filteredResults = mappedResults.filter((r) => {
                const catOk =
                    selectedCategories.length === 0 ||
                    (r.category && selectedCategories.some((c) => r.category.toLowerCase().includes(c.toLowerCase())));
                const typeOk = selectedMediaTypes.length === 0 || (r.mediaType && selectedMediaTypes.includes(r.mediaType));
                const authorOk = selectedAuthors.length === 0 || (r.author && selectedAuthors.includes(r.author));
                const languageOk = selectedLanguages.length === 0 || (r.language && selectedLanguages.includes(r.language));
                const marketOk = selectedMarkets.length === 0 || (r.market && selectedMarkets.includes(r.market));
                return catOk && typeOk && authorOk && languageOk && marketOk;
            });
        }

        let facetsOut = (searchResponse as any)?.facets || [];

// If no correction from search (or we want a suggestion), fall back to completion for a suggestion
        if (!correctedQuery && (query || '').length >= 2) {
            try {
                const name = `projects/${projectId}/locations/${location}/collections/default_collection/dataStores/${dataStoreId}`;
                const [comp] = await completionClient.completeQuery({
                    dataStore: name,
                    query: query || '',
                    pageSize: 1,
                    queryModel: 'document',
                });
                const suggestion = comp.querySuggestions?.[0]?.suggestion;
                if (suggestion && suggestion.toLowerCase() !== (query || '').toLowerCase()) {
                    correctedQuery = suggestion;
                    console.log('Completion-based suggestion:', suggestion, 'for query:', query);
                }
            } catch (e) {
                console.warn('Completion fallback failed:', e);
            }
        }

        return NextResponse.json({
            results: filteredResults,
            totalSize: (searchResponse as any)?.totalSize,
            facets: facetsOut,
            attributionToken: (searchResponse as any)?.attributionToken,
            correctedQuery,
        });

    } catch (error) {
        console.error('Search API Error:', error);
        return NextResponse.json(
            { error: 'Internal Server Error' },
            { status: 500 }
        );
    }
}
