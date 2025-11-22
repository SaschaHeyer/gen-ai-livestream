#!/usr/bin/env node
/**
 * Quick “preview search results” script for workshops.
 * Mirrors https://cloud.google.com/generative-ai-app-builder/docs/preview-search-results#genappbuilder_search-nodejs
 * but points to a media data store instead of an engine.
 *
 * Usage:
 *   node scripts/preview_search.js --project-id sascha-playground-doit \
 *     --data-store-id media_1763324268059 --location global --query "cloud"
 */

const { SearchServiceClient } = require('@google-cloud/discoveryengine');
const { argv } = require('process');

const args = {};
argv.slice(2).forEach((item, idx, list) => {
  if (item.startsWith('--')) {
    const key = item.replace('--', '');
    const val = list[idx + 1] && !list[idx + 1].startsWith('--') ? list[idx + 1] : true;
    args[key] = val;
  }
});

const projectId = args['project-id'];
const dataStoreId = args['data-store-id'];
const location = args.location || 'global';
const query = args.query || '';
const pageSize = Number(args['page-size'] || 10);

if (!projectId || !dataStoreId) {
  console.error('Required: --project-id and --data-store-id');
  process.exit(1);
}

async function main() {
  const client = new SearchServiceClient();

  // dataStores.servingConfigs.search path
  const servingConfig = `projects/${projectId}/locations/${location}/collections/default_collection/dataStores/${dataStoreId}/servingConfigs/default_search`;

  const request = {
    servingConfig,
    query,
    pageSize,
    // Keep empty filter to avoid errors if fields aren't marked filterable
    contentSearchSpec: {
      summarySpec: { summaryResultCount: 3 },
    },
    facetSpecs: [
      { facetKey: { key: 'categories' }, limit: 10 },
      { facetKey: { key: 'content_type' }, limit: 5 },
    ],
  };

  const [response] = await client.search(request, { autoPaginate: false });

  console.log(`Total results: ${response.totalSize || response.results?.length || 0}`);
  console.log('--- RESULTS ---');
  (response.results || []).forEach((r, idx) => {
    const data = r.document?.structData || {};
    console.log(
      `#${idx + 1} ${data.title || r.document?.id} ` +
        `[${data.content_type || 'unknown'}] -> ${data.uri || ''}`
    );
  });

  if (response.facets?.length) {
    console.log('--- FACETS ---');
    response.facets.forEach((f) => {
      console.log(`Facet: ${f.key}`);
      (f.values || []).forEach((v) => console.log(`  ${v.value}: ${v.count}`));
    });
  }

  if (response.summary?.summaryText) {
    console.log('--- SUMMARY ---');
    console.log(response.summary.summaryText);
  }
}

main().catch((err) => {
  console.error('Preview search failed:', err.message);
  process.exit(1);
});
