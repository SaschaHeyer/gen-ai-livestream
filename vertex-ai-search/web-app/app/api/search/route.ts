import { SearchServiceClient } from '@google-cloud/discoveryengine';
import { NextResponse } from 'next/server';

// Initialize client
const client = new SearchServiceClient();

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const { query, pageToken, filter, orderBy } = body;

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

        const request_body = {
            servingConfig: servingConfig,
            query: effectiveQuery,
            pageSize: 10,
            offset: 0,
            // Backend filters are omitted because custom fields may not be marked filterable;
            // we apply filters locally below.
            orderBy: orderBy || undefined,
            contentSearchSpec: {
                snippetSpec: { returnSnippet: true },
                summarySpec: { summaryResultCount: 5, includeCitations: true },
            },
            facetSpecs: [
                { facetKey: { key: 'categories', prefixes: ['doit'] }, limit: 20 },
                { facetKey: { key: 'content_type' }, limit: 10 },
            ],
        };

        if (pageToken) {
            // request_body.pageToken = pageToken;
        }

        const [results, , response] = await client.search(request_body);

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
            };
        }) || [];

        // ---------- Local fallback for filters/facets ----------
        // If the backend doesn't return facets or the fields aren't filterable yet,
        // we still allow the UI to filter using the returned page.
        let filteredResults = mappedResults;

        if (filter) {
            // Very small parser for filters like `categories: ANY("a","b") AND media_type: ANY("clip")`
            const categoriesMatch = /categories:\s*ANY\(\"([^\)]*)\"\)/i.exec(filter);
            const mediaTypeMatch = /content_type:\s*ANY\(\"([^\)]*)\"\)/i.exec(filter);

            const selectedCategories = categoriesMatch?.[1]?.split('","').map((s) => s.replace(/\"/g, '')) || [];
            const selectedMediaTypes = mediaTypeMatch?.[1]?.split('","').map((s) => s.replace(/\"/g, '')) || [];

            filteredResults = mappedResults.filter((r) => {
                const catOk = selectedCategories.length === 0 || (r.category && selectedCategories.includes(r.category));
                const typeOk = selectedMediaTypes.length === 0 || (r.mediaType && selectedMediaTypes.includes(r.mediaType));
                return catOk && typeOk;
            });
        }

        // Facet derivation from filtered results
        let facetsOut = response?.facets || [];
        if (!facetsOut || facetsOut.length === 0) {
            const tally = (items: (string | undefined)[]) => {
                const counts: Record<string, number> = {};
                items.filter(Boolean).forEach((v) => {
                    const key = (v as string).trim();
                    counts[key] = (counts[key] || 0) + 1;
                });
                // group by the last path segment for readability (e.g., finops)
                const grouped: Record<string, { value: string; count: number }[]> = {};
                Object.entries(counts).forEach(([value, count]) => {
                    const parts = value.split('>');
                    const leaf = parts[parts.length - 1].trim();
                    if (!grouped[leaf]) grouped[leaf] = [];
                    grouped[leaf].push({ value, count });
                });

                return Object.values(grouped)
                    .map((arr) => arr.reduce((a, b) => ({ value: a.value, count: a.count + b.count })))
                    .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
            };

            const categoryValues: (string | undefined)[] = [];
            const mediaTypeValues: (string | undefined)[] = [];
            filteredResults.forEach((r) => {
                categoryValues.push(r.category);
                mediaTypeValues.push(r.mediaType);
            });

            facetsOut = [
                { key: 'categories', values: tally(categoryValues) },
                { key: 'content_type', values: tally(mediaTypeValues) },
            ];
        }

        return NextResponse.json({
            results: filteredResults,
            totalSize: response?.totalSize,
            facets: facetsOut,
            attributionToken: (response as any)?.attributionToken,
        });

    } catch (error) {
        console.error('Search API Error:', error);
        return NextResponse.json(
            { error: 'Internal Server Error' },
            { status: 500 }
        );
    }
}
