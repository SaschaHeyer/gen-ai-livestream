/**
 * Simple Cloud Run demo service that intentionally fails on cold starts when
 * the CONFIG_BUCKET environment variable is missing. This provides a clean
 * failure scenario for triage exercises.
 */
const express = require('express');
const { Storage } = require('@google-cloud/storage');

const PORT = process.env.PORT || 8080;
const CONFIG_FILE = process.env.CONFIG_FILE || 'config.json';
const MAX_CONFIG_BYTES = 8 * 1024;

/**
 * Ensures the CONFIG_BUCKET variable is present and that the referenced file
 * can be read from Cloud Storage. Any failure here causes the container to
 * exit, making it easy to reproduce startup crashes.
 */
async function validateStartup() {
  const bucketName = process.env.CONFIG_BUCKET;

  if (!bucketName) {
    throw new Error(
      'Missing CONFIG_BUCKET environment variable. ' +
        'Set CONFIG_BUCKET to a Cloud Storage bucket that contains config.json.'
    );
  }

  const storage = new Storage();
  const file = storage.bucket(bucketName).file(CONFIG_FILE);

  try {
    // We only care that the file exists and is readable. Limit the download to avoid hanging.
    await file.download({ end: 64 }); // Download just the first bytes to keep it light.
    console.info(
      `Loaded configuration stub from gs://${bucketName}/${CONFIG_FILE} during startup validation.`
    );
  } catch (err) {
    err.message = `Failed to load configuration from gs://${bucketName}/${CONFIG_FILE}: ${err.message}`;
    throw err;
  }
}

/**
 * Simulates a developer mistake where a new feature path depends on a missing
 * configuration bucket. Triggered via GET /crash to crash the container and
 * reproduce request-scoped incidents.
 */
async function triggerCrashPath() {
  const bucketName = process.env.CONFIG_BUCKET;
  const storage = new Storage();
  const file = storage.bucket(bucketName).file(CONFIG_FILE);
  const [buffer] = await file.download({ end: MAX_CONFIG_BYTES });
  const config = JSON.parse(buffer.toString('utf-8'));

  // Developer bug: assumes featureFlags is an array, but config.json ships an object.
  return config.featureFlags.map((flag) => flag.name.toUpperCase());
}

async function bootstrap() {
  await validateStartup();

  const app = express();

  app.get('/', (_req, res) => {
    res.json({
      message: 'Cloud Run triage demo service',
      configBucket: process.env.CONFIG_BUCKET,
      configFile: CONFIG_FILE,
    });
  });

  app.get('/crash', async (_req, _res, next) => {
    try {
      await triggerCrashPath();
      // The route should never succeed; reaching here would indicate the bug is fixed.
      _res.json({ status: 'unexpected success' });
    } catch (err) {
      console.error(err);
      _res.status(500).json({
        error: 'CRASH_ENDPOINT_FAILURE',
        message: err.message,
        code:
          err.code ||
          (err instanceof TypeError ? 'TYPE_ERROR' : 'UNEXPECTED'),
      });
      // Exit after the response cycle so logs flush and Express finishes handling.
      setImmediate(() => process.exit(1));
    }
  });

  app.get('/healthz', (_req, res) => res.send('ok'));

  app.listen(PORT, () => {
    console.info(`Demo service listening on port ${PORT}`);
  });
}

bootstrap().catch((err) => {
  console.error('Startup validation failed. The service will exit.', err);
  // Defer the exit so logs flush correctly.
  setImmediate(() => process.exit(1));
});
