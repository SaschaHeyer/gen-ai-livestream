import { CompletionServiceClient, SearchServiceClient } from '@google-cloud/discoveryengine';
import { NextResponse } from 'next/server';

const client = new CompletionServiceClient();
const searchClient = new SearchServiceClient();

export async function POST(request: Request) {
    try {
        const { query, userPseudoId, userId, languageCodes, userCountryCode } = await request.json();
        if (!query || !query.trim()) {
            return NextResponse.json({ suggestions: [] });
        }

        const projectId = process.env.GOOGLE_CLOUD_PROJECT_ID;
        const location = process.env.GOOGLE_CLOUD_LOCATION || 'global';
        const dataStoreId = process.env.VERTEX_AI_DATA_STORE_ID;

        if (!projectId || !dataStoreId) {
            return NextResponse.json(
                { error: 'Missing environment variables' },
                { status: 500 }
            );
        }

        // Completion uses the dataStore path (not servingConfig)
        const dataStore = `projects/${projectId}/locations/${location}/collections/default_collection/dataStores/${dataStoreId}`;

        const [response] = await client.completeQuery({
            dataStore,
            query,
            pageSize: 5,
            queryModel: 'document', // suitable for media/doc search
            userPseudoId: userPseudoId || undefined,
        });

        let suggestions =
            response.querySuggestions?.map((s) => s.suggestion) || [];

        // Fallback: derive quick suggestions from top search titles if completion is empty
        if ((!suggestions || suggestions.length === 0) && query.trim().length >= 2) {
            const servingConfig = `${dataStore}/servingConfigs/default_search`;
            const iterable = searchClient.searchAsync({
                servingConfig,
                query,
                pageSize: 5,
            });
            const titles: string[] = [];
            for await (const res of iterable) {
                const doc: any = res.document;
                let title: string | undefined;
                if (doc?.structData?.title) {
                    title = doc.structData.title;
                } else if (doc?.structData?.fields?.title?.stringValue) {
                    title = doc.structData.fields.title.stringValue;
                }
                if (title) titles.push(title);
                if (titles.length >= 5) break;
            }
            suggestions = titles;
        }

        return NextResponse.json({ suggestions });
    } catch (error) {
        console.error('Autocomplete API Error:', error);
        return NextResponse.json(
            { error: 'Internal Server Error' },
            { status: 500 }
        );
    }
}
