import { DocumentServiceClient } from '@google-cloud/discoveryengine';
import { NextResponse } from 'next/server';

const client = new DocumentServiceClient();

export async function GET(
    _req: Request,
    context: { params: Promise<{ id: string }> }
) {
    try {
        const params = await context.params;
        const projectId = process.env.GOOGLE_CLOUD_PROJECT_ID;
        const location = process.env.GOOGLE_CLOUD_LOCATION || 'global';
        const dataStoreId = process.env.VERTEX_AI_DATA_STORE_ID;
        const id = params.id;

        if (!projectId || !dataStoreId) {
            return NextResponse.json({ error: 'Missing env vars' }, { status: 500 });
        }

        const name = `projects/${projectId}/locations/${location}/collections/default_collection/dataStores/${dataStoreId}/branches/0/documents/${id}`;

        const [doc] = await client.getDocument({ name });

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

        let data: any = doc.structData;
        if (doc.structData && (doc.structData as any).fields) {
            data = unwrapStruct(doc.structData as any);
        }

        return NextResponse.json({
            id: doc.id,
            data,
        });
    } catch (error: any) {
        console.error('Document fetch error:', error);
        if (error.code === 5) {
            return NextResponse.json({ error: 'Not found' }, { status: 404 });
        }
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }
}
