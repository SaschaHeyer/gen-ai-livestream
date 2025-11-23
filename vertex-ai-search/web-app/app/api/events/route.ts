import { NextResponse } from 'next/server';
import { UserEventServiceClient } from '@google-cloud/discoveryengine';

const client = new UserEventServiceClient();

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const {
            eventType,
            userPseudoId,
            userId,
            searchQuery,
            attributionToken,
            documents,
            mediaInfo,
            userAgent,
            pageViewId,
            eventTime,
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

        const now = new Date();
        const userEvent: any = {
            eventType,
            userPseudoId,
            eventTime: {
                seconds: Math.floor(now.getTime() / 1000),
                nanos: (now.getTime() % 1000) * 1e6,
            },
        };

        if (searchQuery || attributionToken || documents?.length) {
            // For non-search events, attributionToken without searchInfo triggers a required-field error.
            const includeAttribution = attributionToken && searchQuery;
            userEvent.searchInfo = searchQuery ? { searchQuery } : undefined;
            userEvent.attributionToken = includeAttribution ? attributionToken : undefined;
            if (documents?.length) {
                userEvent.documents = documents.map((id: string) => ({ id }));
            }
        }

        if (mediaInfo) {
            userEvent.mediaInfo = mediaInfo;
        }

        userEvent.userInfo = {
            userAgent: userAgent || undefined,
            userId: userId || undefined,
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
