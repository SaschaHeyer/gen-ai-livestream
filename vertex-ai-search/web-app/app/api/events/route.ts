import { NextResponse } from 'next/server';
import { UserEventServiceClient } from '@google-cloud/discoveryengine';

const client = new UserEventServiceClient();

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const {
            eventType,
            userPseudoId,
            searchQuery,
            attributionToken,
            documents,
            mediaInfo,
            userAgent,
            pageViewId,
        } = body;

        if (!eventType || !userPseudoId) {
            return NextResponse.json({ error: 'eventType and userPseudoId are required' }, { status: 400 });
        }

        const projectId = process.env.GOOGLE_CLOUD_PROJECT_ID;
        const location = process.env.GOOGLE_CLOUD_LOCATION || 'global';
        const dataStoreId = process.env.VERTEX_AI_DATA_STORE_ID;

        if (!projectId || !dataStoreId) {
            return NextResponse.json({ error: 'Missing environment variables' }, { status: 500 });
        }

        const parent = `projects/${projectId}/locations/${location}/collections/default_collection/dataStores/${dataStoreId}`;

        const userEvent: any = {
            eventType,
            userPseudoId,
            eventTime: new Date().toISOString(),
        };

        if (searchQuery || attributionToken || documents?.length) {
            userEvent.searchInfo = searchQuery ? { searchQuery } : undefined;
            userEvent.attributionToken = attributionToken;
            if (documents?.length) {
                userEvent.documents = documents.map((id: string) => ({ id }));
            }
        }

        if (mediaInfo) {
            userEvent.mediaInfo = mediaInfo;
        }

        userEvent.userInfo = {
            userAgent: userAgent || undefined,
        };

        if (pageViewId) {
            userEvent.pageInfo = { pageViewId };
        }

        await client.writeUserEvent({
            parent,
            userEvent,
        });

        return NextResponse.json({ ok: true });
    } catch (error) {
        console.error('User event error:', error);
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }
}
